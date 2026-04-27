# blueprints/inventario.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS
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

bp = Blueprint('inventario', __name__)


# ── Helpers de permisos granulares ────────────────────────────────────────────
# Cualquier user autenticado puede LEER inventario (necesario para que el
# equipo vea stock/lotes desde su módulo). Pero las ESCRITURAS y operaciones
# críticas se restringen al rol correspondiente.
#
# Patrón de uso al inicio del endpoint:
#     u, err, code = _require_planta_write()
#     if err: return err, code

QC_USERS = CALIDAD_USERS | ADMIN_USERS


def _require_session():
    """Solo autenticación (cualquier user logueado). Usado en lecturas."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    return u, None, None


def _require_planta_write():
    """Operaciones que ESCRIBEN inventario: cualquier usuario autenticado.

    Política decidida por CEO 2026-04-27: el flujo operativo cruza áreas
    (contadoría que registra recepción, asistentes que ajustan conteos,
    técnica que da entrada a piezas), por lo que se abre a cualquier
    usuario logueado. La trazabilidad se mantiene por:
      - audit_log con username + IP en cada operación
      - campo 'operador' en cada movimiento de la tabla movimientos
      - security_events con login/logout

    Operaciones destructivas (reset, delete masivo) siguen requiriendo
    _require_admin(). QC (aprobar lote, etc.) sigue requiriendo
    _require_qc() (CALIDAD + ADMIN).
    """
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    return u, None, None


def _require_qc():
    """Para operaciones de QC: CALIDAD + ADMIN únicamente."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    if u not in QC_USERS:
        return None, jsonify({
            'error': 'Solo equipo de Calidad o admins',
            'detail': f"User '{u}' no está en CALIDAD/ADMIN"
        }), 403
    return u, None, None


def _require_admin():
    """Para operaciones destructivas: solo ADMIN."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    if u not in ADMIN_USERS:
        return None, jsonify({'error': 'Solo administradores'}), 403
    return u, None, None

@bp.route('/api/inventario')
def get_inventario():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM movimientos')
    mov = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM producciones')
    prod = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM alertas')
    alrt = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(CASE WHEN tipo="Entrada" THEN cantidad ELSE -cantidad END),0) FROM movimientos')
    stock = c.fetchone()[0]
    return jsonify({'total_items': mov, 'movimientos': mov, 'producciones': prod,
                    'alertas': alrt, 'stock_total': round(stock, 2)})

@bp.route('/api/formulas', methods=['GET', 'POST'])
def handle_formulas():
    conn = get_db()
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
        return jsonify({'message': f'Formula de {prod} guardada exitosamente'}), 201
    c.execute('SELECT producto_nombre, unidad_base_g, descripcion, fecha_creacion FROM formula_headers ORDER BY producto_nombre')
    headers = c.fetchall()
    formulas = []
    for h in headers:
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (h[0],))
        items = [{'material_id': r[0], 'material_nombre': r[1], 'porcentaje': r[2]} for r in c.fetchall()]
        formulas.append({'producto_nombre': h[0], 'unidad_base_g': h[1], 'descripcion': h[2],
                         'fecha_creacion': h[3], 'items': items})
    return jsonify({'formulas': formulas})

@bp.route('/api/formulas/<producto_nombre>', methods=['DELETE'])
def del_formula(producto_nombre):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (producto_nombre,))
    c.execute('DELETE FROM formula_headers WHERE producto_nombre=?', (producto_nombre,))
    conn.commit()
    return jsonify({'message': f'Formula {producto_nombre} eliminada'})

@bp.route('/api/movimientos', methods=['GET', 'POST'])
def handle_movimientos():
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        u, err, code = _require_planta_write()
        if err:
            return err, code
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
        conn.commit()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201
    c.execute('SELECT id, material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador, lote, proveedor, fecha_vencimiento, numero_factura FROM movimientos ORDER BY fecha DESC LIMIT 500')
    movimientos = [{'id': r[0], 'material_id': r[1] or '', 'material_nombre': r[2], 'cantidad': r[3], 'tipo': r[4], 'fecha': r[5], 'observaciones': r[6], 'operador': r[7] or '', 'lote': r[8] or '', 'proveedor': r[9] or '', 'fecha_vencimiento': r[10] or '', 'numero_factura': r[11] or ''} for r in c.fetchall()]
    return jsonify({'movimientos': movimientos})

@bp.route('/api/movimientos/<int:mov_id>', methods=['DELETE'])
def eliminar_movimiento(mov_id):
    from flask import session as flask_session
    from config import ADMIN_USERS
    usuario = flask_session.get('compras_user', '')
    if usuario not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado — solo administradores pueden eliminar movimientos'}), 403
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id, material_id, material_nombre, lote, cantidad, tipo FROM movimientos WHERE id=?', (mov_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Movimiento no encontrado'}), 404
    c.execute('DELETE FROM movimientos WHERE id=?', (mov_id,))
    conn.commit()
    return jsonify({'message': f'Movimiento {mov_id} eliminado. Lote: {row[3]}, MP: {row[2]}', 'id': mov_id}), 200

@bp.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    """Registra una producción con descuento atómico de MPs (FEFO).

    Flujo robusto (todo o nada):
      1. VALIDAR input (cantidad > 0, producto no vacío, fórmula existe).
      2. PRE-CHECK stock: para cada MP, consultar lotes disponibles (excluyendo
         CUARENTENA/RECHAZADO) y verificar que la suma cubre el requerimiento.
         Si falta stock para CUALQUIER MP → 422 sin escribir nada.
      3. EJECUTAR transacción: INSERT producciones + INSERT movimientos por lote.
         Si algo falla → ROLLBACK explícito + log + 500 con detalle.

    Esto reemplaza el flujo anterior que (a) creaba "salida sin lote" cuando no
    había stock — generando stock negativo silencioso, y (b) no validaba que la
    fórmula existiera — registraba producciones sin descuentos.

    Excepción: si una MP está marcada como ilimitada (agua, etc.) en
    programacion._MP_UNLIMITED, el pre-check la salta. Se sigue registrando el
    movimiento de salida (para trazabilidad de pesaje) pero sin requerir stock.
    """
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        u, err, code = _require_planta_write()
        if err:
            return err, code

        data = request.json or {}
        producto = (data.get('producto') or '').strip()
        presentacion = data.get('presentacion','')
        cantidad_kg = float(data.get('cantidad_kg', data.get('cantidad', 0)) or 0)
        cantidad_g = cantidad_kg * 1000
        operador = (data.get('operador') or '').strip()
        observaciones_in = data.get('observaciones', '')

        # ─── Validación 1: input ─────────────────────────────────────────────
        if not producto:
            return jsonify({'error': 'Producto vacío'}), 400
        if cantidad_kg <= 0:
            return jsonify({'error': 'cantidad_kg debe ser > 0'}), 400
        if not operador:
            return jsonify({'error': 'Falta operador'}), 400

        # ─── Validación 2: fórmula existe ───────────────────────────────────
        c.execute(
            'SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?',
            (producto,)
        )
        formula_items = c.fetchall()
        if not formula_items:
            return jsonify({
                'error': f"Producto sin fórmula registrada: '{producto}'",
                'detalle': 'Crea la fórmula en /tecnica antes de producir'
            }), 400

        # ─── Validación 3: idempotencia (anti-doble-click / replay) ─────────
        # Si en los últimos 90 segundos ya se registró la MISMA producción
        # (mismo producto + cantidad + operador), devolvemos la existente
        # en lugar de crear una nueva. Cubre el caso clásico de doble-click,
        # cliente con red lenta que reintenta, o un POST replay.
        try:
            c.execute("""SELECT id, fecha, lote
                         FROM producciones
                         WHERE producto=? AND cantidad=? AND operador=?
                           AND datetime(fecha) >= datetime('now','-90 seconds')
                         ORDER BY id DESC LIMIT 1""",
                      (producto, cantidad_kg, operador))
            dup = c.fetchone()
            if dup:
                return jsonify({
                    'message': 'Producción ya registrada hace <90s — duplicado evitado',
                    'lote': dup[2] or f'PROD-{dup[0]:05d}',
                    'duplicado': True,
                    'id_existente': dup[0],
                }), 200
        except sqlite3.OperationalError:
            pass  # esquema antiguo sin alguna columna — continuar normal

        # ─── MPs ilimitadas (no requieren validación de stock) ──────────────
        # Carga la lista desde programacion (única fuente de verdad)
        try:
            from .programacion import _MP_UNLIMITED, _norm_mp_name
            unlimited_set = set(_MP_UNLIMITED)
            def _is_unlimited(nombre):
                return _norm_mp_name(nombre or '').upper() in {x.upper() for x in unlimited_set}
        except Exception:
            unlimited_set = set()
            def _is_unlimited(nombre):  # noqa
                return False

        # ─── PRE-CHECK: stock suficiente para TODAS las MPs ─────────────────
        # Construimos el plan completo SIN escribir nada. Si falta stock para
        # alguna MP, abortamos antes del primer INSERT.
        plan_descuentos = []  # cada entry: {mat_id, mat_nombre, g_total, lotes_a_usar:[(lote, vence, g)]}
        faltantes = []        # MPs que no tienen stock suficiente
        for mat_id, mat_nombre, pct in formula_items:
            g_total = round((pct / 100.0) * cantidad_g, 2)
            if g_total <= 0:
                continue
            entry = {
                'mat_id': mat_id, 'mat_nombre': mat_nombre,
                'g_total': g_total, 'lotes_a_usar': [],
                'g_sin_lote': 0.0, 'unlimited': False,
            }
            if _is_unlimited(mat_nombre):
                # Aguas y similares — pesaje real pero sin requerir stock
                entry['unlimited'] = True
                entry['g_sin_lote'] = g_total
                plan_descuentos.append(entry)
                continue

            # FEFO sobre lotes disponibles (excluye CUARENTENA/RECHAZADO)
            c.execute("""SELECT lote, fecha_vencimiento,
                                SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                         FROM movimientos
                         WHERE material_id=? AND lote IS NOT NULL AND lote!='' AND lote!='S/L'
                           AND (estado_lote IS NULL OR estado_lote NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO'))
                         GROUP BY lote HAVING stock > 0
                         ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento=''
                                  THEN '9999' ELSE fecha_vencimiento END ASC""", (mat_id,))
            lotes_fefo = c.fetchall()
            stock_total_disp = sum(float(l[2] or 0) for l in lotes_fefo)
            if stock_total_disp + 0.01 < g_total:  # tolerancia 0.01g por floats
                faltantes.append({
                    'material': mat_nombre,
                    'material_id': mat_id,
                    'requerido_g': g_total,
                    'disponible_g': round(stock_total_disp, 2),
                    'falta_g': round(g_total - stock_total_disp, 2),
                })
                continue

            # Plan FEFO: cuánto sacar de cada lote
            g_restante = g_total
            for lrow in lotes_fefo:
                if g_restante <= 0:
                    break
                lote_n, lote_v, lote_s = lrow
                g_lote = round(min(g_restante, float(lote_s)), 2)
                entry['lotes_a_usar'].append({
                    'lote': lote_n,
                    'vence': str(lote_v)[:10] if lote_v else '',
                    'g': g_lote,
                })
                g_restante = round(g_restante - g_lote, 2)
            plan_descuentos.append(entry)

        if faltantes:
            return jsonify({
                'error': 'Stock insuficiente para producir',
                'producto': producto,
                'cantidad_kg': cantidad_kg,
                'faltantes': faltantes,
                'mensaje': (
                    f"No se puede producir {cantidad_kg}kg de {producto}: "
                    f"{len(faltantes)} MP(s) sin stock suficiente. "
                    f"Verifica entradas en /planta o crea OC en /compras."
                ),
            }), 422  # Unprocessable Entity

        # ─── ESCRITURA ATÓMICA ──────────────────────────────────────────────
        # SQLite con isolation_level='DEFERRED' (default): primer DML inicia
        # transacción implícita, conn.commit() la cierra, conn.rollback() la
        # descarta. Si una excepción ocurre antes del commit, los inserts
        # quedan en transacción y se rollbackean al cerrar la conexión.
        # Aún así, hacemos rollback EXPLÍCITO para no depender de timing.
        fecha = datetime.now().isoformat()
        prod_id = None
        lote_ref = None
        descuentos = []
        try:
            c.execute(
                'INSERT INTO producciones (producto, cantidad, fecha, estado, observaciones, operador, presentacion) VALUES (?,?,?,?,?,?,?)',
                (producto, cantidad_kg, fecha, 'Completado', observaciones_in, operador, presentacion)
            )
            prod_id = c.lastrowid
            lote_ref = f'PROD-{prod_id:05d}'
            try:
                c.execute("UPDATE producciones SET lote=? WHERE id=?", (lote_ref, prod_id))
            except sqlite3.OperationalError as _e:
                if 'no such column' not in str(_e).lower():
                    raise

            for plan in plan_descuentos:
                lotes_log = []
                for uso in plan['lotes_a_usar']:
                    c.execute(
                        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote, operador) VALUES (?,?,?,?,?,?,?,?)",
                        (plan['mat_id'], plan['mat_nombre'], uso['g'], 'Salida', fecha,
                         f"FEFO:{lote_ref}:{producto} x {cantidad_kg}kg", uso['lote'], operador)
                    )
                    lotes_log.append({'lote': uso['lote'], 'vence': uso['vence'], 'cantidad_g': uso['g']})
                # MPs ilimitadas: registrar movimiento de pesaje sin lote
                if plan.get('unlimited') and plan['g_sin_lote'] > 0:
                    c.execute(
                        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador) VALUES (?,?,?,?,?,?,?)",
                        (plan['mat_id'], plan['mat_nombre'], plan['g_sin_lote'], 'Salida', fecha,
                         f"UNLIMITED:{lote_ref}:{producto} x {cantidad_kg}kg (MP sin requerir stock)", operador)
                    )
                    lotes_log.append({'lote': 'unlimited', 'vence': '', 'cantidad_g': plan['g_sin_lote']})

                descuentos.append({
                    'material': plan['mat_nombre'],
                    'material_id': plan['mat_id'],
                    'cantidad_g': plan['g_total'],
                    'unlimited': plan.get('unlimited', False),
                    'lotes_fefo': lotes_log,
                })

            conn.commit()
        except Exception as _e:
            conn.rollback()
            __import__('logging').getLogger('inventario').error(
                "Producción FALLÓ tras pre-check OK (rollback): producto=%s kg=%s err=%s",
                producto, cantidad_kg, _e, exc_info=True
            )
            return jsonify({
                'error': 'Falla transaccional al registrar producción',
                'detalle': str(_e),
                'rollback': 'aplicado — no se descontó nada y no quedó producción registrada',
            }), 500

        # Stock PT se crea via Acondicionamiento → Liberacion (flujo BPM correcto)
        msg = f'Produccion registrada: {producto} x {cantidad_kg}kg (FEFO)'
        if descuentos:
            msg += f'. {len(descuentos)} MPs descontadas.'
        return jsonify({'message': msg, 'descuentos': descuentos, 'lote': lote_ref}), 201
    c.execute('SELECT id, producto, cantidad, fecha, estado, operador, COALESCE(presentacion,""), COALESCE(lote,"") FROM producciones ORDER BY fecha DESC LIMIT 50')
    prod = [{'id': r[0], 'lote': r[7] or f'PROD-{r[0]:05d}',
             'producto': r[1], 'cantidad': r[2], 'fecha': r[3],
             'estado': r[4], 'operador': r[5] or '', 'presentacion': r[6] or ''}
            for r in c.fetchall()]
    return jsonify({'producciones': prod})

@bp.route('/api/produccion/simular', methods=['POST'])
def simular_produccion():
    """Pre-check de stock FEFO + estimado de costo sin commitear ningun movimiento."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
    if not items:
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

@bp.route('/api/formulas/unlock', methods=['POST'])
def formulas_unlock():
    from config import FORMULA_PIN
    data = request.get_json() or {}
    pin = str(data.get('pin', ''))
    if pin == FORMULA_PIN:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'PIN incorrecto'}), 403

@bp.route('/api/formula/costo', methods=['POST'])
def calcular_costo_formula():
    """Calcula costo estimado de un batch sin verificar stock."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
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
    """Traza hacia atrás: dado un lote PT (PROD-00001) devuelve MPs consumidas, proveedor, fecha vencimiento."""
    conn = get_db(); c = conn.cursor()
    # Producción base
    c.execute("SELECT id, producto, cantidad, fecha, operador, observaciones FROM producciones WHERE lote=? OR id=?",
              (lote_ref, lote_ref.replace('PROD-','').lstrip('0') or 0))
    prod = c.fetchone()
    if not prod:
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
    return jsonify({
        'lote_ref': lote_ref, 'produccion': prod_data,
        'mps_consumidas': mps, 'detalle_lotes_mp': detalle_lotes,
        'despachos': despachos,
        'trazabilidad_completa': len(mps) > 0
    })

@bp.route('/api/trazabilidad/lote-mp/<path:lote_mp>')
def trazabilidad_lote_mp(lote_mp):
    """Traza hacia adelante: dado un lote de MP devuelve en qué producciones se usó y a qué clientes llegó."""
    conn = get_db(); c = conn.cursor()
    # Ingreso del lote
    c.execute("""SELECT material_id, material_nombre, cantidad, fecha, proveedor,
                        numero_oc, numero_factura, fecha_vencimiento, estado_lote
                 FROM movimientos WHERE lote=? AND tipo='Entrada' LIMIT 1""", (lote_mp,))
    ingreso = c.fetchone()
    if not ingreso:
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
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                 FROM movimientos GROUP BY material_nombre ORDER BY stock DESC""")
    items = [(r[0], r[1]) for r in c.fetchall() if r[1] and r[1] > 0]
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

@bp.route('/api/alertas', methods=['GET', 'POST'])
def handle_alertas():
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO alertas (material_id, material_nombre, stock_actual, stock_minimo, fecha, estado) VALUES (?,?,?,?,?,?)',
                  (data['material_id'], data['material_nombre'], data['stock_actual'],
                   data['stock_minimo'], datetime.now().isoformat(), 'Activa'))
        conn.commit()
        return jsonify({'message': 'Alerta creada'}), 201
    c.execute('SELECT material_nombre, stock_actual, stock_minimo, estado, fecha FROM alertas ORDER BY fecha DESC')
    alertas = [{'material_nombre': r[0], 'stock_actual': r[1], 'stock_minimo': r[2], 'estado': r[3], 'fecha': r[4]} for r in c.fetchall()]
    return jsonify({'alertas': alertas})

@bp.route('/api/alertas-reabastecimiento')
def alertas_reabastecimiento():
    conn = get_db(); c = conn.cursor()
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
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre")
    rows = c.fetchall()
    return jsonify({'items': [{'material_id':r[0],'material_nombre':r[1],'entradas':round(r[2] or 0,2),'salidas':round(r[3] or 0,2),'stock_actual':round(r[4] or 0,2)} for r in rows]})

@bp.route('/api/lotes')
def get_lotes():
    from datetime import date; hoy = date.today().isoformat()
    conn = get_db(); c = conn.cursor()
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
    rows = c.fetchall()
    result = []
    for r in rows:
        mid,mnm,lote,cant,fvenc,est,pos,prov,estado,inci,tipo,smin = r
        dias,alerta = None,'ok'
        if fvenc and len(str(fvenc))>=10:
            try:
                from datetime import datetime as dt2
                dias=(dt2.strptime(str(fvenc)[:10],'%Y-%m-%d').date()-dt2.strptime(hoy,'%Y-%m-%d').date()).days
                alerta='vencido' if dias<0 else ('critico' if dias<=30 else ('proximo' if dias<=90 else 'ok'))
            except (ValueError, TypeError):
                # Fecha mal formateada — dejar como 'ok' silencio aceptable
                # (no es crítico para el flujo de stock).
                pass
        result.append({'material_id':mid or '','nombre_inci':inci,'material_nombre':mnm or '',
                       'tipo':tipo,'proveedor':prov or '','stock_min_g':round(smin,1),
                       'lote':lote or '','cantidad_g':round(cant or 0,2),'cantidad_kg':round((cant or 0)/1000,3),
                       'estanteria':est or '','posicion':pos or '',
                       'fecha_vencimiento':str(fvenc)[:10] if fvenc else '',
                       'dias_para_vencer':dias,'estado_lote':estado or '','alerta':alerta})
    return jsonify({'lotes': result, 'total': len(result)})

@bp.route('/api/proveedores-unicos', methods=['GET'])
def proveedores_unicos():
    """Lista de proveedores únicos para autocompletado en edición de lote.

    Une los valores de movimientos.proveedor + maestro_mps.proveedor para
    sugerir solo nombres ya conocidos y evitar duplicados por typo
    ('Inchemical' vs 'INCHEMICAL'). Caso-sensitive para conservar el
    formato canónico que el usuario ya escogió.
    """
    u, err, code = _require_session()
    if err:
        return err, code
    conn = get_db()
    c = conn.cursor()
    proveedores = set()
    try:
        for row in c.execute("SELECT DISTINCT proveedor FROM movimientos "
                             "WHERE proveedor IS NOT NULL AND proveedor != ''"):
            proveedores.add(row[0].strip())
    except sqlite3.OperationalError:
        pass
    try:
        for row in c.execute("SELECT DISTINCT proveedor FROM maestro_mps "
                             "WHERE proveedor IS NOT NULL AND proveedor != ''"):
            proveedores.add(row[0].strip())
    except sqlite3.OperationalError:
        pass
    return jsonify({'proveedores': sorted(proveedores, key=lambda s: s.lower())})


@bp.route('/api/lotes/<material_id>/<path:lote>/proveedor', methods=['PUT'])
def editar_proveedor_lote(material_id, lote):
    """Corrige el proveedor de un lote y del catálogo de la MP.

    Caso de uso (jefe de produccion): "este lote en realidad lo trajo
    Lyphar, no Inchemical — corrijamos para no repetir el bug en futuras
    recepciones".

    Doble efecto:
      1. UPDATE movimientos SET proveedor=? WHERE material_id=? AND lote=?
      2. UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?

    Esto evita que la siguiente recepción de la misma MP herede el
    proveedor erroneo desde el catalogo. El audit_log captura el cambio
    para trazabilidad (snapshot del valor anterior + nuevo).

    Body JSON:
      proveedor: str (obligatorio, 2..120 chars, no solo espacios)

    Soporta lote vacío con placeholder _SIN_LOTE_ (igual que DELETE).
    """
    u, err, code = _require_planta_write()
    if err:
        return err, code

    d = request.json or {}
    nuevo_proveedor = (d.get('proveedor') or '').strip()
    if not nuevo_proveedor or len(nuevo_proveedor) < 2:
        return jsonify({
            'error': 'Proveedor invalido',
            'detail': 'Debe tener al menos 2 caracteres.'
        }), 400
    if len(nuevo_proveedor) > 120:
        return jsonify({
            'error': 'Proveedor demasiado largo',
            'detail': 'Maximo 120 caracteres.'
        }), 400

    sin_lote = (lote == '_SIN_LOTE_')

    conn = get_db()
    c = conn.cursor()

    # Snapshot valores actuales antes de cambiar
    if sin_lote:
        prov_anterior_row = c.execute(
            "SELECT MAX(proveedor) FROM movimientos "
            "WHERE material_id=? AND (lote IS NULL OR lote='')",
            (material_id,)
        ).fetchone()
    else:
        prov_anterior_row = c.execute(
            "SELECT MAX(proveedor) FROM movimientos "
            "WHERE material_id=? AND lote=?",
            (material_id, lote)
        ).fetchone()
    prov_anterior_lote = (prov_anterior_row[0] if prov_anterior_row else '') or ''

    cat_row = c.execute(
        "SELECT proveedor FROM maestro_mps WHERE codigo_mp=?",
        (material_id,)
    ).fetchone()
    if cat_row is None:
        return jsonify({
            'error': 'MP no encontrada',
            'detail': f'Codigo {material_id} no existe en maestro_mps'
        }), 404
    prov_anterior_cat = (cat_row[0] or '')

    # Update movimientos del lote
    if sin_lote:
        c.execute(
            "UPDATE movimientos SET proveedor=? "
            "WHERE material_id=? AND (lote IS NULL OR lote='')",
            (nuevo_proveedor, material_id)
        )
    else:
        c.execute(
            "UPDATE movimientos SET proveedor=? "
            "WHERE material_id=? AND lote=?",
            (nuevo_proveedor, material_id, lote)
        )
    movs_actualizados = c.rowcount

    # Update catalogo
    c.execute("UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?",
              (nuevo_proveedor, material_id))

    # Audit log
    try:
        import json as _json
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (u, 'EDITAR_PROVEEDOR_LOTE', 'movimientos+maestro_mps',
                   f'{material_id}/{"" if sin_lote else lote}',
                   _json.dumps({
                       'material_id': material_id,
                       'lote': '' if sin_lote else lote,
                       'proveedor_anterior_lote': prov_anterior_lote,
                       'proveedor_anterior_catalogo': prov_anterior_cat,
                       'proveedor_nuevo': nuevo_proveedor,
                       'movimientos_actualizados': movs_actualizados,
                   }, ensure_ascii=False),
                   request.remote_addr))
    except sqlite3.OperationalError:
        __import__('logging').getLogger('inventario').warning(
            "audit_log no disponible — editar_proveedor por %s sobre %s/%s "
            "no quedo registrado.", u, material_id, lote,
        )

    conn.commit()

    return jsonify({
        'ok': True,
        'message': (f'Proveedor actualizado a "{nuevo_proveedor}" en '
                    f'{movs_actualizados} movimiento(s) del lote y en el '
                    f'catalogo de {material_id}.'),
        'movimientos_actualizados': movs_actualizados,
        'proveedor_anterior_lote': prov_anterior_lote,
        'proveedor_anterior_catalogo': prov_anterior_cat,
        'proveedor_nuevo': nuevo_proveedor,
    }), 200


@bp.route('/api/lotes/<material_id>/<path:lote>', methods=['DELETE'])
def eliminar_lote(material_id, lote):
    """Elimina un lote completo por incoherencia (jefe de produccion).

    Hard-delete de todos los movimientos que comparten (material_id, lote).
    El bloque ENTRADA original + sus salidas asociadas se borran. Antes de
    borrar, se hace snapshot al audit_log con el estado completo del lote
    (cantidad neta, fecha venc, proveedor, # movs) + el motivo del usuario,
    para mantener trazabilidad de lo que se borro y por que.

    Body JSON:
      motivo: str (obligatorio, min 10 chars) - razon documentada

    Caso de uso: recepcion duplicada, codigo MP equivocado, lote registrado
    contra el material erroneo, etc. Para correcciones de cantidad usar
    'Ajustar' en su lugar (genera contra-movimiento, preserva historia).
    """
    u, err, code = _require_planta_write()
    if err:
        return err, code

    d = request.json or {}
    motivo = (d.get('motivo') or '').strip()
    if len(motivo) < 10:
        return jsonify({
            'error': 'Motivo obligatorio',
            'detail': 'Explica por que eliminas este lote (min 10 caracteres). '
                      'Esto queda en audit_log para trazabilidad.'
        }), 400

    # _SIN_LOTE_ es placeholder del frontend para movimientos sin lote
    # (lote NULL o ''). Hacemos match contra ambos.
    sin_lote = (lote == '_SIN_LOTE_')

    conn = get_db()
    c = conn.cursor()

    # Snapshot del lote antes de borrar — solo columnas garantizadas en
    # el schema actual de movimientos (ver database.py CREATE TABLE).
    cols_select = ("m.id, m.tipo, m.cantidad, m.fecha, m.proveedor, "
                   "m.fecha_vencimiento, m.operador, m.observaciones")
    if sin_lote:
        c.execute(f"""SELECT {cols_select}
                     FROM movimientos m
                     WHERE m.material_id=? AND (m.lote IS NULL OR m.lote='')
                     ORDER BY m.fecha ASC""", (material_id,))
    else:
        c.execute(f"""SELECT {cols_select}
                     FROM movimientos m
                     WHERE m.material_id=? AND m.lote=?
                     ORDER BY m.fecha ASC""", (material_id, lote))
    movs = c.fetchall()
    if not movs:
        return jsonify({
            'error': 'Lote no encontrado',
            'detail': f'No existen movimientos para {material_id} / {lote}'
        }), 404

    # Calcular saldo neto + nombre comercial para el log
    saldo_neto = sum(
        (mv[2] or 0) if mv[1] == 'Entrada' else -(mv[2] or 0)
        for mv in movs
    )
    nombre_row = c.execute(
        "SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?",
        (material_id,)
    ).fetchone()
    nombre_comercial = (nombre_row[0] if nombre_row else '') or material_id

    snapshot = {
        'material_id': material_id,
        'nombre_comercial': nombre_comercial,
        'lote': '' if sin_lote else lote,
        'saldo_neto_g_al_eliminar': round(saldo_neto, 2),
        'num_movimientos': len(movs),
        'fechas': [str(mv[3])[:10] for mv in movs if mv[3]],
        'proveedores': sorted({(mv[4] or '') for mv in movs if mv[4]}),
        'operadores':  sorted({(mv[6] or '') for mv in movs if mv[6]}),
        'motivo':      motivo,
    }

    # Audit log antes de borrar (sobrevive aunque algo falle abajo)
    try:
        import json as _json
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (u, 'ELIMINAR_LOTE', 'movimientos',
                   f'{material_id}/{lote}',
                   _json.dumps(snapshot, ensure_ascii=False),
                   request.remote_addr))
    except sqlite3.OperationalError:
        # audit_log no existe en deploy super-viejo — log en Sentry
        # via excepcion explicita y seguir.
        __import__('logging').getLogger('inventario').warning(
            "audit_log no disponible — eliminar_lote por %s sobre %s/%s "
            "no quedo registrado en BD. motivo=%s",
            u, material_id, lote, motivo,
        )

    # Hard delete de los movimientos del lote
    if sin_lote:
        c.execute("DELETE FROM movimientos WHERE material_id=? "
                  "AND (lote IS NULL OR lote='')", (material_id,))
    else:
        c.execute("DELETE FROM movimientos WHERE material_id=? AND lote=?",
                  (material_id, lote))
    deleted = c.rowcount
    conn.commit()

    return jsonify({
        'ok': True,
        'message': (f'Lote {lote} de {nombre_comercial} eliminado. '
                    f'{deleted} movimientos borrados. Saldo neto al momento '
                    f'de eliminar: {saldo_neto:.2f}g.'),
        'deleted_count': deleted,
        'snapshot': snapshot,
    }), 200


@bp.route('/api/maestro-mps', methods=['GET','POST'])
def handle_maestro():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        u, err, code = _require_planta_write()
        if err:
            return err, code
        d = request.json
        # tipo_material: validar contra lista permitida
        tipo_material = d.get('tipo_material', 'MP')
        if tipo_material not in ('MP', 'Envase Primario', 'Envase Secundario', 'Empaque'):
            tipo_material = 'MP'
        c.execute("""INSERT OR REPLACE INTO maestro_mps
                     (codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo,tipo_material)
                     VALUES (?,?,?,?,?,?,?)""",
                  (d['codigo_mp'], d.get('nombre_inci',''), d.get('nombre_comercial',''),
                   d.get('tipo',''), d.get('proveedor',''), d.get('stock_minimo',0),
                   tipo_material))
        conn.commit()
        return jsonify({'message': 'MP guardada', 'tipo_material': tipo_material}), 201
    # GET: filtro opcional por tipo_material via query param
    tipo_filter = (request.args.get('tipo_material') or '').strip()
    if tipo_filter and tipo_filter in ('MP', 'Envase Primario', 'Envase Secundario', 'Empaque'):
        c.execute("""SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo,
                            COALESCE(precio_referencia,0), COALESCE(tipo_material,'MP')
                     FROM maestro_mps WHERE activo=1 AND tipo_material=?
                     ORDER BY nombre_comercial""", (tipo_filter,))
    else:
        c.execute("""SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo,
                            COALESCE(precio_referencia,0), COALESCE(tipo_material,'MP')
                     FROM maestro_mps WHERE activo=1
                     ORDER BY nombre_comercial""")
    rows = c.fetchall()
    return jsonify({'mps': [
        {'codigo_mp':r[0], 'nombre_inci':r[1], 'nombre_comercial':r[2],
         'tipo':r[3], 'proveedor':r[4], 'stock_minimo':r[5],
         'precio_referencia':r[6], 'tipo_material':r[7]}
        for r in rows
    ]})

@bp.route('/api/maestro-mps/<codigo>')
def get_mp(codigo):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    r = c.fetchone()
    return jsonify({'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]}) if r else (jsonify({'error':'not found'}),404)

@bp.route('/api/maestro-mps/<codigo>/stock-minimo', methods=['PUT'])
def update_stock_minimo(codigo):
    """Actualiza el stock minimo de una MP."""
    d = request.json or {}
    nuevo_min = d.get('stock_minimo')
    if nuevo_min is None:
        return jsonify({'error': 'stock_minimo requerido'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET stock_minimo=? WHERE codigo_mp=?", (float(nuevo_min), codigo))
    if c.rowcount == 0:
        return jsonify({'error': 'MP no encontrada'}), 404
    conn.commit()
    return jsonify({'message': f'Stock minimo de {codigo} actualizado a {nuevo_min}'})

@bp.route('/api/maestro-mps/<codigo>/proveedor', methods=['PUT'])
def update_mp_proveedor(codigo):
    """Actualiza el proveedor asignado a una MP en maestro_mps.
    Sin auth — edicion de catalogo, no accion sensible de inventario.
    Al guardar, tambien registra el proveedor en proveedores (directorio Compras)."""
    d = request.json or {}
    proveedor = (d.get('proveedor') or '').strip()
    conn = get_db()
    c = conn.cursor()

    # 1. Actualizar maestro_mps
    c.execute("UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?", (proveedor, codigo))
    updated = c.rowcount

    if updated == 0:
        # MP no existe en maestro_mps — crearla con info de movimientos
        mov = c.execute(
            "SELECT material_nombre FROM movimientos WHERE material_id=? LIMIT 1", (codigo,)
        ).fetchone()
        nombre = mov[0] if mov else codigo
        c.execute("""
            INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, tipo, proveedor, stock_minimo, activo)
            VALUES (?, ?, '', 'MP', ?, 0, 1)
            ON CONFLICT(codigo_mp) DO UPDATE SET proveedor=excluded.proveedor
        """, (codigo, nombre, proveedor))

    # 2. Upsert en directorio de proveedores (tabla proveedores) si tiene nombre
    if proveedor:
        from datetime import datetime as _dt
        exists = c.execute(
            "SELECT nombre FROM proveedores WHERE nombre=?", (proveedor,)
        ).fetchone()
        if not exists:
            try:
                c.execute("""
                    INSERT INTO proveedores
                    (nombre, contacto, email, telefono, categoria, condiciones_pago,
                     nit, direccion, num_cuenta, tipo_cuenta, banco, concepto_compra, fecha_creacion)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (proveedor, '', '', '', 'mp', '30 dias',
                      '', '', '', '', '', 'Materias Primas', _dt.now().isoformat()))
            except Exception:
                pass  # Si ya existe por nombre con diferente case, ignorar

    conn.commit()
    return jsonify({'ok': True, 'codigo_mp': codigo, 'proveedor': proveedor})

@bp.route('/api/maestro-mps/<codigo>/mee-stock-minimo', methods=['PUT'])
def update_mee_stock_minimo(codigo):
    """Actualiza el stock minimo de un MEE."""
    d = request.json or {}
    nuevo_min = d.get('stock_minimo')
    if nuevo_min is None:
        return jsonify({'error': 'stock_minimo requerido'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE maestro_mee SET stock_minimo=? WHERE codigo=?", (float(nuevo_min), codigo))
    if c.rowcount == 0:
        return jsonify({'error': 'MEE no encontrado'}), 404
    conn.commit()
    return jsonify({'message': f'Stock minimo de {codigo} actualizado a {nuevo_min}'})

@bp.route('/api/consumo-manual', methods=['POST'])
def consumo_manual():
    """Registra consumo manual de una MP (ajuste por uso)."""
    d = request.json or {}
    codigo = (d.get('codigo_mp') or '').upper().strip()
    cantidad = float(d.get('cantidad') or 0)
    lote = d.get('lote', '')
    obs = d.get('observaciones', 'Consumo manual')
    operador = d.get('operador', session.get('compras_user', ''))
    if not codigo or cantidad <= 0:
        return jsonify({'error': 'Codigo y cantidad positiva requeridos'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    nombre = mp[0] if mp else codigo
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,lote,operador)
                 VALUES (?,?,?,'Salida',datetime('now'),?,?,?)""",
              (codigo, nombre, cantidad, obs, lote, operador))
    conn.commit()
    return jsonify({'message': f'Consumo de {cantidad} registrado para {nombre}'}), 201

@bp.route('/api/maestro-mps/<codigo>/archivar', methods=['PUT'])
def archivar_mp(codigo):
    """Archiva una MP (la marca como inactiva sin borrarla)."""
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET activo=0 WHERE codigo_mp=?", (codigo,))
    if c.rowcount == 0:
        return jsonify({'error': 'MP no encontrada'}), 404
    conn.commit()
    return jsonify({'message': f'MP {codigo} archivada exitosamente'})

@bp.route('/api/recepcion', methods=['POST'])
def registrar_recepcion():
    u, err, code = _require_planta_write()
    if err:
        return err, code
    d = request.json; codigo = (d.get('codigo_mp') or '').upper().strip()
    if not codigo: return jsonify({'error': 'Codigo MP requerido'}), 400
    cantidad_recibida = float(d.get('cantidad') or 0)
    if cantidad_recibida <= 0:
        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
    conn = get_db(); c = conn.cursor()
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
    # Actualizar precio_referencia en maestro_mps si viene precio.
    # Solo ignoramos si la columna 'ultima_act_precio' no existe (versión vieja).
    if precio_kg > 0:
        try:
            c.execute("UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now') WHERE codigo_mp=?", (precio_kg, codigo))
        except sqlite3.OperationalError as _e:
            if 'no such column' not in str(_e).lower():
                __import__('logging').getLogger('inventario').error(
                    "UPDATE precio_referencia falló para %s: %s", codigo, _e
                )
    lote = (d.get('lote') or '').strip()
    if not lote or lote.upper()=='AUTO':
        from datetime import date; lote = f"ESP{date.today().strftime('%y%m%d')}{codigo[-3:]}"
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,
                  lote,fecha_vencimiento,estanteria,posicion,proveedor,estado_lote,operador,
                  precio_kg,numero_factura,numero_oc)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (codigo,nombre,cantidad_recibida,'Entrada',datetime.now().isoformat(),
               d.get('observaciones','Ingreso MP'),lote,d.get('fecha_vencimiento',''),
               d.get('estanteria',''),d.get('posicion',''),proveedor,estado_lote,
               d.get('operador',''),precio_kg,numero_factura,numero_oc))
    mov_id = c.lastrowid
    # Log precio historico — solo ignorar si tabla no existe (legacy).
    if precio_kg > 0:
        try:
            c.execute("INSERT OR IGNORE INTO precios_mp_historico (codigo_mp,precio_kg,numero_factura,proveedor,fecha) VALUES (?,?,?,?,datetime('now'))",
                      (codigo, precio_kg, numero_factura, proveedor))
        except sqlite3.OperationalError as _e:
            if 'no such table' not in str(_e).lower():
                __import__('logging').getLogger('inventario').error(
                    "INSERT precios_mp_historico falló: %s", _e
                )
    # Cerrar OC si se referencia una
    oc_warning = None
    if numero_oc:
        try:
            c.execute("UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?",
                      (cantidad_recibida, lote, numero_oc, codigo))
            # verificar si todos los items de la OC estan recibidos
            c.execute("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=? AND (cantidad_g - cantidad_recibida_g) > 1", (numero_oc,))
            pendientes = c.fetchone()[0]
            if pendientes == 0:
                c.execute("UPDATE ordenes_compra SET estado='RECIBIDA',fecha_recepcion=datetime('now'),recibido_por=? WHERE numero_oc=?",
                          (d.get('operador',''), numero_oc))
        except Exception as oc_err:
            # Log but don't fail the reception — OC can be reconciled manually
            print(f'[WARN] OC update failed for {numero_oc}: {oc_err}', flush=True)
            oc_warning = f'OC {numero_oc} no pudo actualizarse automaticamente — verificar manualmente'
    conn.commit()
    msg = f'{nombre} ingresada. Lote: {lote}'
    if cuarentena: msg += ' — En CUARENTENA (pendiente aprobacion QC)'
    if numero_oc and not oc_warning: msg += f' | OC {numero_oc} actualizada'
    if oc_warning: msg += f' | ⚠ {oc_warning}'
    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':cantidad_recibida,'cuarentena':cuarentena,'oc_warning':oc_warning}), 201

@bp.route('/api/lotes/cuarentena', methods=['GET'])
def lotes_cuarentena():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.lote, m.cantidad,
                      m.fecha, m.proveedor, m.numero_factura, m.numero_oc, m.observaciones,
                      mp.nombre_inci, m.estado_lote
               FROM movimientos m
               LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
               WHERE m.estado_lote IN ('CUARENTENA','CUARENTENA_EXTENDIDA') AND m.tipo='Entrada'
               ORDER BY m.fecha DESC""")
    rows = c.fetchall()
    cols = ['id','codigo_mp','nombre','lote','cantidad','fecha','proveedor','numero_factura','numero_oc','observaciones','nombre_inci','estado_lote']
    return jsonify([dict(zip(cols,r)) for r in rows])

@bp.route('/api/lotes/liberar', methods=['POST'])
def liberar_lote():
    # Equipo de Calidad (CALIDAD_USERS) y admins pueden liberar lotes —
    # antes solo era admins, lo que bloqueaba el flujo legítimo de QC.
    u, err, code = _require_qc()
    if err:
        return err, code
    d = request.json or {}
    mov_id = d.get('id')
    accion = (d.get('accion') or 'APROBAR').upper()
    if accion not in ('APROBAR','RECHAZAR'):
        return jsonify({'error': 'Accion debe ser APROBAR o RECHAZAR'}), 400
    nuevo_estado = 'VIGENTE' if accion == 'APROBAR' else 'RECHAZADO'
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=? AND estado_lote='CUARENTENA'", (nuevo_estado, mov_id))
    if c.rowcount == 0:
        return jsonify({'error': 'Lote no encontrado o ya procesado'}), 404
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','?'), f'LOTE_{accion}', 'movimientos',
               str(mov_id), f'Lote liberado: {accion}', request.remote_addr))
    conn.commit()
    return jsonify({'message': f'Lote {accion.lower()}ado correctamente', 'estado': nuevo_estado})

# /api/trazabilidad/<lote> eliminado — duplicado de /api/trazabilidad/lote/<path:lote>
# que es más completo (también busca despachos). Mantener el de path por
# consistencia con lotes que contienen '/' o caracteres especiales.

# ── CONTEO CICLICO BDG-PRO-002 ──────────────────────────────────
# Soporta filtro por tipo_material (MP / Envase Primario / Envase Secundario /
# Empaque) — clave para inventario cíclico de E&E (envase y empaque).
# Sin filtro = todo. Filtro = solo materiales del tipo indicado.
@bp.route('/api/conteo/estanterias', methods=['GET'])
def conteo_estanterias():
    tipo = (request.args.get('tipo_material') or '').strip()
    conn = get_db(); c = conn.cursor()
    if tipo in ('MP', 'Envase Primario', 'Envase Secundario', 'Empaque'):
        c.execute("""SELECT COALESCE(NULLIF(m.estanteria,''),'Sin estanteria') as est,
                            COUNT(DISTINCT m.material_id) as total_mps,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_total
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id = mp.codigo_mp
                     WHERE COALESCE(mp.tipo_material,'MP') = ?
                     GROUP BY est ORDER BY est""", (tipo,))
    else:
        c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est,
                            COUNT(DISTINCT material_id) as total_mps,
                            SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_total
                     FROM movimientos GROUP BY est ORDER BY est""")
    rows = c.fetchall()
    return jsonify([
        {'estanteria': r[0], 'total_mps': r[1], 'stock_total': round(r[2] or 0, 1)}
        for r in rows
    ])

@bp.route('/api/conteo/materiales', methods=['GET'])
def conteo_materiales_estanteria():
    est = request.args.get('estanteria', '')
    tipo = (request.args.get('tipo_material') or '').strip()
    conn = get_db(); c = conn.cursor()
    type_filter = (
        " AND COALESCE(mp.tipo_material,'MP') = ?"
        if tipo in ('MP', 'Envase Primario', 'Envase Secundario', 'Empaque')
        else ""
    )
    type_args = (tipo,) if type_filter else ()
    if est and est != 'Sin estanteria':
        c.execute(f"""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            MAX(m.estanteria) as estanteria,
                            COALESCE(mp.tipo_material,'MP') as tipo_material
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE m.estanteria=?{type_filter}
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""", (est,) + type_args)
    else:
        c.execute(f"""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            '' as estanteria,
                            COALESCE(mp.tipo_material,'MP') as tipo_material
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE (m.estanteria IS NULL OR m.estanteria=''){type_filter}
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""", type_args)
    rows = c.fetchall()
    cols = ['codigo_mp','nombre','inci','precio_ref','stock_sistema','estanteria','tipo_material']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/conteo/iniciar', methods=['POST'])
def conteo_iniciar():
    u, err, code = _require_planta_write()
    if err:
        return err, code
    d = request.json or {}
    est = d.get('estanteria', '')
    responsable = d.get('responsable', session.get('compras_user',''))
    from datetime import date
    conn = get_db(); c = conn.cursor()
    # ── Verificar si ya existe un conteo ABIERTO para esta estantería ──────────
    c.execute("SELECT id, numero FROM conteos_fisicos WHERE estanteria=? AND estado='Abierto' ORDER BY id DESC LIMIT 1", (est,))
    existing = c.fetchone()
    if existing:
        return jsonify({'conteo_id': existing[0], 'numero': existing[1],
                        'message': 'Conteo retomado', 'resuming': True})
    numero = 'CNT-' + date.today().strftime('%Y%m%d') + '-' + est.replace(' ','')[:6].upper()
    # Si el número ya existe (mismo día), agregar sufijo incremental
    c.execute("SELECT COUNT(*) FROM conteos_fisicos WHERE numero LIKE ?", (numero + '%',))
    suffix = c.fetchone()[0]
    if suffix > 0:
        numero = numero + f'-{suffix+1}'
    try:
        c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) VALUES (?,datetime('now'),'Abierto',?,?,'Ciclico')",
                  (numero, responsable, est))
        conteo_id = c.lastrowid
        conn.commit()
        return jsonify({'conteo_id': conteo_id, 'numero': numero, 'message': 'Conteo iniciado', 'resuming': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/conteo/programacion', methods=['GET'])
def conteo_programacion():
    """Retorna la programación cíclica automática.

    Modo MP (default, sin filtro): rotación por estantería.
    Modo E&E (?tipo_material=Empaque|Envase Primario|Envase Secundario):
        rotación de 3 ITEMS específicos por semana ISO. Como E&E no tiene
        ubicación física, en lugar de elegir estantería se eligen 3 ítems
        determinísticos para la semana — el equipo busca los 3 y los cuenta.

    Determinístico: la misma semana siempre devuelve los mismos 3 ítems.
    Rota por TODOS los ítems del tipo a lo largo del año.
    """
    tipo = (request.args.get('tipo_material') or '').strip()
    if tipo in ('Envase Primario', 'Envase Secundario', 'Empaque'):
        return _conteo_programacion_items(tipo)
    # Modo MP por estantería (legacy)
    from datetime import date, timedelta
    import math
    conn = get_db(); c = conn.cursor()
    # Obtener todas las estanterias con stock positivo desde movimientos
    c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est
                 FROM movimientos
                 GROUP BY est
                 HAVING SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) > 0
                 ORDER BY est""")
    estanterias = [r[0] for r in c.fetchall()]
    if not estanterias:
        return jsonify({'semanas': [], 'total_estanterias': 0})
    n = len(estanterias)
    hoy = date.today()
    # Lunes de la semana actual
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    semanas = []
    for delta in range(-1, 5):  # semana pasada + actual + próximas 4
        lunes = lunes_actual + timedelta(weeks=delta)
        semana_iso = lunes.isocalendar()[1]
        anio = lunes.isocalendar()[0]
        idx = (semana_iso - 1) % n
        est = estanterias[idx]
        # Verificar si ya hay conteo para esa semana + estantería
        fecha_fin = lunes + timedelta(days=6)
        c.execute("""SELECT id, numero, estado FROM conteos_fisicos
                     WHERE estanteria=? AND fecha_inicio BETWEEN ? AND ?
                     ORDER BY id DESC LIMIT 1""",
                  (est, lunes.isoformat(), fecha_fin.isoformat() + ' 23:59:59'))
        conteo = c.fetchone()
        semanas.append({
            'semana': semana_iso,
            'anio': anio,
            'lunes': lunes.isoformat(),
            'estanteria': est,
            'es_actual': delta == 0,
            'conteo_id': conteo[0] if conteo else None,
            'conteo_numero': conteo[1] if conteo else None,
            'conteo_estado': conteo[2] if conteo else 'Pendiente',
        })
    return jsonify({'semanas': semanas, 'total_estanterias': n, 'estanterias': estanterias})


def _conteo_programacion_items(tipo_material):
    """Programación cíclica para E&E: 3 ítems por semana, deterministas.

    El stock de Envase y Empaque vive en `maestro_mee` (NO en maestro_mps).
    No tiene localización física específica como las MPs, por eso la rotación
    es por ÍTEM en lugar de por estantería.

    Algoritmo:
      1. Lista ordenada de items activos en maestro_mee filtrados por
         categoría según el tipo solicitado:
           'Envase Primario'   → categoria LIKE '%envase%'  (frasco, tubo, gotero)
           'Envase Secundario' → categoria LIKE '%envase%'  (caja, display)
           'Empaque'           → categoria LIKE '%empaque%' (etiqueta, sello)
         Si solo hay un valor 'Envase' genérico, los 3 botones muestran lo
         mismo (es lo que el user pidió: rotar todos los E&E).
      2. Para una semana ISO N: índices [(3*N) % L, (3*N+1) % L, (3*N+2) % L]
         donde L = total ítems. Garantiza:
           - Mismos 3 ítems para la misma semana (determinístico).
           - Rotación completa: tras ⌈L/3⌉ semanas se han contado todos.
           - Sin solapamiento: 3 ítems distintos cada semana.
      3. Devuelve esquema compatible con UI: 'estanteria' lleva etiqueta
         sintética "E&E-<tipo>-S<sem>", 'items_programados' los códigos+nombres.
    """
    from datetime import date, timedelta

    conn = get_db(); c = conn.cursor()
    # Universo: items activos en maestro_mee. Filtramos por categoría según
    # el tipo solicitado. Si no hay distinción real en la categoría, devuelve
    # todos (es lo que el user quiere: que el jefe de planta vea cualquier
    # item de E&E rotando, no le importa la sub-clasificación rígida).
    if 'empaque' in tipo_material.lower():
        cat_pattern = '%empaque%'
    else:
        # Envase Primario o Envase Secundario → ambos toman de categoria
        # tipo "Envase" (sin distinguir, porque el catálogo no lo hace).
        cat_pattern = '%envase%'

    c.execute("""SELECT codigo, descripcion
                 FROM maestro_mee
                 WHERE LOWER(COALESCE(estado,''))='activo'
                   AND LOWER(COALESCE(categoria,'')) LIKE ?
                 ORDER BY codigo""", (cat_pattern,))
    items = c.fetchall()
    # Fallback: si la categoría no calza (ej: usuario pone categoría diferente
    # o solo tiene 'Otro'), devolver TODOS los items activos. El user prefiere
    # tener algo que rotar antes que un mensaje vacío.
    if not items:
        c.execute("""SELECT codigo, descripcion FROM maestro_mee
                     WHERE LOWER(COALESCE(estado,''))='activo'
                     ORDER BY codigo""")
        items = c.fetchall()

    if not items:
        # Diagnóstico contra maestro_mee (que es la tabla del stock de E&E)
        try:
            stats = c.execute("""
                SELECT COALESCE(NULLIF(TRIM(categoria),''),'(sin categoria)') AS cat,
                       COUNT(*) AS total
                FROM maestro_mee
                GROUP BY cat ORDER BY total DESC
            """).fetchall()
            cats_existentes = [{'tipo': r[0], 'total': r[1]} for r in stats]
            total_catalogo = sum(r['total'] for r in cats_existentes)
        except Exception:
            cats_existentes, total_catalogo = [], 0
        return jsonify({
            'semanas': [],
            'total_items': 0,
            'tipo_material': tipo_material,
            'mensaje': f"No hay items de E&E activos en maestro_mee para '{tipo_material}'.",
            'diagnostico': {
                'total_catalogo': total_catalogo,
                'sin_clasificar': 0,
                'tipos_existentes': cats_existentes,
                'accion_sugerida': (
                    "El catálogo de Envase y Empaque (maestro_mee) está vacío "
                    "o todos los items están en estado Inactivo. Ve a Planta → "
                    "Maestro de Envase y Empaque y agrega/activa los items que "
                    "tu equipo debe contar cíclicamente."
                ),
            }
        })

    L = len(items)
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    semanas = []

    for delta in range(-1, 5):  # semana pasada + actual + próximas 4
        lunes = lunes_actual + timedelta(weeks=delta)
        semana_iso = lunes.isocalendar()[1]
        anio = lunes.isocalendar()[0]
        # Combinamos año + semana para que la rotación no se repita igual cada año
        seed = anio * 100 + semana_iso
        # 3 índices distintos, deterministas
        indices = [(3 * seed + offset) % L for offset in range(3)]
        # Si L < 3, evitar duplicados
        if L < 3:
            indices = list(range(L))
        items_semana = [
            {'codigo_mp': items[i][0], 'nombre': items[i][1]}
            for i in indices
        ]

        # Buscar conteo asociado de la semana (estanteria=etiqueta sintética)
        etiqueta = f"E&E-{tipo_material}-S{semana_iso:02d}"
        fecha_fin = lunes + timedelta(days=6)
        c.execute("""SELECT id, numero, estado FROM conteos_fisicos
                     WHERE estanteria=? AND fecha_inicio BETWEEN ? AND ?
                     ORDER BY id DESC LIMIT 1""",
                  (etiqueta, lunes.isoformat(), fecha_fin.isoformat() + ' 23:59:59'))
        conteo = c.fetchone()

        semanas.append({
            'semana': semana_iso,
            'anio': anio,
            'lunes': lunes.isoformat(),
            'estanteria': etiqueta,  # campo legacy compatible con UI
            'tipo_material': tipo_material,
            'items_programados': items_semana,
            'es_actual': delta == 0,
            'conteo_id': conteo[0] if conteo else None,
            'conteo_numero': conteo[1] if conteo else None,
            'conteo_estado': conteo[2] if conteo else 'Pendiente',
        })

    return jsonify({
        'semanas': semanas,
        'total_items': L,
        'tipo_material': tipo_material,
        'modo': 'items',  # vs 'estanteria' del modo MP
    })


@bp.route('/api/conteo/<int:conteo_id>/guardar', methods=['POST'])
def conteo_guardar(conteo_id):
    d = request.json or {}
    items = d.get('items', [])
    UMBRAL_ESCALA = 0.05  # 5% -> escala a gerencia (BDG-PRO-002 num 8)
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT estado FROM conteos_fisicos WHERE id=?", (conteo_id,))
    row = c.fetchone()
    if not row or row[0] != 'Abierto':
        return jsonify({'error': 'Conteo no encontrado o ya cerrado'}), 400

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
    conn.commit()
    return jsonify({'message': 'Conteo guardado', 'items_con_diferencia': items_con_diff})

@bp.route('/api/conteo/<int:conteo_id>/cerrar', methods=['POST'])
def conteo_cerrar(conteo_id):
    """Cierra un conteo físico aplicando ajustes automáticos.

    Flujo deseado por el dueño del negocio:
      - Diferencias <5% del stock sistema → AUTO-AJUSTE: se inserta movimiento
        de Entrada/Salida que sincroniza el kardex con la realidad física.
      - Diferencias >=5% → NO se aplica ajuste. Se marca como pendiente de
        gerencia y se genera ALERTA en panel (BDG-PRO-002 num 8). Gerencia
        revisa el caso (puede ser hurto, mal pesaje, error de fórmula) y
        aprueba manualmente con /api/conteo/<id>/ajustar.

    Trazabilidad: cada auto-ajuste queda en `movimientos` con lote
    'AJUSTE-CICLICO-<conteo_id>' y observaciones que indican causa.
    """
    user = session.get('compras_user','') or 'sistema'
    conn = get_db(); c = conn.cursor()

    c.execute("SELECT estado FROM conteos_fisicos WHERE id=?", (conteo_id,))
    cf = c.fetchone()
    if not cf:
        return jsonify({'error': 'Conteo no encontrado'}), 404
    if cf[0] == 'Cerrado':
        return jsonify({'error': 'El conteo ya estaba cerrado'}), 400

    # ── Items con diferencia ────────────────────────────────────────────────
    c.execute("""SELECT id, codigo_mp, nombre_mp, stock_sistema, stock_fisico,
                        diferencia, estanteria, causa_diferencia, valor_diferencia,
                        requiere_gerencia, aprobado_gerencia, ajuste_aplicado
                 FROM conteo_items
                 WHERE conteo_id=? AND COALESCE(diferencia,0) <> 0""", (conteo_id,))
    items_con_diff = c.fetchall()

    auto_ajustados = []
    pendientes_gerencia_lista = []

    try:
        for it in items_con_diff:
            (it_id, codigo, nombre, stock_sis, stock_fis, diff, estant,
             causa, valor, req_ger, aprob_ger, ya_ajustado) = it
            if ya_ajustado:
                continue
            diff = float(diff or 0)
            if diff == 0:
                continue
            tipo_mov = 'Entrada' if diff > 0 else 'Salida'

            if req_ger and not aprob_ger:
                # Diferencia significativa — NO ajustar. Pendiente de gerencia.
                pendientes_gerencia_lista.append({
                    'item_id': it_id, 'codigo_mp': codigo, 'nombre': nombre,
                    'stock_sistema': stock_sis, 'stock_fisico': stock_fis,
                    'diferencia_g': diff, 'valor_diferencia': valor,
                    'causa': causa, 'estanteria': estant,
                })
                continue

            # Auto-ajuste para diferencias menores
            obs = (f"Ajuste automático conteo cíclico #{conteo_id} | "
                   f"Causa: {causa or 'no indicada'} | Cerrado por: {user}")
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, estanteria, estado_lote, operador)
                         VALUES (?,?,?,?,datetime('now'),?,?,?,'VIGENTE',?)""",
                      (codigo, nombre, abs(diff), tipo_mov, obs,
                       f'AJUSTE-CICLICO-{conteo_id}', estant or '', user))
            c.execute("UPDATE conteo_items SET ajuste_aplicado=1 WHERE id=?", (it_id,))
            try:
                c.execute("""INSERT INTO audit_log
                             (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                             VALUES (?,?,?,?,?,?,datetime('now'))""",
                          (user, 'AJUSTE_INVENTARIO_AUTO', 'conteo_items', str(it_id),
                           f'MP:{codigo} Diff:{diff}g Auto:<5% Causa:{causa or "n/a"}',
                           request.remote_addr if request else ''))
            except sqlite3.OperationalError:
                pass  # audit_log puede no existir en versiones viejas
            auto_ajustados.append({
                'item_id': it_id, 'codigo_mp': codigo, 'nombre': nombre,
                'diferencia_g': diff, 'tipo': tipo_mov,
            })

        c.execute("""UPDATE conteos_fisicos
                     SET estado='Cerrado', fecha_cierre=datetime('now')
                     WHERE id=?""", (conteo_id,))
        conn.commit()
    except Exception as _e:
        conn.rollback()
        __import__('logging').getLogger('inventario').error(
            "conteo_cerrar(%s) FALLÓ — rollback aplicado: %s",
            conteo_id, _e, exc_info=True
        )
        return jsonify({
            'error': 'Falla transaccional al cerrar conteo',
            'detalle': str(_e),
            'rollback': 'aplicado — ningún ajuste se persistió',
        }), 500

    # Email de alerta a gerencia si hay pendientes (best-effort, no bloquea).
    # Se envía a EMAIL_GERENCIA (env var, separado del buzón de facturación).
    # Soporta múltiples destinatarios separados por coma.
    # Si EMAIL_GERENCIA no está configurado, fallback a EMAIL_REMITENTE para
    # no perder el alerta — pero el operador debe configurarlo en Render.
    if pendientes_gerencia_lista:
        try:
            from notificaciones import SistemaNotificaciones
            import os as _os
            sn = SistemaNotificaciones()
            if sn.email_remitente and sn.contraseña:
                gerencia_raw = _os.environ.get('EMAIL_GERENCIA', '').strip()
                if gerencia_raw:
                    destinatarios = [e.strip() for e in gerencia_raw.split(',')
                                     if e.strip() and '@' in e.strip()]
                else:
                    destinatarios = [sn.email_remitente]
                total_valor = sum(p.get('valor_diferencia') or 0 for p in pendientes_gerencia_lista)
                lista_html = ''.join([
                    f"<li><strong>{p['codigo_mp']}</strong> — {p['nombre']}: "
                    f"diff <strong>{p['diferencia_g']:+.0f}g</strong> "
                    f"(${(p.get('valor_diferencia') or 0):,.0f}) — {p.get('causa') or 'sin causa'}</li>"
                    for p in pendientes_gerencia_lista[:20]
                ])
                body = f"""<html><body style="font-family:Arial,sans-serif">
                <h2 style="color:#c62828">Alerta — Conteo cíclico requiere aprobación Gerencia</h2>
                <p>Conteo <strong>#{conteo_id}</strong> cerrado por <strong>{user}</strong>.</p>
                <p>{len(pendientes_gerencia_lista)} item(s) con diferencia &gt;5% no fueron ajustados
                automáticamente. Valor total estimado: <strong>${total_valor:,.0f}</strong>.</p>
                <ul>{lista_html}</ul>
                <p>Ingresa a /planta y aprueba/rechaza cada item para que el ajuste se aplique al kardex.</p>
                </body></html>"""
                sn.enviar_en_background(
                    sn._enviar_email,
                    asunto=f"[HHA] Conteo cíclico #{conteo_id}: {len(pendientes_gerencia_lista)} items requieren Gerencia",
                    body=body,
                    destinatarios=destinatarios,
                )
        except Exception as _e_mail:
            __import__('logging').getLogger('inventario').error(
                "Email alerta gerencia conteo %s falló: %s", conteo_id, _e_mail
            )

    msg_parts = [f'Conteo #{conteo_id} cerrado.']
    if auto_ajustados:
        msg_parts.append(f'{len(auto_ajustados)} ajuste(s) automático(s) aplicado(s) al kardex.')
    if pendientes_gerencia_lista:
        msg_parts.append(
            f'ATENCIÓN: {len(pendientes_gerencia_lista)} item(s) con diferencia >5% '
            f'pendientes de aprobación Gerencia General (BDG-PRO-002).')
    return jsonify({
        'message': ' '.join(msg_parts),
        'auto_ajustados': auto_ajustados,
        'pendientes_gerencia': pendientes_gerencia_lista,
        'total_items_ajustados': len(auto_ajustados),
        'total_pendientes': len(pendientes_gerencia_lista),
    })


@bp.route('/api/conteo/alertas-gerencia', methods=['GET'])
def conteo_alertas_gerencia():
    """Lista de items con diferencia >5% pendientes de aprobación de gerencia.

    Útil para que gerencia tenga un dashboard de "qué decisiones están
    esperándome" sin tener que abrir conteo por conteo.
    """
    user = session.get('compras_user','')
    if not user:
        return jsonify({'error': 'No autenticado'}), 401
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT cf.id AS conteo_id, cf.numero, cf.estanteria, cf.fecha_cierre,
                        ci.id AS item_id, ci.codigo_mp, ci.nombre_mp,
                        ci.stock_sistema, ci.stock_fisico, ci.diferencia,
                        ci.causa_diferencia, ci.valor_diferencia,
                        ci.aprobado_gerencia, ci.aprobado_gerencia_por,
                        ci.ajuste_aplicado
                 FROM conteo_items ci
                 JOIN conteos_fisicos cf ON ci.conteo_id = cf.id
                 WHERE ci.requiere_gerencia=1 AND ci.ajuste_aplicado=0
                 ORDER BY ABS(ci.valor_diferencia) DESC LIMIT 200""")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    total_valor = sum(r.get('valor_diferencia') or 0 for r in rows)
    return jsonify({
        'pendientes': rows,
        'total': len(rows),
        'total_valor_diferencia': round(total_valor, 0),
    })

@bp.route('/api/conteo/<int:conteo_id>/ajustar', methods=['POST'])
def conteo_ajustar(conteo_id):
    user = session.get('compras_user','')
    d = request.json or {}
    item_id = d.get('item_id')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT ci.*, cf.estado FROM conteo_items ci JOIN conteos_fisicos cf ON ci.conteo_id=cf.id WHERE ci.id=?", (item_id,))
    item = c.fetchone()
    if not item:
        return jsonify({'error': 'Item no encontrado'}), 404
    cols = [desc[0] for desc in c.description]
    it = dict(zip(cols, item))
    if it['requiere_gerencia'] and not it['aprobado_gerencia']:
        if user not in ADMIN_USERS:
            return jsonify({'error': 'Diferencia >5% requiere aprobacion Gerencia General (BDG-PRO-002)'}), 403
        c.execute("UPDATE conteo_items SET aprobado_gerencia=1,aprobado_gerencia_por=? WHERE id=?", (user, item_id))
    diff = float(it['diferencia'])
    if diff == 0:
        return jsonify({'message': 'Sin diferencia, no se requiere ajuste'})
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
    conn.commit()
    return jsonify({'message': f'Ajuste aplicado: {tipo_mov} de {abs(diff):.0f}g para {it["nombre_mp"]}'})

@bp.route('/api/conteo/historial', methods=['GET'])
def conteo_historial():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT cf.id, cf.numero, cf.estanteria, cf.fecha_inicio, cf.fecha_cierre,
                        cf.estado, cf.responsable, cf.total_items, cf.items_diferencia,
                        COUNT(CASE WHEN ci.requiere_gerencia=1 THEN 1 END) as items_gerencia
                 FROM conteos_fisicos cf
                 LEFT JOIN conteo_items ci ON cf.id=ci.conteo_id
                 GROUP BY cf.id ORDER BY cf.fecha_inicio DESC LIMIT 50""")
    rows = c.fetchall()
    cols = ['id','numero','estanteria','fecha_inicio','fecha_cierre','estado','responsable','total_items','items_diferencia','items_gerencia']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/conteo/<int:conteo_id>/items', methods=['GET'])
def conteo_get_items(conteo_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM conteo_items WHERE conteo_id=? ORDER BY codigo_mp", (conteo_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/lotes/cc-review', methods=['POST'])
def cc_review():
    # Antes era hardcoded {hernando} + ADMIN_USERS. Ahora usa CALIDAD_USERS
    # (laura, miguel, yuliel) + ADMIN — consistente con la matriz de permisos.
    user, err, code = _require_qc()
    if err:
        return err, code
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
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, material_id, lote, estado_lote FROM movimientos WHERE id=?", (mov_id,))
    mov = c.fetchone()
    if not mov:
        return jsonify({'error': 'Lote no encontrado'}), 404
    if mov[3] not in ('CUARENTENA', 'CUARENTENA_EXTENDIDA'):
        return jsonify({'error': 'Lote no esta en cuarentena'}), 400
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
        except sqlite3.OperationalError as _e:
            # Si la tabla solicitudes_compra cambió de schema, no romper el rechazo QC.
            __import__('logging').getLogger('inventario').error(
                "Auto-creación de solicitud devolución falló: %s", _e
            )
    conn.commit()
    msgs = {'APROBADO': 'Lote APROBADO. Disponible para produccion.',
            'RECHAZADO': 'Lote RECHAZADO. Notificacion creada en Compras.',
            'CUARENTENA_EXTENDIDA': 'CUARENTENA EXTENDIDA. Maximo 5 dias para definicion.'}
    return jsonify({'message': msgs.get(estado_final,''), 'estado': estado_final})

@bp.route('/api/movimientos/<int:mov_id>/anular', methods=['POST'])
def anular_movimiento(mov_id):
    """Anula un movimiento generando un contra-movimiento. Requiere autenticacion."""
    user = session.get('compras_user', '')
    d = request.json or {}
    motivo = d.get('motivo', '').strip()
    if not motivo:
        return jsonify({'error': 'Motivo de anulacion requerido'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT m.*, mp.nombre FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id = mp.codigo_mp
                 WHERE m.id=?""", (mov_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Movimiento no encontrado'}), 404
    cols = [d[0] for d in c.description]
    mov = dict(zip(cols, row))
    # Verificar que no esté ya anulado
    if mov.get('observaciones','').startswith('[ANULADO]'):
        return jsonify({'error': 'Movimiento ya anulado'}), 400
    # Solo admin puede anular movimientos de otros usuarios
    if user not in ADMIN_USERS and mov.get('responsable','') != user:
        return jsonify({'error': 'Solo puedes anular tus propios movimientos o ser administrador'}), 403
    # Generar contra-movimiento (invierte el tipo)
    tipo_inv = 'Salida' if mov['tipo'] == 'Entrada' else 'Entrada'
    obs_contra = f'[ANULACION] del movimiento #{mov_id} — {motivo} — por {user}'
    c.execute("""INSERT INTO movimientos
                 (material_id, tipo, cantidad, unidad, lote_ref, responsable, observaciones, fecha)
                 VALUES (?,?,?,?,?,?,?,datetime('now'))""",
              (mov['material_id'], tipo_inv, mov['cantidad'], mov.get('unidad','g'),
               mov.get('lote_ref',''), user, obs_contra))
    # Marcar original como anulado
    c.execute("UPDATE movimientos SET observaciones=? WHERE id=?",
              ('[ANULADO] ' + (mov.get('observaciones') or ''), mov_id))
    # Registrar en audit_log
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (user, 'ANULAR_MOVIMIENTO', 'movimientos', str(mov_id),
               f'Anulado mov #{mov_id} ({mov["tipo"]} {mov["cantidad"]}g de {mov["material_id"]}) — {motivo}',
               request.remote_addr))
    conn.commit()
    return jsonify({'ok': True, 'message': f'Movimiento #{mov_id} anulado. Contra-movimiento generado.',
                    'tipo_contramovimiento': tipo_inv})

@bp.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    """OPERACIÓN PELIGROSA: borra TODOS los movimientos de inventario.

    Solo admins. Triple confirmación:
      1. Sesión debe ser ADMIN_USERS
      2. JSON.confirmacion == 'BORRAR_TODO_INVENTARIO_AHORA' (no solo 'BORRAR')
      3. JSON.fecha_actual == fecha de hoy (YYYY-MM-DD) — anti copy-paste accidental
    Antes de ejecutar: snapshot a backup_log + log de seguridad.
    """
    user = session.get('compras_user', '')
    if not user or user not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado. Solo administradores.'}), 403

    d = request.json or {}
    if d.get('confirmacion', '') != 'BORRAR_TODO_INVENTARIO_AHORA':
        return jsonify({
            'error': 'confirmacion debe ser exactamente "BORRAR_TODO_INVENTARIO_AHORA"',
            'hint': 'Anti copy-paste accidental. Esta operación borra TODOS los movimientos.'
        }), 400

    from datetime import date as _date
    hoy = _date.today().isoformat()
    if d.get('fecha_actual', '') != hoy:
        return jsonify({
            'error': f'fecha_actual debe ser "{hoy}" (formato YYYY-MM-DD)',
            'hint': 'Doble confirmación: la fecha de HOY debe coincidir.'
        }), 400

    # Forzar backup antes de borrar — recuperabilidad obligatoria
    try:
        from backup import do_backup
        bk_result = do_backup(triggered_by=f"pre-reset:{user}")
        if not bk_result.get('ok') and not bk_result.get('skipped'):
            return jsonify({
                'error': 'No se pudo crear backup pre-reset. Operación abortada.',
                'detail': bk_result.get('error', '')[:200]
            }), 500
        backup_filename = bk_result.get('filename', '(skipped — otro en curso)')
    except Exception as e:
        return jsonify({
            'error': 'Backup pre-reset falló. Operación abortada.',
            'detail': str(e)[:200]
        }), 500

    # Log de seguridad ANTES (en caso de crash queda traza del intento)
    from auth import _log_sec, _client_ip
    _log_sec("inventario_reset_INICIADO", user, _client_ip(),
             f"backup={backup_filename}")

    conn = get_db(); c = conn.cursor()
    rows_deleted = c.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
    c.execute("DELETE FROM movimientos")
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (user, 'RESET_MOVIMIENTOS', 'movimientos', 'ALL',
               f'Borrados {rows_deleted} movimientos. Backup pre-reset: {backup_filename}',
               _client_ip()))
    conn.commit()

    _log_sec("inventario_reset_COMPLETADO", user, _client_ip(),
             f"deleted={rows_deleted} backup={backup_filename}")

    return jsonify({
        'ok': True,
        'message': f'{rows_deleted} movimientos borrados.',
        'backup_pre_reset': backup_filename,
        'restore_hint': 'Si fue un error: descarga el backup desde /admin → Backups y restaura.'
    })

@bp.route('/rotulos/<producto_nombre>/<cantidad_str>')
def generar_rotulos(producto_nombre, cantidad_str):
    if 'compras_user' not in session:
        return redirect('/login')
    try: cantidad_kg = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    prod = urllib.parse.unquote(producto_nombre); op_num = "OP-"+date.today().strftime('%Y%m%d'); cant_g = cantidad_kg*1000
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT material_id,material_nombre,porcentaje FROM formula_items WHERE producto_nombre=?", (prod,))
    items = c.fetchall()
    lotes = {}; incis = {}
    for r in items:
        mid = r[0]
        c.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp=?", (mid,)); ir=c.fetchone(); incis[mid]=ir[0] if ir and ir[0] else ''
        c.execute("SELECT lote,estanteria,posicion,fecha_vencimiento FROM movimientos WHERE material_id=? AND tipo='Entrada' AND lote IS NOT NULL AND lote!='' AND lote!='S/L' ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento='' THEN '9999' ELSE fecha_vencimiento END ASC LIMIT 1", (mid,))
        row=c.fetchone(); lotes[mid]={'lote':row[0] if row else 'S/L','est':row[1] if row else '','pos':row[2] if row else '','vence':str(row[3])[:10] if row and row[3] else ''}
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
    if 'compras_user' not in session:
        return redirect('/login')
    try: cantidad = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper(); lote=urllib.parse.unquote(lote)
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT nombre_inci,nombre_comercial,tipo,proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,)); mp=c.fetchone()
    c.execute("SELECT fecha_vencimiento,estanteria,posicion,proveedor FROM movimientos WHERE material_id=? AND lote=? ORDER BY fecha DESC LIMIT 1", (codigo,lote)); mov=c.fetchone()
    ni=mp[0] if mp else ''; nc=mp[1] if mp else codigo; tp=mp[2] if mp else ''
    pv=(mp[3] if mp and mp[3] else '') or (mov[3] if mov and len(mov)>3 and mov[3] else '')
    fv=str(mov[0])[:10] if mov and mov[0] else ''; ub=((mov[1] or '')+(mov[2] or '')) if mov else ''
    nr="REC-"+date.today().strftime('%Y%m%d')+"-"+codigo[-3:]; bv=codigo+'|'+lote
    h=('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
       '<title>Rotulo Recepcion MP</title>'
       '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
       '<style>'
       '*{margin:0;padding:0;box-sizing:border-box;}'
       'body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
       '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
       '.pb{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
       '.r{background:white;border:3px solid #1a252f;border-radius:5px;max-width:520px;margin:auto;}'
       '.rh{background:#1a252f;color:white;padding:8px 12px;text-align:center;}'
       '.lote{background:#fff3cd;border:2px solid #f39c12;padding:10px;text-align:center;margin:10px;}'
       '.lnum{font-size:20pt;font-weight:bold;color:#c0392b;letter-spacing:2px;}'
       'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
       '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:35%;}'
       '.termica{display:none;}'
       '@media print{'
         '.ph{display:none!important;}.r{display:none!important;}'
         '.termica{display:block!important;}'
         'body{background:white;padding:0;margin:0;}'
         '@page{size:50mm auto;margin:1mm;}'
       '}'
       '</style></head><body>'
    )
    h+=('<div class="ph"><b>Rotulo de Recepcion Materia Prima</b>'
        '<button class="pb" onclick="window.print()">&#128438; Imprimir etiqueta termica</button></div>'
    )
    h+=('<div class="r"><div class="rh">'
        '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
        '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; '+hoy+'</span>'
        '</div>'
        '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE</div>'
        '<div class="lnum">'+lote+'</div>'
        '<svg id="bc" style="margin-top:6px;"></svg>'
        '<div style="font-size:7pt;color:#888;margin-top:2px;">'+bv+'</div></div>'
        '<table>'
        '<tr><td class="l">Codigo MP:</td><td style="font-weight:700;">'+codigo+'</td></tr>'
        '<tr><td class="l">Nombre INCI:</td><td style="font-size:0.9em;color:#1a5276;">'+ni+'</td></tr>'
        '<tr><td class="l">Nombre Comercial:</td><td style="font-weight:700;">'+nc+'</td></tr>'
        '<tr><td class="l">Tipo / Funcion:</td><td>'+tp+'</td></tr>'
        '<tr><td class="l">Proveedor:</td><td style="font-weight:700;">'+pv+'</td></tr>'
        '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">'+f"{cantidad:,.0f} g"+'</td></tr>'
        '<tr><td class="l">Fecha de recepcion:</td><td style="font-weight:700;">'+hoy+'</td></tr>'
        '<tr><td class="l">Fecha de vencimiento:</td><td style="color:#c0392b;font-weight:700;">'+fv+'</td></tr>'
        '<tr><td class="l">Fecha de analisis:</td><td style="height:28px;background:#fffde7;"></td></tr>'
        '<tr style="background:#e8f5e9;">'
        '<td class="l" style="color:#1b5e20;font-weight:800;font-size:10pt;vertical-align:middle;">Estado de calidad:</td>'
        '<td style="height:70px;vertical-align:top;padding:8px;">'
        '<div style="display:flex;gap:20px;margin-bottom:6px;">'
        '<span style="font-size:11pt;font-weight:700;">&#9744; Aprobado</span>'
        '<span style="font-size:11pt;font-weight:700;">&#9744; Cuarentena</span>'
        '<span style="font-size:11pt;font-weight:700;">&#9744; Rechazado</span>'
        '</div>'
        '<div style="background:#fffde7;border:1px dashed #f39c12;height:36px;border-radius:3px;display:flex;align-items:center;justify-content:center;">'
        '<span style="font-size:7.5pt;color:#aaa;">[ espacio para sticker de calidad ]</span>'
        '</div></td></tr>'
        '<tr><td class="l">Ubicacion:</td><td>Est. '+ub+'</td></tr>'
        '<tr><td class="l">N de Recepcion:</td><td>'+nr+'</td></tr>'
        '<tr><td class="l">Recibido por:</td><td style="height:30px;"></td></tr>'
        '<tr><td class="l">Analizado / Aprobado por:</td><td style="height:30px;"></td></tr>'
        '</table>'
        '<div style="background:#ecf0f1;padding:4px 10px;font-size:7.5pt;color:#888;text-align:center;">'
        'COC-PRO-002-F07 &nbsp;|&nbsp; '+hoy+'</div></div>'
    )
    h+=('<div class="termica" style="width:50mm;font-family:Arial,sans-serif;font-size:6.5pt;border:2px solid #000;word-break:break-word;">'
        '<div style="background:#000;color:#fff;text-align:center;padding:2px;font-size:6pt;font-weight:bold;">ESPAGIRIA LAB &nbsp;|&nbsp; COC-PRO-002-F07</div>'
        '<div style="text-align:center;padding:3px 2px 1px;">'
        '<svg id="bc2" style="width:46mm;height:18mm;"></svg>'
        '<div style="font-size:8pt;font-weight:bold;color:#c0392b;letter-spacing:1px;margin-top:1px;">'+lote+'</div>'
        '</div>'
        '<table style="width:100%;border-collapse:collapse;font-size:6.5pt;">'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;width:40%;">Codigo:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;">'+codigo+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">INCI:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-style:italic;">'+ni+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Tipo/Funcion:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;">'+tp+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Proveedor:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;">'+pv+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Nombre:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;">'+nc+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Cantidad:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;color:#27ae60;">'+f"{cantidad:,.0f} g"+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Recep:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;">'+hoy+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Vence:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;color:#c0392b;">'+fv+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Analisis:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;background:#fffde7;height:10px;"></td></tr>'
        '<tr><td colspan="2" style="border:1px solid #999;padding:1px 2px;background:#c8f7c5;font-weight:bold;">Estado de Calidad:</td></tr>'
        '<tr><td colspan="2" style="border:1px solid #999;padding:2px 3px;background:#c8f7c5;">'
        '<span style="margin-right:6px;">&#9744; Aprobado</span>'
        '<span style="margin-right:6px;">&#9744; Cuarentena</span>'
        '<span>&#9744; Rechazado</span>'
        '<div style="margin-top:2px;border:1px dashed #f39c12;background:#fffde7;height:16px;'
        'display:flex;align-items:center;justify-content:center;">'
        '<span style="font-size:5.5pt;color:#aaa;">[sticker QC]</span></div></td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Ubicacion:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;font-weight:bold;">Est. '+ub+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">N Recepcion:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;">'+nr+'</td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Recibido por:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;height:14px;"></td></tr>'
        '<tr><td style="border:1px solid #999;padding:1px 2px;background:#eee;font-weight:bold;">Anal./Aprobado:</td>'
        '<td style="border:1px solid #999;padding:1px 2px;height:14px;"></td></tr>'
        '</table>'
        '<div style="text-align:center;font-size:5.5pt;color:#666;padding:1px;">'+nr+'</div>'
        '</div>'
    )
    h+=('<script>window.onload=function(){'
        'try{JsBarcode("#bc","'+bv+'",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}'
        'try{JsBarcode("#bc2","'+bv+'",{format:"CODE128",width:1,height:35,displayValue:false,margin:0});}catch(e){}'
        '}</script>'
        '</body></html>')
    return h

@bp.route('/rotulo-recepcion-mee/<codigo>/<cantidad_str>')
def rotulo_recepcion_mee(codigo, cantidad_str):
    if 'compras_user' not in session:
        return redirect('/login')
    try: cantidad = int(float(cantidad_str))
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    codigo = urllib.parse.unquote(codigo)
    lote_ref = request.args.get('lote','')
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT descripcion, categoria, proveedor, unidad FROM maestro_mee WHERE codigo=?", (codigo,))
        mee = c.fetchone()
        c.execute("SELECT lote_ref, responsable, fecha, observaciones FROM movimientos_mee WHERE mee_codigo=? AND tipo='Entrada' AND anulado=0 ORDER BY id DESC LIMIT 1", (codigo,))
        mov = c.fetchone()
    except Exception as e:
        return f"<h2>Error DB: {e}</h2>", 500
    desc  = mee[0] if mee else codigo
    cat   = mee[1] if mee else ''
    prov  = mee[2] if mee else ''
    unid  = mee[3] if mee and len(mee)>3 else 'und'
    lote  = lote_ref or (mov[0] if mov else '')
    oper  = mov[1] if mov else ''
    obs   = mov[3] if mov and len(mov)>3 else ''
    nr    = "REC-MEE-" + date.today().strftime('%Y%m%d') + "-" + codigo[-4:]
    # M.ENV: envases primarios / M.EMP: empaque secundario
    env_cats = {'Envase','Frasco','Tapa','Gotero','Contorno'}
    is_env = cat in env_cats
    chk_mp  = '&#9744;'; chk_env = '&#9745;' if is_env else '&#9744;'; chk_emp = '&#9745;' if not is_env else '&#9744;'
    cant_str = f"{cantidad:,} {unid}"

    css = ('<style>'
           '*{margin:0;padding:0;box-sizing:border-box;}'
           'body{font-family:Arial,sans-serif;font-size:9pt;background:#ddd;padding:16px;}'
           '.ph{background:#1a3a5c;color:white;padding:8px 16px;display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}'
           '.pb{background:#2980b9;color:white;border:none;padding:6px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
           '.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:920px;margin:auto;}'
           '.rot{background:white;border:2.5px solid #1a3a5c;border-radius:4px;}'
           '.rh{background:#1a3a5c;color:white;padding:5px 10px;display:grid;grid-template-columns:1fr auto;gap:2px;font-size:8pt;}'
           '.rh-title{font-weight:700;font-size:9.5pt;}'
           '.rh-meta{text-align:right;font-size:7pt;opacity:0.85;line-height:1.5;}'
           'table{width:100%;border-collapse:collapse;}'
           'td{border:1px solid #bbb;padding:3px 6px;font-size:8.5pt;}'
           '.lbl{background:#ecf0f1;font-weight:700;font-size:7.5pt;color:#333;width:42%;}'
           '.val{font-weight:600;}'
           '.tipo{background:#dbe9f5;}'
           '.calidad td{background:#e8f5e9;}'
           '.firma td{height:30px;}'
           '.bc{text-align:center;padding:5px;background:#f8f9fa;border-bottom:1px solid #bbb;}'
           '.footer{background:#dde8f0;padding:3px 8px;font-size:7pt;color:#555;text-align:center;}'
           '@media print{'
           '@page{size:A4;margin:8mm;}'
           '.ph{display:none;}'
           'body{background:white;padding:0;}'
           '.grid{display:grid;grid-template-columns:1fr 1fr;gap:4mm;}'
           '.rot{border:1.5px solid #000;page-break-inside:avoid;}'
           '}'
           '</style>')

    def make_label(bid):
        lbl  = '<div class="rot">'
        lbl += ('<div class="rh">'
                '<div><div class="rh-title">IDENTIFICACI&Oacute;N DE INSUMOS</div>'
                '<div style="font-size:7pt;opacity:0.8;">Espagiria Laboratorios</div></div>'
                '<div class="rh-meta">'
                'C&oacute;digo: <b>COC-PRO-002-F04</b><br>'
                'Versi&oacute;n: 2 &nbsp;|&nbsp; P&aacute;g: 1 de 1<br>'
                'Vigencia: 13-Jun-2025 / 12-Jun-2028'
                '</div></div>')
        lbl += (f'<div class="bc">'
                f'<div style="font-size:7pt;color:#666;margin-bottom:2px;">C&Oacute;DIGO &mdash; BARRAS</div>'
                f'<svg id="{bid}" style="max-width:100%;"></svg>'
                f'<div style="font-family:monospace;font-weight:700;font-size:9pt;letter-spacing:2px;color:#1a3a5c;">{codigo}</div>'
                f'</div>')
        lbl += '<table>'
        lbl += f'<tr><td class="lbl">NOMBRE COMERCIAL DEL INSUMO</td><td class="val" colspan="3">{desc}</td></tr>'
        lbl += f'<tr><td class="lbl">NOMBRE INCI DEL INSUMO</td><td colspan="3">&mdash;</td></tr>'
        lbl += f'<tr><td class="lbl">MARCA O FORMA QU&Iacute;MICA</td><td colspan="3">{prov}</td></tr>'
        lbl += ('<tr class="tipo"><td class="lbl tipo">TIPO DE INSUMO</td>'
                f'<td style="text-align:center;width:18%;">{chk_mp} MP</td>'
                f'<td style="text-align:center;width:18%;">{chk_env} M.ENV</td>'
                f'<td style="text-align:center;width:18%;">{chk_emp} M.EMP</td></tr>')
        lbl += f'<tr><td class="lbl">C&Oacute;DIGO INTERNO</td><td class="val">{codigo}</td><td class="lbl">LOTE</td><td class="val">{lote}</td></tr>'
        lbl += f'<tr><td class="lbl">CANTIDAD</td><td class="val">{cant_str}</td><td class="lbl">PROVEEDOR</td><td class="val">{prov}</td></tr>'
        lbl += f'<tr><td class="lbl">FECHA DE RECEPCI&Oacute;N</td><td class="val">{hoy}</td><td class="lbl">FECHA DE AN&Aacute;LISIS</td><td style="height:26px;background:#fffde7;"></td></tr>'
        lbl += f'<tr><td class="lbl">OBSERVACIONES</td><td colspan="3" style="height:24px;">{obs}</td></tr>'
        lbl += f'<tr><td class="lbl">FECHA DE VENCIMIENTO</td><td colspan="3">N/A &mdash; Material de envase/empaque</td></tr>'
        lbl += ('<tr class="calidad"><td class="lbl calidad" style="color:#1b5e20;">ESTADO</td>'
                '<td colspan="3" style="height:26px;">'
                '<span style="margin-right:12px;">&#9744; Aprobado</span>'
                '<span style="margin-right:12px;">&#9744; En cuarentena</span>'
                '<span>&#9744; Rechazado</span></td></tr>')
        lbl += '<tr class="firma"><td class="lbl">FECHA Y FIRMA REALIZADO POR</td><td colspan="3"></td></tr>'
        lbl += '<tr class="firma"><td class="lbl">FECHA Y FIRMA APROBADO POR</td><td colspan="3"></td></tr>'
        lbl += '</table>'
        lbl += f'<div class="footer">COC-PRO-002-F04 &nbsp;|&nbsp; {cat} &nbsp;|&nbsp; {hoy} &nbsp;|&nbsp; N&deg; Rec: {nr}</div>'
        lbl += '</div>'
        return lbl

    h  = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
    h += '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
    h += css + '</head><body>'
    h += ('<div class="ph">'
          '<b>R&oacute;tulo Identificaci&oacute;n Insumos MEE &mdash; Espagiria '
          '<span style="font-size:0.8em;opacity:0.8;">(4 etiquetas por hoja A4)</span></b>'
          '<button class="pb" onclick="window.print()">&#128203; Imprimir 4</button></div>')
    h += '<div class="grid">'
    bids = ['bc0','bc1','bc2','bc3']
    for bid in bids:
        h += make_label(bid)
    h += '</div>'
    js_parts = [f'try{{JsBarcode("#{b}","{codigo}",{{format:"CODE128",width:1.6,height:40,displayValue:false,margin:1}});}}catch(e){{}}' for b in bids]
    h += '<script>window.onload=function(){' + ''.join(js_parts) + '}</script>'
    h += '</body></html>'
    return h
    return h

@bp.route('/api/ordenes-compra/pendientes-recepcion')
def ocs_pendientes_recepcion():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT oc.numero_oc, oc.proveedor, oc.fecha, oc.valor_total,
                        oci.codigo_mp, oci.nombre_mp, oci.cantidad_g, oci.precio_unitario
                 FROM ordenes_compra oc
                 JOIN ordenes_compra_items oci ON oc.numero_oc = oci.numero_oc
                 WHERE oc.estado IN ('Aprobada','Enviada','Parcial')
                 ORDER BY oc.fecha DESC""")
    rows = c.fetchall()
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
    conn = get_db(); c = conn.cursor()
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
    return jsonify({'lote': lote, 'movimientos': movs, 'producciones': prods, 'despachos': desps})

@bp.route('/api/mp/<codigo>/historial-precios')
def historial_precios_mp(codigo):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT fecha, proveedor, precio_kg, valor_total, numero_factura, numero_oc
                 FROM movimientos WHERE material_id=? AND tipo='Entrada' AND precio_kg>0
                 ORDER BY fecha DESC LIMIT 24""", (codigo,))
    hist = [{'fecha':r[0],'proveedor':r[1],'precio_kg':r[2],'valor_total':r[3],'factura':r[4],'oc':r[5]} for r in c.fetchall()]
    c.execute("SELECT precio_referencia, proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    return jsonify({'codigo': codigo, 'precio_referencia': mp[0] if mp else 0,
                    'proveedor_habitual': mp[1] if mp else '', 'historial': hist})

@bp.route('/api/mp/<codigo>/consumo-historico')
def consumo_historico_mp(codigo):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT substr(fecha,1,7) as mes,
                        SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END) as consumo_g,
                        COUNT(CASE WHEN tipo='Salida' THEN 1 END) as n_salidas
                 FROM movimientos WHERE material_id=?
                 GROUP BY substr(fecha,1,7) ORDER BY mes DESC LIMIT 12""", (codigo,))
    meses = [{'mes':r[0],'consumo_g':r[1],'n_salidas':r[2]} for r in c.fetchall()]
    consumos = [m['consumo_g'] for m in meses if m['consumo_g'] and m['consumo_g'] > 0]
    promedio = sum(consumos)/len(consumos) if consumos else 0
    c.execute("SELECT lead_time_dias, stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
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
    conn = get_db(); c = conn.cursor()
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
        conn.commit()
        return jsonify({'numero': num, 'id': cid, 'total_items': len(mps)}), 201
    c.execute("SELECT id,numero,fecha_inicio,estado,responsable,total_items,items_diferencia FROM conteos_fisicos ORDER BY fecha_inicio DESC LIMIT 20")
    rows = [{'id':r[0],'numero':r[1],'fecha':r[2],'estado':r[3],'responsable':r[4],'total':r[5],'diffs':r[6]} for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/conteos/<int:cid>', methods=['GET','PATCH'])
def conteo_detalle(cid):
    conn = get_db(); c = conn.cursor()
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
        r = c.fetchone()
        return jsonify({'id':r[0],'numero':r[1],'estado':r[2],'total':r[3],'diffs':r[4]})
    c.execute("SELECT * FROM conteos_fisicos WHERE id=?", (cid,)); h = c.fetchone()
    if not h: return jsonify({'error':'No encontrado'}), 404
    c.execute("SELECT codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,ajuste_aplicado,observaciones FROM conteo_items WHERE conteo_id=? ORDER BY nombre_mp", (cid,))
    items = [{'codigo':r[0],'nombre':r[1],'sistema':r[2],'fisico':r[3],'diff':r[4],'ajustado':r[5],'obs':r[6]} for r in c.fetchall()]
    return jsonify({'header':{'id':h[0],'numero':h[1],'estado':h[4],'responsable':h[5],'total':h[7],'diffs':h[8]},'items':items})

@bp.route('/api/lotes/cuarentena/<int:mov_id>/liberar', methods=['POST'])
def liberar_cuarentena(mov_id):
    # Liberación de cuarentena = decisión de Calidad. Antes solo admins,
    # ahora QC + admins (consistente con cc-review y liberar_lote).
    u, err, code = _require_qc()
    if err:
        return err, code
    d = request.json or {}; decision = d.get('decision','Aprobado')
    conn = get_db(); c = conn.cursor()
    nuevo_estado = 'VIGENTE' if decision == 'Aprobado' else 'RECHAZADO'
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=?", (nuevo_estado, mov_id))
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session['compras_user'], f'{decision.upper()}_CUARENTENA', 'movimientos',
               str(mov_id), d.get('observaciones',''), request.remote_addr))
    conn.commit()
    return jsonify({'ok':True, 'decision':decision, 'estado':nuevo_estado})

@bp.route('/api/maestro-mp/<codigo>/precio', methods=['POST'])
def actualizar_precio_mp(codigo):
    d = request.json or {}; precio = float(d.get('precio_kg', 0))
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET precio_referencia=?,ultima_act_precio=? WHERE codigo_mp=?",
              (precio, datetime.now().isoformat()[:10], codigo))
    c.execute("""INSERT INTO precios_mp_historico (codigo_mp,proveedor,precio_kg,fecha,origen,observaciones)
                 VALUES (?,?,?,?,?,?)""",
              (codigo, d.get('proveedor',''), precio, datetime.now().isoformat()[:10],
               d.get('origen','manual'), d.get('observaciones','')))
    conn.commit()
    return jsonify({'ok':True, 'precio_kg':precio})

@bp.route('/api/admin/backfill-precios-mp', methods=['POST'])
def backfill_precios_mp():
    """Pobla precio_referencia en maestro_mps desde movimientos.precio_kg y precios_mp_historico.
    Solo actualiza MPs que tienen precio_referencia=0 o nulo."""
    conn = get_db(); c = conn.cursor()
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
    conn.commit()
    return jsonify({
        'ok': True,
        'actualizados': actualizados,
        'con_precio_ahora': con_precio,
        'total_activos': total_activos,
        'cobertura_pct': round(con_precio / total_activos * 100, 1) if total_activos > 0 else 0
    })

# ═══════════════════════════════════════════════════════════════════════
# MÓDULO MEE — Material de Empaque y Envase  (Tasks #70 #71 #72)
# ═══════════════════════════════════════════════════════════════════════

def _init_mee_movimientos():
    conn = get_db(); c = conn.cursor()
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
    conn.commit()

_init_mee_movimientos()

@bp.route('/api/mee', methods=['POST'])
def mee_crear():
    """Crea un nuevo material en maestro_mee."""
    d = request.json or {}
    codigo      = d.get('codigo','').strip().upper()
    descripcion = d.get('descripcion','').strip()
    categoria   = d.get('categoria','Otro').strip()
    proveedor   = d.get('proveedor','').strip()
    unidad      = d.get('unidad','und').strip()
    stock_actual = float(d.get('stock_actual', 0))
    stock_minimo = float(d.get('stock_minimo', 0))
    if not codigo or not descripcion:
        return jsonify({'error': 'codigo y descripcion requeridos'}), 400
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("""INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, proveedor,
                                              stock_actual, stock_minimo, estado)
                     VALUES (?,?,?,?,?,?,?,'Activo')""",
                  (codigo, descripcion, categoria, unidad, proveedor, stock_actual, stock_minimo))
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True, 'codigo': codigo, 'message': f'Material {codigo} creado exitosamente'})

@bp.route('/api/mee/stock', methods=['GET'])
def mee_stock_list():
    """Lista maestro_mee con stock, alertas y metricas de movimiento."""
    conn = get_db(); c = conn.cursor()
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
                r['dias_sin_mov'] = days
                r['obsoleto'] = days > 90
            except Exception:
                r['dias_sin_mov'] = None; r['obsoleto'] = False
        else:
            r['dias_sin_mov'] = None; r['obsoleto'] = s > 0

    c.execute("SELECT DISTINCT categoria FROM maestro_mee WHERE estado='Activo' ORDER BY categoria")
    categorias = [row[0] for row in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo'")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND stock_minimo>0 AND stock_actual<stock_minimo")
    bajo = c.fetchone()[0]
    return jsonify({'items': rows, 'categorias': categorias, 'total': total, 'bajo_minimo': bajo})

@bp.route('/api/mee/movimiento', methods=['POST'])
def mee_registrar_movimiento():
    """Registra una entrada, salida o ajuste de empaque MEE."""
    d = request.json or {}
    codigo      = d.get('codigo','').strip()
    tipo        = d.get('tipo','').strip()
    cantidad    = float(d.get('cantidad', 0))
    unidad      = d.get('unidad','und').strip()
    lote_ref    = d.get('lote_ref','').strip()
    batch_ref   = d.get('batch_ref','').strip()
    responsable = d.get('responsable', session.get('compras_user','')).strip()
    obs         = d.get('observaciones','').strip()

    if not codigo or tipo not in ('Entrada','Salida','Ajuste') or cantidad <= 0:
        return jsonify({'error': 'codigo, tipo (Entrada/Salida/Ajuste) y cantidad>0 requeridos'}), 400

    conn = get_db(); c = conn.cursor()
    c.execute("SELECT codigo, descripcion, stock_actual, unidad FROM maestro_mee WHERE codigo=?", (codigo,))
    mee = c.fetchone()
    if not mee:
        return jsonify({'error': f'Codigo MEE {codigo} no encontrado'}), 404

    c.execute("""INSERT INTO movimientos_mee
                 (mee_codigo, tipo, cantidad, unidad, lote_ref, batch_ref, responsable, observaciones)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (codigo, tipo, cantidad, unidad, lote_ref, batch_ref, responsable, obs))
    mov_id = c.lastrowid

    if tipo == 'Entrada':
        c.execute("UPDATE maestro_mee SET stock_actual = stock_actual + ? WHERE codigo=?", (cantidad, codigo))
    elif tipo == 'Salida':
        c.execute("UPDATE maestro_mee SET stock_actual = MAX(0, stock_actual - ?) WHERE codigo=?", (cantidad, codigo))
    else:
        c.execute("UPDATE maestro_mee SET stock_actual = ? WHERE codigo=?", (cantidad, codigo))

    c.execute("SELECT stock_actual, stock_minimo FROM maestro_mee WHERE codigo=?", (codigo,))
    s_new, s_min = c.fetchone()
    conn.commit()

    alerta = None
    if s_min and s_min > 0 and s_new < s_min:
        alerta = f'Stock bajo minimo: {s_new:.0f} {unidad} (minimo: {s_min:.0f})'
    return jsonify({
        'ok': True, 'movimiento_id': mov_id, 'stock_nuevo': s_new, 'alerta': alerta,
        'message': f'{tipo} de {cantidad:.0f} {unidad} registrada para {mee[1]}'
    })

@bp.route('/api/mee/movimientos', methods=['GET'])
def mee_historial_movimientos():
    """Historial paginado de movimientos MEE."""
    codigo = request.args.get('codigo','')
    tipo   = request.args.get('tipo','')
    limit  = min(int(request.args.get('limit', 50)), 200)
    conn = get_db(); c = conn.cursor()
    sql = """SELECT mv.id, mv.mee_codigo, COALESCE(m.descripcion,'') as descripcion,
                    mv.tipo, mv.cantidad, mv.unidad, mv.lote_ref, mv.batch_ref,
                    mv.responsable, mv.observaciones, mv.fecha, mv.anulado
             FROM movimientos_mee mv
             LEFT JOIN maestro_mee m ON mv.mee_codigo = m.codigo
             WHERE mv.anulado=0"""
    params = []
    if codigo:
        sql += " AND mv.mee_codigo=?"; params.append(codigo)
    if tipo:
        sql += " AND mv.tipo=?"; params.append(tipo)
    sql += f" ORDER BY mv.fecha DESC LIMIT {limit}"
    c.execute(sql, params)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'movimientos': rows, 'total': len(rows)})

@bp.route('/api/mee/alertas', methods=['GET'])
def mee_alertas_list():
    """Alertas MEE: bajo minimo + posible obsolescencia (sin mov >90 dias)."""
    from datetime import date, timedelta
    conn = get_db(); c = conn.cursor()
    hace90 = (date.today() - timedelta(days=90)).isoformat()

    c.execute("""SELECT m.codigo, m.descripcion, m.categoria, m.stock_actual, m.stock_minimo, m.unidad
                 FROM maestro_mee m
                 WHERE m.estado='Activo' AND m.stock_minimo>0 AND m.stock_actual < m.stock_minimo
                 ORDER BY (m.stock_actual / m.stock_minimo) ASC""")
    bajo_minimo = [{'codigo': r[0], 'descripcion': r[1], 'categoria': r[2],
                    'stock_actual': r[3], 'stock_minimo': r[4], 'unidad': r[5],
                    'ratio': round(r[3]/r[4], 2) if r[4] else 0} for r in c.fetchall()]

    c.execute("""SELECT m.codigo, m.descripcion, m.categoria, m.stock_actual, m.unidad,
                        MAX(mv.fecha) as ultimo_mov
                 FROM maestro_mee m
                 LEFT JOIN movimientos_mee mv ON m.codigo=mv.mee_codigo AND mv.anulado=0
                 WHERE m.estado='Activo' AND m.stock_actual>0
                 GROUP BY m.codigo
                 HAVING ultimo_mov IS NULL OR ultimo_mov < ?
                 ORDER BY ultimo_mov ASC LIMIT 15""", (hace90,))
    obsolescencia = [{'codigo': r[0], 'descripcion': r[1], 'categoria': r[2],
                      'stock_actual': r[3], 'unidad': r[4], 'ultimo_mov': r[5] or 'Nunca'}
                     for r in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo'")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND stock_minimo>0 AND stock_actual<stock_minimo")
    n_bajo = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movimientos_mee WHERE anulado=0 AND fecha>=date('now','-7 days')")
    mov_sem = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movimientos_mee WHERE tipo='Entrada' AND anulado=0 AND fecha>=date('now','-30 days')")
    ent_mes = c.fetchone()[0]
    return jsonify({
        'bajo_minimo': bajo_minimo, 'obsolescencia': obsolescencia,
        'resumen': {'total_mee': total, 'bajo_minimo': n_bajo,
                    'movimientos_semana': mov_sem, 'entradas_mes': ent_mes}
    })

@bp.route('/api/mee/trazabilidad', methods=['GET'])
def mee_trazabilidad():
    """Trazabilidad MEE: batch->empaque consumido  |  codigo->historial de batches."""
    batch  = request.args.get('batch','').strip()
    codigo = request.args.get('codigo','').strip()
    conn = get_db(); c = conn.cursor()

    if batch:
        c.execute("""SELECT mv.id, mv.mee_codigo, COALESCE(m.descripcion,'') as descripcion,
                            m.categoria, mv.cantidad, mv.unidad, mv.responsable, mv.fecha, mv.observaciones
                     FROM movimientos_mee mv LEFT JOIN maestro_mee m ON mv.mee_codigo=m.codigo
                     WHERE mv.batch_ref LIKE ? AND mv.tipo='Salida' AND mv.anulado=0
                     ORDER BY mv.fecha""", (f'%{batch}%',))
        cols = [d[0] for d in c.description]
        consumos = [dict(zip(cols, r)) for r in c.fetchall()]
        return jsonify({'tipo': 'batch', 'referencia': batch, 'consumos': consumos, 'total': len(consumos)})

    elif codigo:
        c.execute("""SELECT mv.id, mv.tipo, mv.batch_ref, mv.lote_ref, mv.cantidad, mv.unidad,
                            mv.responsable, mv.fecha, mv.observaciones
                     FROM movimientos_mee mv
                     WHERE mv.mee_codigo=? AND mv.anulado=0
                     ORDER BY mv.fecha DESC LIMIT 100""", (codigo,))
        cols = [d[0] for d in c.description]
        historial = [dict(zip(cols, r)) for r in c.fetchall()]
        return jsonify({'tipo': 'mee', 'referencia': codigo, 'historial': historial, 'total': len(historial)})

    return jsonify({'error': 'Proporcione parametro batch o codigo'}), 400

@bp.route('/api/mee/anular/<int:mov_id>', methods=['POST'])
def mee_anular_movimiento(mov_id):
    """Anula un movimiento MEE revirtiendo el impacto en stock."""
    user = session.get('compras_user','')
    payload = request.json or {}
    motivo = payload.get('motivo','').strip()
    if not motivo:
        return jsonify({'error': 'Motivo obligatorio'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM movimientos_mee WHERE id=?", (mov_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'No encontrado'}), 404
    cols_mv = [d[0] for d in c.description]
    mv = dict(zip(cols_mv, row))
    if mv['anulado']:
        return jsonify({'error': 'Ya anulado'}), 400
    if mv['tipo'] == 'Entrada':
        c.execute("UPDATE maestro_mee SET stock_actual=MAX(0,stock_actual-?) WHERE codigo=?",
                  (mv['cantidad'], mv['mee_codigo']))
    elif mv['tipo'] == 'Salida':
        c.execute("UPDATE maestro_mee SET stock_actual=stock_actual+? WHERE codigo=?",
                  (mv['cantidad'], mv['mee_codigo']))
    c.execute("UPDATE movimientos_mee SET anulado=1, observaciones=observaciones||? WHERE id=?",
              (f' [ANULADO por {user}: {motivo}]', mov_id))
    conn.commit()
    return jsonify({'ok': True, 'message': f'Movimiento #{mov_id} anulado y stock revertido'})

# ═══════════════════════════════════════════════════════════════
#  ACONDICIONAMIENTO + LIBERACIÓN — Fase 4
# ═══════════════════════════════════════════════════════════════

def _init_acondicionamiento():
    conn = get_db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS acondicionamiento (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        produccion_id       INTEGER DEFAULT 0,
        envasado_id         INTEGER DEFAULT 0,
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
    # Nuevas columnas — múltiples presentaciones y flujo liberación→stock_pt.
    # Usamos safe_alter (database.py) que distingue "columna ya existe"
    # (benigno) de errores reales (loguea + relanza).
    from database import safe_alter
    for _sql in [
        "ALTER TABLE acondicionamiento ADD COLUMN sku TEXT DEFAULT ''",
        "ALTER TABLE acondicionamiento ADD COLUMN precio_base REAL DEFAULT 0",
        "ALTER TABLE liberaciones ADD COLUMN sku TEXT DEFAULT ''",
        "ALTER TABLE liberaciones ADD COLUMN precio_base REAL DEFAULT 0",
    ]:
        safe_alter(conn, _sql)
    conn.commit()

_init_acondicionamiento()

# ══════════════════════════════════════════════════════════════════
# ENVASADO — Paso entre Produccion y Acondicionamiento
# ══════════════════════════════════════════════════════════════════

@bp.route('/api/producciones/sin-envasar', methods=['GET'])
def producciones_sin_envasar():
    """Cola de producciones sin registro de envasado vinculado."""
    conn = get_db(); c = conn.cursor()
    c.execute("""
        SELECT p.id, p.lote, p.producto, p.cantidad, p.fecha, p.operador, p.presentacion
        FROM producciones p
        LEFT JOIN envasado e ON e.produccion_id = p.id
        WHERE e.id IS NULL
          AND COALESCE(p.estado,'') NOT IN ('cancelado','Cancelado')
        ORDER BY p.id DESC LIMIT 100
    """)
    cols = ['id','lote','producto','cantidad_kg','fecha','operador','presentacion']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'cola': rows})

@bp.route('/api/envasado', methods=['GET', 'POST'])
def envasado_list():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        produccion_id = int(d.get('produccion_id') or 0)
        lote = d.get('lote', '').strip()
        producto = d.get('producto', '').strip()
        presentacion = d.get('presentacion', '').strip()
        batch_g = float(d.get('batch_g', 0) or 0)
        unidades = int(d.get('unidades', 0) or 0)
        envase_codigo = d.get('envase_codigo', '').strip()
        tapa_codigo = d.get('tapa_codigo', '').strip()
        operador = d.get('operador', session.get('compras_user', '')).strip()
        fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
        obs = d.get('observaciones', '').strip()

        if not lote or not producto:
            return jsonify({'error': 'lote y producto son requeridos'}), 400
        if unidades <= 0:
            return jsonify({'error': 'unidades debe ser > 0'}), 400

        # ─── PRE-CHECK MEE ──────────────────────────────────────────────────
        # Validar que los códigos existan en maestro_mee (anti-typo) y que
        # haya stock suficiente. Si falta cualquiera → 422 sin escribir nada.
        # Antes: si el código no existía, se hacía continue silencioso y el
        # INSERT en envasado quedaba sin descuento, dejando data inconsistente.
        plan_mee = []  # [(codigo, cant, descripcion, stock_actual, stock_minimo)]
        errores_mee = []
        for tipo_mee, codigo_mee, cant in [
            ('envase', envase_codigo, unidades),
            ('tapa', tapa_codigo, unidades),
        ]:
            if not codigo_mee:
                continue  # opcional: producto sin tapa, etc.
            row = c.execute(
                "SELECT stock_actual, stock_minimo, descripcion, estado "
                "FROM maestro_mee WHERE codigo=?",
                (codigo_mee,)
            ).fetchone()
            if not row:
                errores_mee.append({
                    'tipo': tipo_mee,
                    'codigo': codigo_mee,
                    'error': 'código no existe en maestro_mee',
                })
                continue
            stock_actual, stock_minimo, descripcion, estado = row[0], row[1], row[2], row[3]
            if estado != 'Activo':
                errores_mee.append({
                    'tipo': tipo_mee,
                    'codigo': codigo_mee,
                    'error': f'item está {estado}, no Activo',
                })
                continue
            if (stock_actual or 0) < cant:
                errores_mee.append({
                    'tipo': tipo_mee,
                    'codigo': codigo_mee,
                    'descripcion': descripcion,
                    'stock_disponible': stock_actual,
                    'requerido': cant,
                    'falta': cant - (stock_actual or 0),
                    'error': 'stock insuficiente',
                })
                continue
            plan_mee.append((codigo_mee, cant, descripcion or '',
                             stock_actual, stock_minimo))

        if errores_mee:
            return jsonify({
                'error': 'No se puede registrar el envasado',
                'detalle': 'Códigos MEE inválidos o sin stock suficiente',
                'errores': errores_mee,
                'mensaje': (
                    'Verifica los códigos en el dropdown y que haya stock. '
                    'Si necesitás más MEE, crea OC en /compras.'
                ),
            }), 422

        # ─── ESCRITURA TRANSACCIONAL ─────────────────────────────────────────
        try:
            c.execute("""INSERT INTO envasado
                (produccion_id, lote, producto, presentacion, batch_g, unidades,
                 envase_codigo, tapa_codigo, operador, fecha, estado, observaciones)
                VALUES (?,?,?,?,?,?,?,?,?,?,'Completado',?)""",
                (produccion_id, lote, producto, presentacion, batch_g, unidades,
                 envase_codigo, tapa_codigo, operador, fecha, obs))
            nuevo_id = c.lastrowid

            alertas_mee = []
            for codigo_mee, cant, descripcion, stock_actual, stock_minimo in plan_mee:
                nuevo_stock = max(0, (stock_actual or 0) - cant)
                c.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?",
                          (nuevo_stock, codigo_mee))
                c.execute("""INSERT INTO movimientos_mee
                    (mee_codigo, tipo, cantidad, lote_ref, observaciones, responsable, fecha)
                    VALUES (?,?,?,?,?,?,?)""",
                    (codigo_mee, 'Salida', cant, lote,
                     'Envasado ' + lote + ' - ' + producto + ' ' + presentacion,
                     operador, fecha))
                if (stock_minimo or 0) > 0 and nuevo_stock < stock_minimo:
                    deficit = stock_minimo - nuevo_stock
                    alertas_mee.append({
                        'codigo': codigo_mee, 'nombre': descripcion,
                        'stock': nuevo_stock, 'minimo': stock_minimo,
                        'deficit': deficit,
                    })
        except Exception as _e:
            conn.rollback()
            __import__('logging').getLogger('inventario').error(
                "Envasado FALLÓ tras pre-check OK (rollback): lote=%s err=%s",
                lote, _e, exc_info=True
            )
            return jsonify({
                'error': 'Falla transaccional al registrar envasado',
                'detalle': str(_e),
                'rollback': 'aplicado — no se descontó ningún MEE',
            }), 500

        # Si hay MEE bajo minimo, crear solicitud de compra automatica en Compras
        if alertas_mee:
            try:
                c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM solicitudes_compra WHERE numero LIKE ?",
                          (f"SOL-{datetime.now().strftime('%Y')}-%",))
                n_sol = (c.fetchone()[0] or 0) + 1
                num_sol = f"SOL-{datetime.now().strftime('%Y')}-{n_sol:04d}"
                obs_sol = 'Alerta automatica envasado ' + lote + ': MEE bajo minimo'
                c.execute("""INSERT INTO solicitudes_compra
                    (numero, fecha, estado, solicitante, urgencia, observaciones,
                     area, empresa, categoria, tipo)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (num_sol, datetime.now().isoformat(), 'Pendiente',
                     operador, 'Alta', obs_sol,
                     'Produccion', 'Espagiria', 'Material de Empaque', 'Compra'))
                for a in alertas_mee:
                    c.execute("""INSERT INTO solicitudes_compra_items
                        (numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion)
                        VALUES (?,?,?,?,?,?)""",
                        (num_sol, a['codigo'], a['nombre'], a['deficit'], 'und',
                         'Deficit MEE post-envasado ' + lote))
            except Exception as _e:
                print(f'[envasado] solicitud auto error: {_e}')

        conn.commit()
        return jsonify({'ok': True, 'id': nuevo_id, 'alertas_mee': alertas_mee}), 201

    # GET
    prod_id = request.args.get('produccion_id', '')
    if prod_id:
        c.execute("SELECT * FROM envasado WHERE produccion_id=? ORDER BY id DESC", (prod_id,))
    else:
        c.execute("SELECT * FROM envasado ORDER BY id DESC LIMIT 100")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'envasados': rows})

@bp.route('/api/envasado/pendientes-acond', methods=['GET'])
def envasado_pendientes():
    """Retorna envasados Completado que no tienen acondicionamiento asociado."""
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT e.* FROM envasado e
                 LEFT JOIN acondicionamiento a ON a.envasado_id = e.id
                 WHERE a.id IS NULL
                 ORDER BY e.id DESC""")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'pendientes': rows})

@bp.route('/api/acondicionamiento/pendientes-lib', methods=['GET'])
def acond_pendientes_lib():
    """Retorna acondicionamientos completados sin liberacion asociada."""
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT a.id, a.lote, a.producto, a.unidades_producidas,
                        a.presentacion, a.cantidad_batch_g, a.fecha,
                        a.sku, a.precio_base
                 FROM acondicionamiento a
                 LEFT JOIN liberaciones l ON l.acondicionamiento_id = a.id
                 WHERE l.id IS NULL
                 ORDER BY a.id DESC""")
    cols = ['id','lote','producto','unidades','presentacion','batch_g','fecha','sku','precio_base']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'pendientes': rows})

@bp.route('/api/acondicionamiento', methods=['GET', 'POST'])
def acondicionamiento_list():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        u = session.get('compras_user', '')
        mee_items = d.get('mee_consumido', [])
        envasado_id = int(d.get('envasado_id', 0) or 0)
        batch_g = float(d.get('batch_g', 0) or d.get('cantidad_batch_g', 0) or 0)
        uds = int(d.get('unidades', 0) or d.get('unidades_producidas', 0) or 0)
        c.execute("""INSERT INTO acondicionamiento
            (envasado_id, produccion_id, lote, producto, cantidad_batch_g, unidades_producidas,
             presentacion, mee_consumido, fecha, operador, observaciones, sku, precio_base)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (envasado_id, int(d.get('produccion_id') or 0), d.get('lote', ''), d.get('producto', ''),
             batch_g, uds,
             d.get('presentacion', ''), json.dumps(mee_items),
             d.get('fecha', datetime.now().strftime('%Y-%m-%d')), u,
             d.get('observaciones', ''), d.get('sku', '').strip(),
             float(d.get('precio_base', 0) or 0)))
        new_id = c.lastrowid
        # Auto-descontar MEE del maestro_mee
        lote_ref = d.get('lote', '')
        for item in mee_items:
            cod = str(item.get('codigo', item.get('codigo_mee', ''))).strip()
            cant = float(item.get('cantidad', 0) or 0)
            if not cod or cant <= 0: continue
            c.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
            row = c.fetchone()
            if not row: continue
            nuevo = max(0, row[0] - cant)
            c.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo, cod))
            c.execute("""INSERT INTO movimientos_mee
                         (mee_codigo, tipo, cantidad, lote_ref, batch_ref, responsable, observaciones)
                         VALUES (?,?,?,?,?,?,?)""",
                      (cod, 'Salida', cant, lote_ref, lote_ref, u,
                       f'Consumo acondicionamiento {lote_ref}'))
        conn.commit()
        return jsonify({'ok': True, 'id': new_id}), 201
    c.execute("""SELECT id, produccion_id, lote, producto, cantidad_batch_g, unidades_producidas,
                        presentacion, fecha, operador, estado, observaciones
                 FROM acondicionamiento ORDER BY creado_en DESC LIMIT 100""")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/acondicionamiento/<int:aid>', methods=['PATCH'])
def acondicionamiento_update(aid):
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    if 'estado' in d: c.execute("UPDATE acondicionamiento SET estado=? WHERE id=?", (d['estado'], aid))
    if 'unidades_producidas' in d: c.execute("UPDATE acondicionamiento SET unidades_producidas=? WHERE id=?", (int(d['unidades_producidas']), aid))
    if 'mee_consumido' in d: c.execute("UPDATE acondicionamiento SET mee_consumido=? WHERE id=?", (json.dumps(d['mee_consumido']), aid))
    if 'observaciones' in d: c.execute("UPDATE acondicionamiento SET observaciones=? WHERE id=?", (d['observaciones'], aid))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/liberacion', methods=['GET', 'POST'])
def liberacion_list():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        c.execute("""INSERT INTO liberaciones
            (acondicionamiento_id, lote, producto, unidades, presentacion,
             fecha_produccion, cliente, destino, observaciones, sku, precio_base)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (int(d.get('acondicionamiento_id', 0)), d.get('lote', ''), d.get('producto', ''),
             int(d.get('unidades', 0)), d.get('presentacion', ''), d.get('fecha_produccion', ''),
             d.get('cliente', ''), d.get('destino', 'ANIMUS'), d.get('observaciones', ''),
             d.get('sku', '').strip(), float(d.get('precio_base', 0) or 0)))
        conn.commit(); new_id = c.lastrowid
        return jsonify({'ok': True, 'id': new_id}), 201
    estado = request.args.get('estado', '')
    if estado: c.execute("SELECT * FROM liberaciones WHERE estado=? ORDER BY creado_en DESC LIMIT 100", (estado,))
    else: c.execute("SELECT * FROM liberaciones ORDER BY creado_en DESC LIMIT 100")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/liberacion/<int:lid>', methods=['PATCH'])
def liberacion_update(lid):
    u = session.get('compras_user', '')
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    estado = d.get('estado', '')
    if estado == 'Liberado':
        c.execute("UPDATE liberaciones SET estado='Liberado', fecha_liberacion=?, aprobado_por=?, cliente=? WHERE id=?",
                  (datetime.now().strftime('%Y-%m-%d'), u, d.get('cliente', ''), lid))
        # Auto-crear entrada en stock_pt al liberar
        c.execute("SELECT lote, producto, unidades, sku, precio_base, presentacion FROM liberaciones WHERE id=?", (lid,))
        lib = c.fetchone()
        if lib and lib[3]:  # sku presente
            lote_lib, prod_lib, uds_lib, sku_lib, precio_lib, pres_lib = lib
            fecha_lib = datetime.now().strftime('%Y-%m-%d')
            c.execute("""INSERT INTO stock_pt
                         (sku, descripcion, lote_produccion, fecha_produccion,
                          unidades_inicial, unidades_disponible, precio_base,
                          empresa, estado, observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (sku_lib, prod_lib, lote_lib, fecha_lib,
                       uds_lib, uds_lib, precio_lib,
                       'ANIMUS', 'Disponible',
                       f'Liberacion aprobada por {u} — {pres_lib}'))
        # Registrar en calidad como BPM completado
        try:
            _lib_val = lib[1] if lib else 'PT'
            _lib_lote = lib[0] if lib else ''
            _cli_dest = d.get('cliente','') or 'sin cliente'
            c.execute("""INSERT INTO calidad_registros
                         (fecha, tarea_id, usuario, estado, valor_registrado, observaciones)
                         VALUES (date('now'), NULL, ?, 'Completado', ?, ?)""",
                     (u,
                      f"{_lib_lote} | {str(_lib_val)[:40]}",
                      f"BPM Liberacion PT -> {_cli_dest}"))
        except Exception:
            pass
    elif estado == 'Rechazado':
        c.execute("UPDATE liberaciones SET estado='Rechazado', aprobado_por=?, observaciones=? WHERE id=?",
                  (u, d.get('observaciones', ''), lid))
    else:
        c.execute("UPDATE liberaciones SET observaciones=? WHERE id=?", (d.get('observaciones', ''), lid))
    conn.commit()
    return jsonify({'ok': True})


# ─── ALERTAS VIVAS DE PLANTA ─────────────────────────────────────────────────
# Endpoint unificado que el panel admin / centro de mando consume para mostrar
# todo lo que requiere atención HOY. Cubre items #3, #4, #6 del audit:
#   - Vencimientos próximos (<30 días) y vencidos
#   - Stock por debajo de mínimo
#   - Conteos cíclicos cerrados con discrepancias > tolerancia, sin ajuste
#   - Lotes en cuarentena que llevan > 5 días esperando QC

@bp.route('/api/planta/alertas-vivas', methods=['GET'])
def alertas_vivas_planta():
    """Consolida todas las alertas operacionales de Planta en un solo endpoint.

    Retorna { vencimientos, stock_bajo, discrepancias, cuarentena_extendida,
              total, severidad_max }
    severidad_max: 'critico' | 'alto' | 'medio' | 'ok'
    """
    u, err, code = _require_session()
    if err:
        return err, code

    conn = get_db(); c = conn.cursor()
    from datetime import date, timedelta
    hoy = date.today()
    in_30 = (hoy + timedelta(days=30)).isoformat()
    hace_5 = (hoy - timedelta(days=5)).isoformat()

    # ── 1. Vencimientos ───────────────────────────────────────────────────────
    # MPs con stock vivo cuyo lote vence en <30 días (o ya vencido)
    c.execute("""
        SELECT m.material_id, m.material_nombre, m.lote, m.fecha_vencimiento,
               COALESCE(mp.tipo_material,'MP') as tipo,
               SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock
        FROM movimientos m
        LEFT JOIN maestro_mps mp ON m.material_id = mp.codigo_mp
        WHERE m.fecha_vencimiento != ''
          AND m.fecha_vencimiento <= ?
          AND m.estado_lote IN ('VIGENTE','CUARENTENA')
        GROUP BY m.material_id, m.lote
        HAVING stock > 0
        ORDER BY m.fecha_vencimiento ASC
        LIMIT 100
    """, (in_30,))
    venc_rows = c.fetchall()
    vencimientos = []
    for r in venc_rows:
        try:
            fv = date.fromisoformat(r[3][:10])
            dias = (fv - hoy).days
        except (ValueError, TypeError, IndexError):
            dias = None
        vencimientos.append({
            'material_id': r[0], 'material_nombre': r[1], 'lote': r[2],
            'fecha_vencimiento': r[3], 'dias_restantes': dias,
            'tipo_material': r[4], 'stock_g': round(r[5] or 0, 1),
            'severidad': 'critico' if dias is not None and dias < 0 else
                         ('alto' if dias is not None and dias <= 7 else 'medio')
        })

    # ── 2. Stock bajo mínimo ──────────────────────────────────────────────────
    c.execute("""
        SELECT mp.codigo_mp, mp.nombre_comercial, mp.stock_minimo,
               COALESCE(mp.tipo_material,'MP') as tipo,
               COALESCE((
                   SELECT SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END)
                   FROM movimientos m
                   WHERE m.material_id = mp.codigo_mp AND m.estado_lote='VIGENTE'
               ), 0) as stock_actual
        FROM maestro_mps mp
        WHERE mp.activo = 1 AND COALESCE(mp.stock_minimo, 0) > 0
    """)
    stock_bajo = []
    for r in c.fetchall():
        codigo, nombre, st_min, tipo, st_act = r
        if st_act < st_min:
            ratio = st_act / st_min if st_min else 0
            stock_bajo.append({
                'codigo_mp': codigo, 'nombre': nombre,
                'stock_minimo': st_min, 'stock_actual': round(st_act, 1),
                'tipo_material': tipo, 'cobertura_pct': round(ratio * 100, 1),
                'severidad': 'critico' if ratio < 0.25 else ('alto' if ratio < 0.5 else 'medio')
            })
    stock_bajo.sort(key=lambda x: x['cobertura_pct'])

    # ── 3. Discrepancias de conteo cíclico no resueltas ───────────────────────
    discrepancias = []
    try:
        c.execute("""
            SELECT cf.id, cf.numero, cf.estanteria, cf.cerrado_en,
                   COUNT(ci.id) as n_items,
                   SUM(CASE WHEN ABS(ci.diferencia) > 0 THEN 1 ELSE 0 END) as n_dif
            FROM conteos_fisicos cf
            LEFT JOIN conteo_items ci ON cf.id = ci.conteo_id
            WHERE cf.estado = 'Cerrado' AND cf.ajuste_aplicado = 0
            GROUP BY cf.id
            HAVING n_dif > 0
            ORDER BY cf.cerrado_en DESC
            LIMIT 20
        """)
        for r in c.fetchall():
            discrepancias.append({
                'conteo_id': r[0], 'numero': r[1], 'estanteria': r[2],
                'cerrado_en': r[3], 'items_con_diferencia': r[5],
                'severidad': 'alto'
            })
    except sqlite3.OperationalError:
        # Tabla puede no tener columna ajuste_aplicado en versiones legacy
        pass

    # ── 4. Cuarentenas extendidas (>5 días esperando QC) ──────────────────────
    c.execute("""
        SELECT m.id, m.material_id, m.material_nombre, m.lote, m.fecha,
               m.cantidad, m.proveedor
        FROM movimientos m
        WHERE m.estado_lote IN ('CUARENTENA', 'CUARENTENA_EXTENDIDA')
          AND m.tipo = 'Entrada'
          AND m.fecha < ?
        ORDER BY m.fecha ASC
        LIMIT 50
    """, (hace_5,))
    cuarentena_extendida = [
        {'mov_id': r[0], 'material_id': r[1], 'material_nombre': r[2],
         'lote': r[3], 'fecha_ingreso': r[4], 'cantidad_g': r[5],
         'proveedor': r[6], 'severidad': 'alto'}
        for r in c.fetchall()
    ]

    total = (len(vencimientos) + len(stock_bajo) +
             len(discrepancias) + len(cuarentena_extendida))
    sevs = (
        [v['severidad'] for v in vencimientos] +
        [v['severidad'] for v in stock_bajo] +
        [v['severidad'] for v in discrepancias] +
        [v['severidad'] for v in cuarentena_extendida]
    )
    sev_orden = {'critico': 3, 'alto': 2, 'medio': 1, 'ok': 0}
    severidad_max = max(sevs, key=lambda s: sev_orden.get(s, 0)) if sevs else 'ok'

    return jsonify({
        'vencimientos':           vencimientos,
        'stock_bajo':             stock_bajo,
        'discrepancias':          discrepancias,
        'cuarentena_extendida':   cuarentena_extendida,
        'total':                  total,
        'severidad_max':          severidad_max,
        'evaluado_en':            hoy.isoformat(),
    })


# ─── KARDEX + VALORACIÓN FIFO ────────────────────────────────────────────────
# Reporte estándar contable para auditoría y costeo.

@bp.route('/api/planta/kardex/<codigo_mp>', methods=['GET'])
def planta_kardex(codigo_mp):
    """Kardex de un MP específico: entradas, salidas, saldo running, valor FIFO.

    Query params:
      - desde: YYYY-MM-DD (opcional, default hace 12 meses)
      - hasta: YYYY-MM-DD (opcional, default hoy)
    """
    u, err, code = _require_session()
    if err:
        return err, code

    from datetime import date, timedelta
    desde = (request.args.get('desde') or
             (date.today() - timedelta(days=365)).isoformat())
    hasta = request.args.get('hasta') or date.today().isoformat()

    conn = get_db(); c = conn.cursor()

    # Datos maestros
    c.execute("""SELECT codigo_mp, nombre_comercial, nombre_inci,
                        COALESCE(precio_referencia,0), COALESCE(stock_minimo,0),
                        COALESCE(tipo_material,'MP')
                 FROM maestro_mps WHERE codigo_mp=?""", (codigo_mp,))
    mp = c.fetchone()
    if not mp:
        return jsonify({'error': f'MP {codigo_mp} no existe'}), 404

    # Movimientos del rango
    c.execute("""SELECT id, fecha, tipo, cantidad, lote, observaciones,
                        proveedor, COALESCE(precio_kg,0), numero_oc, numero_factura,
                        estado_lote, fecha_vencimiento
                 FROM movimientos
                 WHERE material_id=? AND fecha >= ? AND fecha <= ?
                 ORDER BY fecha ASC, id ASC""",
              (codigo_mp, desde, hasta + 'T23:59:59'))
    rows = c.fetchall()

    # Algoritmo FIFO: cada entrada va a una "capa" (queue) con su precio.
    # Cada salida consume capas FIFO (más antigua primero) y registra el
    # costo unitario ponderado de esa salida.
    capas = []  # [(cantidad_kg_restante, precio_kg, lote)]
    movimientos = []
    saldo_g = 0.0
    valor_acum = 0.0

    for r in rows:
        mid, fecha, tipo, cant, lote, obs, prov, pkg, oc, fac, est_lote, fvenc = r
        cant_kg = (cant or 0) / 1000.0

        if tipo == 'Entrada':
            saldo_g += (cant or 0)
            costo_entrada = cant_kg * (pkg or 0)
            valor_acum += costo_entrada
            capas.append({
                'cantidad_kg_restante': cant_kg,
                'precio_kg': pkg or 0,
                'lote': lote, 'fecha': fecha,
            })
            mov = {
                'id': mid, 'fecha': fecha, 'tipo': 'Entrada',
                'cantidad_kg': round(cant_kg, 3), 'precio_kg': round(pkg or 0, 2),
                'costo': round(costo_entrada, 2), 'lote': lote, 'proveedor': prov,
                'oc': oc, 'factura': fac, 'estado_lote': est_lote,
                'fecha_vencimiento': fvenc,
                'saldo_g_running': round(saldo_g, 1),
                'valor_running': round(valor_acum, 2),
            }
        else:  # Salida
            saldo_g -= (cant or 0)
            # Consumir capas FIFO
            falta_kg = cant_kg
            costo_salida = 0.0
            consumos = []
            i = 0
            while falta_kg > 1e-9 and i < len(capas):
                if capas[i]['cantidad_kg_restante'] <= 1e-9:
                    i += 1
                    continue
                tomar = min(capas[i]['cantidad_kg_restante'], falta_kg)
                costo_salida += tomar * capas[i]['precio_kg']
                consumos.append({
                    'lote': capas[i]['lote'],
                    'kg': round(tomar, 3),
                    'precio_kg': capas[i]['precio_kg']
                })
                capas[i]['cantidad_kg_restante'] -= tomar
                falta_kg -= tomar
                if capas[i]['cantidad_kg_restante'] <= 1e-9:
                    i += 1
            valor_acum -= costo_salida
            costo_unit = (costo_salida / cant_kg) if cant_kg > 0 else 0
            mov = {
                'id': mid, 'fecha': fecha, 'tipo': 'Salida',
                'cantidad_kg': round(cant_kg, 3),
                'costo_unit_kg': round(costo_unit, 2),
                'costo_total': round(costo_salida, 2),
                'lote': lote, 'observaciones': obs,
                'consumos_fifo': consumos,
                'saldo_g_running': round(saldo_g, 1),
                'valor_running': round(valor_acum, 2),
            }
        movimientos.append(mov)

    # Capas remanentes = stock actual valorado FIFO
    stock_actual = [
        {
            'lote': cp['lote'],
            'cantidad_kg': round(cp['cantidad_kg_restante'], 3),
            'precio_kg': cp['precio_kg'],
            'valor': round(cp['cantidad_kg_restante'] * cp['precio_kg'], 2),
            'fecha_entrada': cp['fecha'],
        }
        for cp in capas if cp['cantidad_kg_restante'] > 1e-6
    ]

    # Totales
    total_entradas = sum(m['cantidad_kg'] for m in movimientos if m['tipo'] == 'Entrada')
    total_salidas = sum(m['cantidad_kg'] for m in movimientos if m['tipo'] == 'Salida')
    valor_actual = round(sum(c['valor'] for c in stock_actual), 2)

    return jsonify({
        'mp': {
            'codigo_mp': mp[0], 'nombre_comercial': mp[1],
            'nombre_inci': mp[2], 'precio_referencia': mp[3],
            'stock_minimo': mp[4], 'tipo_material': mp[5],
        },
        'rango': {'desde': desde, 'hasta': hasta},
        'totales': {
            'entradas_kg': round(total_entradas, 3),
            'salidas_kg':  round(total_salidas, 3),
            'saldo_actual_g': round(saldo_g, 1),
            'valor_actual_fifo': valor_actual,
            'movimientos_count': len(movimientos),
        },
        'movimientos': movimientos,
        'stock_actual_capas': stock_actual,
    })


@bp.route('/api/planta/valoracion-inventario', methods=['GET'])
def planta_valoracion_inventario():
    """Valoración total del inventario FIFO de todas las MPs activas.

    Calcula el valor de cada MP con su stock actual al precio FIFO
    (capas en orden de ingreso). Útil para reporte contable y cierre.
    Query: ?tipo_material=MP|Envase Primario|Envase Secundario|Empaque
    """
    u, err, code = _require_session()
    if err:
        return err, code

    tipo_filter = (request.args.get('tipo_material') or '').strip()
    conn = get_db(); c = conn.cursor()

    # MPs candidatas
    if tipo_filter in ('MP', 'Envase Primario', 'Envase Secundario', 'Empaque'):
        c.execute("""SELECT codigo_mp, nombre_comercial, COALESCE(tipo_material,'MP')
                     FROM maestro_mps WHERE activo=1 AND tipo_material=?""",
                  (tipo_filter,))
    else:
        c.execute("""SELECT codigo_mp, nombre_comercial, COALESCE(tipo_material,'MP')
                     FROM maestro_mps WHERE activo=1""")
    mps = c.fetchall()

    out = []
    valor_total = 0.0
    for codigo, nombre, tipo in mps:
        c.execute("""SELECT fecha, tipo, cantidad, COALESCE(precio_kg,0), lote
                     FROM movimientos WHERE material_id=?
                     ORDER BY fecha ASC, id ASC""", (codigo,))
        movs = c.fetchall()
        capas = []
        stock_g = 0
        for mv in movs:
            fecha, tp, cant, pkg, lote = mv
            cant_kg = (cant or 0) / 1000.0
            if tp == 'Entrada':
                stock_g += (cant or 0)
                capas.append([cant_kg, pkg or 0, lote])
            else:
                stock_g -= (cant or 0)
                falta = cant_kg
                for capa in capas:
                    if falta <= 1e-9:
                        break
                    if capa[0] <= 1e-9:
                        continue
                    tomar = min(capa[0], falta)
                    capa[0] -= tomar
                    falta -= tomar
        valor = sum(cap[0] * cap[1] for cap in capas if cap[0] > 1e-6)
        if stock_g > 0 or valor > 0:
            out.append({
                'codigo_mp': codigo, 'nombre': nombre, 'tipo_material': tipo,
                'stock_g': round(stock_g, 1),
                'stock_kg': round(stock_g / 1000, 3),
                'valor_fifo': round(valor, 2),
            })
            valor_total += valor

    out.sort(key=lambda x: x['valor_fifo'], reverse=True)

    # Totales por tipo de material
    por_tipo = {}
    for item in out:
        t = item['tipo_material']
        por_tipo.setdefault(t, {'count': 0, 'valor': 0, 'stock_kg': 0})
        por_tipo[t]['count'] += 1
        por_tipo[t]['valor'] += item['valor_fifo']
        por_tipo[t]['stock_kg'] += item['stock_kg']
    for t in por_tipo:
        por_tipo[t]['valor'] = round(por_tipo[t]['valor'], 2)
        por_tipo[t]['stock_kg'] = round(por_tipo[t]['stock_kg'], 3)

    return jsonify({
        'items': out,
        'valor_total_fifo': round(valor_total, 2),
        'count': len(out),
        'por_tipo_material': por_tipo,
        'filtro_tipo': tipo_filter or 'todos',
    })


# ═══════════════════════════════════════════════
#  MAQUILA 360 — API
# ═══════════════════════════════════════════════
