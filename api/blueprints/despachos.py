# blueprints/despachos.py — extraído de index.py (Fase C)
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

bp = Blueprint('despachos', __name__)

@bp.route('/recepcion')
def recepcion_panel():
    if 'compras_user' not in session:
        return redirect('/login?next=/recepcion')
    return Response(RECEPCION_HTML, mimetype='text/html')

@bp.route('/api/recepcion/detalle/<numero_oc>')
def recepcion_detalle_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, proveedor, estado, categoria, fecha, '
        'COALESCE(valor_total,0), creado_por, observaciones '
        'FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    oc = c.fetchone()
    if oc is None:
        return jsonify({'error': 'OC no encontrada'}), 404
    _INTANGIBLE = ('SVC', 'CC', 'Influencer/Marketing Digital')
    if oc[3] in _INTANGIBLE:
        return jsonify({
            'error': f'La OC {oc[0]} es de tipo {oc[3]} (intangible). '
                     'No requiere recepcion fisica — se gestiona directamente en Compras.'
        }), 422
    c.execute(
        'SELECT codigo_mp, nombre_mp, COALESCE(cantidad_g,0), '
        'COALESCE(precio_unitario,0), COALESCE(cantidad_recibida_g,0), '
        'COALESCE(lote_asignado,"") '
        'FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
    items = c.fetchall()
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

@bp.route('/api/recepcion/seguimiento')
def recepcion_seguimiento():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    # Recepcion debe ver TODAS las OCs activas — incluyendo Borrador/Revisada/
    # Aprobada/Pendiente — para que Catalina les pueda hacer seguimiento desde
    # que se crean hasta que llegan. Antes solo veia desde 'Autorizada' lo que
    # generaba que las OCs nuevas creadas desde solicitud (estado='Revisada')
    # quedaran invisibles en recepcion. Categoria-filter sigue excluyendo
    # servicios/CC/influencers (no requieren recepcion fisica de mercancia).
    # JOIN con solicitudes_compra: trae el numero SOL de origen para que
    # Recepcion vea la trazabilidad SOL → OC → recepcion. Sebastian pidió
    # 28-abr-2026: las OCs en transito deben mostrar de qué SOL vienen.
    c.execute(
        'SELECT oc.numero_oc, oc.fecha, oc.estado, oc.proveedor, oc.categoria, '
        'COALESCE(oc.valor_total,0), COALESCE(oc.fecha_recepcion,""), '
        'COALESCE(oc.observaciones,"") || '
        '  CASE WHEN COALESCE(oc.observaciones_recepcion,"") != "" '
        '       THEN " | RECEP: " || oc.observaciones_recepcion ELSE "" END, '
        'COALESCE(oc.tiene_discrepancias,0), '
        'COALESCE(oc.fecha_pago,""), COALESCE(oc.fecha_autorizacion,""), '
        'COALESCE(oc.recibido_por,""), '
        'COALESCE(sc.numero,""), '            # sol_numero (origen)
        'COALESCE(oc.fecha_entrega_est,"") '  # ETA estimada
        'FROM ordenes_compra oc '
        'LEFT JOIN solicitudes_compra sc ON sc.numero_oc = oc.numero_oc '
        "WHERE oc.estado IN "
        "('Borrador','Pendiente','Revisada','Aprobada','Autorizada','Recibida','Parcial','Pagada') "
        "AND oc.categoria NOT IN ('SVC','CC','Influencer/Marketing Digital','Cuenta de Cobro') "
        'ORDER BY '
        # Priorizar las que aun no se reciben para que aparezcan arriba
        "  CASE oc.estado "
        "    WHEN 'Borrador'   THEN 1 "
        "    WHEN 'Pendiente'  THEN 2 "
        "    WHEN 'Revisada'   THEN 3 "
        "    WHEN 'Aprobada'   THEN 4 "
        "    WHEN 'Autorizada' THEN 5 "
        "    WHEN 'Pagada'     THEN 6 "  # Pagada antes de Recibida = en transito
        "    WHEN 'Recibida'   THEN 7 "
        "    WHEN 'Parcial'    THEN 8 "
        "    ELSE 9 END, "
        '  oc.fecha DESC '
        'LIMIT 300')
    rows = c.fetchall()
    # Estado derivado "en_transito": OC pagada o autorizada PERO no recibida
    def _en_transito(estado, fecha_recep):
        return estado in ('Autorizada', 'Pagada') and not fecha_recep
    return jsonify([
        {'numero_oc': r[0], 'fecha': r[1], 'estado': r[2], 'proveedor': r[3],
         'categoria': r[4], 'valor_total': r[5], 'fecha_recepcion': r[6],
         'observaciones': r[7], 'tiene_discrepancias': r[8],
         'fecha_pago': r[9], 'fecha_autorizacion': r[10], 'recibido_por': r[11],
         'sol_numero': r[12], 'fecha_entrega_est': r[13],
         'en_transito': _en_transito(r[2], r[6])}
        for r in rows
    ])

@bp.route('/api/recepcion/lotes-cuarentena')
def recepcion_lotes_cuarentena():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, material_id, material_nombre, cantidad, lote,
                        fecha_vencimiento, proveedor, fecha, numero_oc
                 FROM movimientos
                 WHERE tipo='Entrada' AND (estado_lote='Cuarentena' OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))
                 ORDER BY fecha DESC LIMIT 100""")
    rows = c.fetchall()
    cols = ['id','material_id','material_nombre','cantidad','lote','fecha_vencimiento','proveedor','fecha','numero_oc']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/recepcion/aprobar-lote', methods=['POST'])
def recepcion_aprobar_lote():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    mov_id = d.get('mov_id')
    nuevo_estado = d.get('estado', 'Aprobado')  # Aprobado o Rechazado
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    usuario = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=?, operador=? WHERE id=?",
              (nuevo_estado, usuario, mov_id))
    conn.commit()
    return jsonify({'ok': True, 'estado': nuevo_estado})

@bp.route('/api/recepcion/trazabilidad/<path:lote>')
def recepcion_trazabilidad_lote(lote):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
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
    return jsonify({'lote': lote, 'movimientos': movs, 'oc': oc_info})

# ─── Recursos Humanos ────────────────────────────────────────────────────────

