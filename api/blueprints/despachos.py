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


@bp.route('/api/recepcion/seguimiento')
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


@bp.route('/api/recepcion/lotes-cuarentena')
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


@bp.route('/api/recepcion/aprobar-lote', methods=['POST'])
def recepcion_aprobar_lote():
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


@bp.route('/api/recepcion/trazabilidad/<path:lote>')
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

