# blueprints/despachos.py · extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS
try:
    from config import MP_LIBERA_USERS
except Exception:
    MP_LIBERA_USERS = set()
try:
    from config import ASEGURAMIENTO_USERS, TECNICA_USERS  # Sebastián 8-jul: aprobar/liberar MP = rol calidad ampliado
except Exception:
    ASEGURAMIENTO_USERS, TECNICA_USERS = set(), set()
from database import get_db
from audit_helpers import audit_log
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
    # Pago directo (sin material físico) → no se recibe. Alineado con recibir_oc (revisor 19-jul H2:
    # antes faltaban los nombres largos 'Servicio'/'Cuenta de Cobro' → una OC de servicio tecleada
    # directo se renderizaba como recepción normal aunque el submit la frenara).
    try:
        from blueprints.compras import CATEGORIAS_PAGO_DIRECTO as _PDD
        _INTANGIBLE = tuple(set(_PDD) | {'SVC', 'CC', 'Influencer/Marketing Digital'})
    except Exception:
        _INTANGIBLE = ('SVC', 'CC', 'Influencer/Marketing Digital', 'Servicio', 'Cuenta de Cobro')
    if oc[3] in _INTANGIBLE:
        return jsonify({
            'error': f'La OC {oc[0]} es de tipo {oc[3]} (intangible). '
                     'No requiere recepcion fisica · se gestiona directamente en Compras.'
        }), 422
    # Recepcion se identifica por INCI + codigo (Sebastian 12-jun · el comercial
    # confunde por proveedor). JOIN a maestro para traer el INCI; nombre_mp
    # (comercial) sigue disponible pero el front ya no lo muestra.
    c.execute(
        'SELECT oi.codigo_mp, oi.nombre_mp, COALESCE(oi.cantidad_g,0), '
        'COALESCE(oi.precio_unitario,0), COALESCE(oi.cantidad_recibida_g,0), '
        "COALESCE(oi.lote_asignado,''), COALESCE(m.nombre_inci,'') "
        'FROM ordenes_compra_items oi '
        'LEFT JOIN maestro_mps m ON m.codigo_mp = oi.codigo_mp '
        'WHERE oi.numero_oc=?', (numero_oc,))
    items = c.fetchall()
    try:
        from blueprints.compras import _CATS_CONSUMO as _CC
    except Exception:
        _CC = ()
    _es_consumo = oc[3] in _CC  # consumible/EPP/papelería → recepción ADMINISTRATIVA (sin cuarentena)
    # Enriquecer items (Sebastián 21-jul): unidad correcta (MP=g · envases/consumibles=uds),
    # descripción COMPLETA (los envases mostraban solo el código) y detectar CARGOS que NO se
    # reciben (flete, domicilio, calibración, servicios embebidos en la OC física).
    _mee_desc = {}
    try:
        _codes = [(i[0] or '').strip().upper() for i in items if (i[0] or '').strip().upper().startswith('MEE-')]
        if _codes:
            _ph = ','.join('?' for _ in _codes)
            for r in c.execute("SELECT UPPER(TRIM(codigo)), COALESCE(descripcion,'') FROM maestro_mee "
                               "WHERE UPPER(TRIM(codigo)) IN (" + _ph + ")", tuple(_codes)).fetchall():
                _mee_desc[r[0]] = r[1]
    except Exception:
        pass
    _CARGO_KW = ('FLETE', 'DOMICILIO', 'ENVIO', 'ENVÍO', 'TRANSPORTE', 'CALIBRAC',
                 'SERVICIO', 'MANTENIMIENTO', 'INSTALAC')

    def _item_dict(i):
        cod = (i[0] or '').strip()
        nom = (i[1] or '').strip()
        inci = (i[6] or '').strip()
        cu = cod.upper()
        es_mee = cu.startswith('MEE-')
        desc_full = (_mee_desc.get(cu) or nom or cod) if es_mee else (nom or cod)
        _txt = (nom + ' ' + cod).upper()
        es_cargo = (not es_mee) and (not inci) and any(k in _txt for k in _CARGO_KW)
        # Unidad (fix revisión ultracode): envases=uds · consumibles=uds · MP=g (aunque no tenga INCI
        # cargado todavía, una MP en OC MP se mide en gramos). Antes MP sin INCI salía 'uds' por error.
        if es_mee or _es_consumo:
            unidad = 'uds'
        else:
            unidad = 'g'
        return {'codigo_mp': cod, 'nombre_mp': nom, 'cantidad_g': i[2],
                'precio_unitario': i[3], 'cantidad_recibida_g': i[4], 'lote_asignado': i[5],
                'inci': inci, 'descripcion_full': desc_full, 'unidad': unidad,
                'es_mee': es_mee, 'es_cargo': es_cargo}
    return jsonify({
        'numero_oc': oc[0], 'proveedor': oc[1], 'estado': oc[2],
        'categoria': oc[3], 'fecha': oc[4], 'valor_total': oc[5],
        'creado_por': oc[6], 'observaciones': oc[7], 'es_consumo': _es_consumo,
        'items': [_item_dict(i) for i in items]
    })

@bp.route('/api/recepcion/seguimiento')
def recepcion_seguimiento():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    # Recepcion debe ver TODAS las OCs activas · incluyendo Borrador/Revisada/
    # Aprobada/Pendiente · para que Catalina les pueda hacer seguimiento desde
    # que se crean hasta que llegan. Antes solo veia desde 'Autorizada' lo que
    # generaba que las OCs nuevas creadas desde solicitud (estado='Revisada')
    # quedaran invisibles en recepcion. Categoria-filter sigue excluyendo
    # servicios/CC/influencers (no requieren recepcion fisica de mercancia).
    # JOIN con solicitudes_compra: trae el numero SOL de origen para que
    # Recepcion vea la trazabilidad SOL → OC → recepcion. Sebastian pidió
    # 28-abr-2026: las OCs en transito deben mostrar de qué SOL vienen.
    # Sebastián 19-jul (consumibles en recepción): Recepción monitorea MP/MEE (bodega, con cuarentena)
    # Y consumibles/EPP/papelería (recepción ADMINISTRATIVA · comprobar que llegó lo pedido, sin cuarentena).
    # Solo se excluye el PAGO DIRECTO (servicios/CC/influencer · pago puro sin material físico). Antes se
    # excluía todo CATEGORIAS_SIN_KARDEX (incl. consumibles) · ahora `recibir_oc` sí los recibe (admin).
    try:
        from blueprints.compras import CATEGORIAS_PAGO_DIRECTO as _PD
    except Exception:
        _PD = ('SVC', 'CC', 'Cuenta de Cobro', 'Servicio')
    _excl = tuple(set(_PD) | {'SVC', 'CC', 'Influencer/Marketing Digital', 'Cuenta de Cobro', 'Servicio'})
    _not_in = ','.join("'" + x.replace("'", "''") + "'" for x in _excl)
    c.execute(
        'SELECT oc.numero_oc, oc.fecha, oc.estado, oc.proveedor, oc.categoria, '
        "COALESCE(oc.valor_total,0), COALESCE(oc.fecha_recepcion,''), "
        "COALESCE(oc.observaciones,'') || "
        "  CASE WHEN COALESCE(oc.observaciones_recepcion,'') != '' "
        "       THEN ' | RECEP: ' || oc.observaciones_recepcion ELSE '' END, "
        "COALESCE(oc.tiene_discrepancias,0), "
        "COALESCE(oc.fecha_pago,''), COALESCE(oc.fecha_autorizacion,''), "
        "COALESCE(oc.recibido_por,''), "
        # H4 (12-jun): una fila por OC (numero_oc no es UNIQUE · N SOLs → 1 OC).
        # PERF (15-jul): en vez de un subquery CORRELACIONADO por fila (×300), un
        # LEFT JOIN a la SOL mínima PRE-AGRUPADA (1 sola pasada · no duplica · PG-safe).
        "COALESCE(s.sol_min,''), "  # sol_numero origen
        "COALESCE(oc.fecha_entrega_est,'') "  # ETA estimada
        'FROM ordenes_compra oc '
        "LEFT JOIN (SELECT numero_oc, MIN(numero) AS sol_min FROM solicitudes_compra "
        "           WHERE COALESCE(numero_oc,'') != '' GROUP BY numero_oc) s "
        "  ON s.numero_oc = oc.numero_oc "
        "WHERE oc.estado IN "
        "('Borrador','Pendiente','Revisada','Aprobada','Autorizada','Recibida','Parcial','Pagada') "
        "AND COALESCE(oc.categoria,'MP') NOT IN (" + _not_in + ") "
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
    """Lotes en cuarentena pendientes de QC.

    Sebastian 5-may-2026 (audit zero-error Recepciones): ANTES filtraba
    por estado_lote='Cuarentena' (Capitalizado) pero compras.py escribe
    'CUARENTENA' (UPPERCASE) cuando se recibe via OC. Resultado: lotes
    recepcionados via OC NO APARECIAN en la bandeja QC · trazabilidad
    INVIMA rota silenciosamente.

    FIX: UPPER() comparison · matchea 'Cuarentena', 'CUARENTENA',
    'cuarentena' indistintamente. Tambien incluye CUARENTENA_EXTENDIDA
    (lotes que requirieron AQL adicional).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    # Sebastián 8-jul: alineado EXACTO a /api/lotes/cuarentena (la vista CC del CEO) para que Laura/Yuliel vean
    # LO MISMO en su módulo Calidad que en la pantalla de Planta. Antes esta lista incluía TODOS los tipos
    # (envases/EPP) y lotes con estado_lote NULL (viejos) → "se ve diferente". Ahora: SOLO Materia Prima
    # (COC-PRO-001) + estado CUARENTENA explícito (UPPER · M23). Los envases van por su flujo de calidad aparte.
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.cantidad, m.lote,
                        m.fecha_vencimiento, m.proveedor, m.fecha, m.numero_oc, m.estado_lote
                 FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 LEFT JOIN ordenes_compra oc ON oc.numero_oc = m.numero_oc
                 WHERE UPPER(COALESCE(m.estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA') AND m.tipo='Entrada'
                   AND TRIM(COALESCE(m.material_id,'')) <> ''
                   AND COALESCE(m.observaciones,'') NOT LIKE '%::ANULADA-mov#%'
                   AND UPPER(COALESCE(mp.tipo_material,'MP'))='MP'
                   AND UPPER(COALESCE(oc.categoria,'MATERIA PRIMA')) IN ('MATERIA PRIMA','MATERIA_PRIMA','MP','')
                 ORDER BY m.fecha DESC LIMIT 100""")
    rows = c.fetchall()
    cols = ['id','material_id','material_nombre','cantidad','lote',
            'fecha_vencimiento','proveedor','fecha','numero_oc','estado_lote']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/recepcion/aprobar-lote', methods=['POST'])
def recepcion_aprobar_lote():
    """Aprobar o rechazar un lote en cuarentena · decisión INVIMA de calidad.

    Solo Calidad/Admin puede liberar (Resolución 2214/2021 art. 10).
    Estados válidos: 'Aprobado' (libera para uso) o 'Rechazado' (bloquea uso).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario = session.get('compras_user', '')
    if usuario not in (set(CALIDAD_USERS) | set(ASEGURAMIENTO_USERS) | set(TECNICA_USERS) | set(ADMIN_USERS) | set(MP_LIBERA_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin puede aprobar lotes'}), 403
    d = request.get_json() or {}
    mov_id = d.get('mov_id')
    nuevo_estado = d.get('estado', 'Aprobado')
    motivo = (d.get('motivo') or '').strip()
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    try:
        mov_id = int(mov_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'mov_id inválido'}), 400
    if nuevo_estado not in ('Aprobado', 'Rechazado'):
        return jsonify({'error': "estado debe ser 'Aprobado' o 'Rechazado'"}), 400
    if nuevo_estado == 'Rechazado' and len(motivo) < 10:
        return jsonify({'error': 'motivo (≥10 chars) requerido para rechazar'}), 400
    conn = get_db(); c = conn.cursor()
    # Capturar estado anterior para audit log
    antes_row = c.execute(
        "SELECT estado_lote, lote, material_nombre, cantidad, operador "
        "FROM movimientos WHERE id=?", (mov_id,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Movimiento no encontrado'}), 404
    antes = dict(antes_row)
    # P0 (12-jun · hallazgo Fable): persistir estado_lote CANONICO en mayusculas.
    # Antes guardaba 'Aprobado'/'Rechazado' (Title-case) y el FEFO filtra
    # NOT IN ('...','RECHAZADO') case-sensitive -> un lote RECHAZADO se colaba a
    # produccion. Aprobado->VIGENTE (usable), Rechazado->RECHAZADO (bloqueado).
    estado_canon = 'VIGENTE' if nuevo_estado == 'Aprobado' else 'RECHAZADO'
    # FIX 17-jun (auditoría Planta · M27/INVIMA) · esta ruta de disposición SOLO puede
    # actuar sobre un lote EN CUARENTENA (igual que liberar_cuarentena). Sin este guard
    # hacía UPDATE incondicional → podía REVIVIR un lote RECHAZADO a VIGENTE (material
    # rechazado vuelto usable/vendible) o pisar un VIGENTE. CAS: condición en el WHERE +
    # rowcount → dos disposiciones concurrentes del mismo lote no se cruzan.
    # FIX 7-jul (audit ultracode): alinear el CAS con lo que la BANDEJA lista (incluye lotes LEGACY con
    # estado_lote IS NULL · pre-cuarentena) · antes el CAS exigía CUARENTENA estricto → COALESCE(NULL,'')=''
    # no matcheaba → 409 al disponer un lote legacy que la bandeja sí mostraba. RECHAZADO/VIGENTE (no NULL)
    # siguen bloqueados (no revive material rechazado).
    c.execute("UPDATE movimientos SET estado_lote=?, operador=? "
              "WHERE id=? AND (UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA') "
              "               OR (estado_lote IS NULL AND COALESCE(lote,'')<>''))",
              (estado_canon, usuario, mov_id))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({
            'error': f"El lote no está en cuarentena (estado: {antes.get('estado_lote','')}) · "
                     f"no se puede disponer por esta ruta",
            'codigo': 'ESTADO_NO_LIBERABLE',
        }), 409
    accion = 'APROBAR_LOTE' if nuevo_estado == 'Aprobado' else 'RECHAZAR_LOTE'
    audit_log(c, usuario=usuario, accion=accion, tabla='movimientos',
              registro_id=mov_id, antes=antes,
              despues={'estado_lote': nuevo_estado, 'operador': usuario,
                       'motivo': motivo} if motivo else
                      {'estado_lote': nuevo_estado, 'operador': usuario},
              detalle=f"{accion} lote {antes.get('lote','·')} ({antes.get('material_nombre','')})"
                      + (f" · motivo: {motivo}" if motivo else ""))
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

