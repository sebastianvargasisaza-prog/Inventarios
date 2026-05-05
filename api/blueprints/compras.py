# blueprints/compras.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
import logging
from datetime import datetime, timedelta

log = logging.getLogger('compras')
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import (
    DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, COMPRAS_ACCESS,
    USER_EMAILS, LIMITES_APROBACION_OC,
)
from database import get_db
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec
from audit_helpers import audit_log, intentar_insert_con_retry
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

bp = Blueprint('compras', __name__)


# ── Helpers de permisos granulares ────────────────────────────────────────────
# Los grupos:
#   COMPRAS_ACCESS    = {catalina, mayra, alejandro, sebastian}
#                       Pueden CREAR solicitudes/OCs, recibir mercancía, gestionar
#                       proveedores, generar OCs desde Planta.
#   ADMIN_USERS       = {sebastian, alejandro}
#                       Pueden ejecutar TODAS las operaciones, incluso autorizar
#                       y pagar (CONTADORA está excluida explícitamente de
#                       autorización/pago para mantener segregación de duties).
#   CONTADORA_USERS   = {mayra, catalina}
#                       Pueden ver/gestionar pero NO autorizar/pagar OCs
#                       directamente — la autorización es responsabilidad de
#                       admin. (Mayra ve todo lo financiero; pagar implica
#                       movimiento de dinero que necesita firma de admin.)


def _require_compras_session():
    """Cualquier user autenticado puede hacer LECTURAS en compras."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    return u, None, None


def _require_compras_write():
    """Para CREAR/EDITAR solicitudes y OCs: COMPRAS_ACCESS o ADMIN."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    allowed = COMPRAS_ACCESS | ADMIN_USERS
    if u not in allowed:
        return None, jsonify({
            'error': 'Sin acceso a operaciones de Compras',
            'detail': f"User '{u}' no está en COMPRAS_ACCESS"
        }), 403
    return u, None, None


def _require_authorize_oc():
    """Para AUTORIZAR/PAGAR OCs: COMPRAS_ACCESS o ADMIN."""
    return _require_compras_write()


def _check_monto_limit(usuario, monto):
    """Valida que el usuario pueda autorizar el monto.

    Retorna (None, None) si OK, o (response, status_code) si excede el límite.
    Admins (límite None) siempre pueden. Otros tienen LIMITES_APROBACION_OC.
    """
    if usuario in ADMIN_USERS:
        return None, None
    limite = LIMITES_APROBACION_OC.get(usuario)
    if limite is None:
        # Usuario sin límite explícito: usar 0 (no puede autorizar nada)
        return jsonify({
            'error': f"Usuario '{usuario}' no tiene límite de aprobación configurado",
            'detail': 'Solo usuarios con LIMITES_APROBACION_OC en config pueden autorizar.'
        }), 403
    if monto > limite:
        return jsonify({
            'error': f'Monto ${monto:,.0f} excede tu límite de aprobación (${limite:,.0f})',
            'detail': 'Esta OC requiere aprobación de un administrador.',
            'codigo': 'EXCEDE_LIMITE_APROBACION',
            'limite_usuario': limite,
            'monto_solicitado': monto,
        }), 403
    return None, None

def _is_animus_payment(c, numero_oc=None, beneficiario_nombre=None,
                       observaciones=None, categoria=None):
    """Determina si un pago debe atribuirse a ANIMUS LAB S.A.S.

    Empresa pagadora del grupo HHA:
      - Influencers, marketing digital, cuenta de cobro → ANIMUS LAB
      - Mercancía, MPs, planta, servicios técnicos     → ESPAGIRIA

    Detección multi-señal — cualquiera prende Animus, así soporta CEs
    legacy (creados antes del dispatch) y casos donde la categoría está
    vacía o mal poblada:

      1. categoria contiene 'influencer' / 'marketing' / 'cuenta de cobro'
      2. existe un row en pagos_influencers para el numero_oc
      3. solicitudes_compra.influencer_id NOT NULL para el numero_oc
      4. beneficiario_nombre matchea un row de marketing_influencers
      5. observaciones contienen la palabra 'influencer'

    Cualquier excepción de SQL (tabla legacy faltante en deploy viejo) se
    silencia y se evalúa la siguiente señal — la falta de tabla nunca
    debe romper la generación del PDF.
    """
    # Señal 1: keyword en categoría
    cat_low = (categoria or '').lower()
    if ('influencer' in cat_low
            or 'marketing' in cat_low
            or 'cuenta de cobro' in cat_low):
        return True

    # Señal 2: pago_influencers row
    if numero_oc:
        try:
            row = c.execute(
                "SELECT 1 FROM pagos_influencers WHERE numero_oc=? LIMIT 1",
                (numero_oc,)
            ).fetchone()
            if row:
                return True
        except sqlite3.OperationalError:
            pass

        # Señal 3: solicitudes_compra.influencer_id
        try:
            row = c.execute(
                "SELECT influencer_id FROM solicitudes_compra "
                "WHERE numero_oc=? AND influencer_id IS NOT NULL LIMIT 1",
                (numero_oc,)
            ).fetchone()
            if row and row[0]:
                return True
        except sqlite3.OperationalError:
            pass

    # Señal 4: beneficiario en marketing_influencers
    if beneficiario_nombre:
        try:
            row = c.execute(
                "SELECT 1 FROM marketing_influencers "
                "WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?)) LIMIT 1",
                (beneficiario_nombre,)
            ).fetchone()
            if row:
                return True
        except sqlite3.OperationalError:
            pass

    # Señal 5: observaciones contienen 'influencer'
    if observaciones and 'influencer' in (observaciones or '').lower():
        return True

    return False


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
    """Dashboard stats. Sebastian (30-abr-2026): los paneles 'Vencimientos
    próximos', 'Top 5 MPs' y 'Estado general de lotes' aparecían vacíos —
    el cálculo dependía del campo estado_lote que NO se mantiene
    automáticamente. Fix: calcular los estados dinámicamente desde
    fecha_vencimiento, y soportar variantes de tipo de movimiento.
    """
    from datetime import date
    hoy = date.today().isoformat()
    conn = get_db(); c = conn.cursor()

    # Soporta 'Entrada', 'Ingreso', 'Ajuste', 'Devolucion' como entradas;
    # 'Salida', 'Consumo' como salidas.
    SUMA_STOCK = (
        "SUM(CASE "
        "WHEN tipo IN ('Entrada','Ingreso','Ajuste','Devolucion','Devolución') THEN cantidad "
        "WHEN tipo IN ('Salida','Consumo') THEN -cantidad "
        "ELSE 0 END)"
    )
    FILTRO_ENTRADA = "tipo IN ('Entrada','Ingreso','Ajuste','Devolucion','Devolución')"

    # ── Vencimientos próximos 6 meses ─────────────────────────────────────
    # Calculo a nivel LOTE — agrupar entradas por (material_id, lote) y
    # restar consumos, mostrar solo lotes con stock_restante > 0 con
    # fecha_vencimiento en próximos 180 dias.
    venc_por_mes = {}
    try:
        c.execute(f"""
            WITH lote_stock AS (
              SELECT material_id, lote,
                     MIN(fecha_vencimiento) as venc,
                     {SUMA_STOCK} as stock_restante_g
              FROM movimientos
              WHERE lote IS NOT NULL AND lote != ''
              GROUP BY material_id, lote
              HAVING stock_restante_g > 0
            )
            SELECT venc, COUNT(*) as n, SUM(stock_restante_g) as total_g
            FROM lote_stock
            WHERE venc IS NOT NULL AND venc >= ? AND venc <= date(?, '+180 days')
            GROUP BY substr(venc, 1, 7)
            ORDER BY venc
        """, (hoy, hoy))
        for row in c.fetchall():
            if row[0]:
                mes = str(row[0])[:7]
                venc_por_mes[mes] = {'lotes': row[1], 'kg': round((row[2] or 0)/1000, 1)}
    except Exception as e:
        # Fallback simple si la query agrupada falla
        try:
            c.execute(f"""
                SELECT fecha_vencimiento, COUNT(*) as n, SUM(cantidad) as total_g
                FROM movimientos
                WHERE {FILTRO_ENTRADA}
                  AND fecha_vencimiento IS NOT NULL
                  AND fecha_vencimiento >= ?
                  AND fecha_vencimiento <= date(?, '+180 days')
                GROUP BY substr(fecha_vencimiento, 1, 7)
            """, (hoy, hoy))
            for row in c.fetchall():
                if row[0]:
                    mes = str(row[0])[:7]
                    venc_por_mes[mes] = {'lotes': row[1], 'kg': round((row[2] or 0)/1000, 1)}
        except Exception:
            pass

    # ── Alertas reabastecimiento: MPs bajo mínimo ─────────────────────────
    try:
        c.execute(f"""SELECT COUNT(*) FROM maestro_mps m
                     LEFT JOIN (SELECT material_id, {SUMA_STOCK} as stock
                                FROM movimientos GROUP BY material_id) s
                       ON m.codigo_mp=s.material_id
                     WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(s.stock,0)<m.stock_minimo""")
        mps_bajo_minimo = c.fetchone()[0] or 0
    except Exception:
        mps_bajo_minimo = 0

    # ── Estado general de lotes — CALCULADO desde fecha_vencimiento ──────
    # No depender de estado_lote (campo desactualizado). Calcular por:
    #   VENCIDO: fecha_vencimiento < hoy AND stock > 0
    #   CRITICO: 0-30 dias
    #   PROXIMO: 31-90 dias
    estados = {'VENCIDO': 0, 'CRITICO': 0, 'PROXIMO': 0}
    try:
        c.execute(f"""
            WITH lote_stock AS (
              SELECT material_id, lote, MIN(fecha_vencimiento) as venc,
                     {SUMA_STOCK} as stock_g
              FROM movimientos
              WHERE lote IS NOT NULL AND lote != '' AND fecha_vencimiento IS NOT NULL
              GROUP BY material_id, lote
              HAVING stock_g > 0
            )
            SELECT
              SUM(CASE WHEN venc < date('now') THEN 1 ELSE 0 END) as vencidos,
              SUM(CASE WHEN venc >= date('now') AND venc <= date('now','+30 days') THEN 1 ELSE 0 END) as criticos,
              SUM(CASE WHEN venc > date('now','+30 days') AND venc <= date('now','+90 days') THEN 1 ELSE 0 END) as proximos
            FROM lote_stock
        """)
        r = c.fetchone()
        if r:
            estados = {'VENCIDO': r[0] or 0, 'CRITICO': r[1] or 0, 'PROXIMO': r[2] or 0}
    except Exception:
        pass

    # ── Top 5 MPs por stock actual ────────────────────────────────────────
    top_stock = []
    try:
        c.execute(f"""SELECT material_id, material_nombre, {SUMA_STOCK} as stock
                     FROM movimientos
                     GROUP BY material_id, material_nombre
                     HAVING stock > 0
                     ORDER BY stock DESC LIMIT 5""")
        top_stock = [{'codigo': r[0], 'nombre': r[1], 'kg': round((r[2] or 0)/1000, 1)}
                     for r in c.fetchall()]
    except Exception:
        pass

    # ── Stock total en kg ─────────────────────────────────────────────────
    try:
        c.execute(f"SELECT {SUMA_STOCK} FROM movimientos")
        stock_total_g = c.fetchone()[0] or 0
    except Exception:
        stock_total_g = 0

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
    conn = get_db(); c = conn.cursor()

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
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) FROM ordenes_compra WHERE numero_oc LIKE ?", (f"OC-{datetime.now().strftime('%Y')}-%",)); num=(c.fetchone()[0] or 0)+1
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
            eb += '  CANTIDAD A PEDIR: ' + f"{int(it['cantidad_pedir']):,}".replace(',', '.') + ' g\n'
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

    conn.commit()
    return jsonify({
        'message': f'{len(ordenes_creadas)} OC(s) generadas automaticamente',
        'ordenes': ordenes_creadas
    }), 201

# ── MÓDULO COMPRAS ──────────────────────────────────────────────────────────
@bp.route('/api/compras/influencer/limpiar-no-pagadas', methods=['GET', 'POST'])
def limpiar_influencer_no_pagadas():
    """Limpia SOLs/OCs de Influencer/Marketing/CC que NO se han pagado.

    Sebastian (30-abr-2026): "elimíname todo lo que quedó en influencers
    de compras que ya no son para pagar no se de donde salieron".

    Modo dry-run (default): GET o POST sin {confirm:true} → devuelve
    la lista de candidatos sin borrar nada. Para revisar antes.

    Modo real: POST {confirm:true} → ejecuta borrado.
    Solo admin (sebastian/alejandro).

    Borra:
      - SOL con categoria influencer/marketing/cuenta_de_cobro
        Y estado IN ('Pendiente','Aprobada','Rechazada')  ← NO 'Pagada'
        Y la OC vinculada NO tiene pagos efectivos.
      - OC vinculada (si no esta pagada) + sus items + pagos_influencers
        Pendientes (preserva los Pagados, son historial).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = (session.get('compras_user') or '').lower()
    if user not in {a.lower() for a in ADMIN_USERS}:
        return jsonify({'error': 'Solo admin'}), 403

    payload = request.get_json(silent=True) or {}
    confirm = payload.get('confirm') is True

    conn = get_db(); c = conn.cursor()
    sols = c.execute("""
        SELECT numero, solicitante, valor, estado, numero_oc, categoria,
               observaciones, fecha
        FROM solicitudes_compra
        WHERE (LOWER(COALESCE(categoria,'')) LIKE '%influencer%'
               OR LOWER(COALESCE(categoria,'')) LIKE '%marketing%'
               OR LOWER(COALESCE(categoria,'')) LIKE '%cuenta de cobro%')
          AND estado IN ('Pendiente','Aprobada','Rechazada')
        ORDER BY numero DESC
    """).fetchall()

    candidatos = []
    for s in sols:
        numero, solicitante, valor, estado, oc_num, cat, obs, fecha = s
        razon_skip = None
        n_pagos_oc = 0
        n_pagos_inf_pagados = 0
        if oc_num:
            try:
                n_pagos_oc = c.execute(
                    "SELECT COUNT(*) FROM pagos_oc WHERE numero_oc=?", (oc_num,)
                ).fetchone()[0] or 0
            except sqlite3.OperationalError:
                n_pagos_oc = 0
            try:
                n_pagos_inf_pagados = c.execute(
                    "SELECT COUNT(*) FROM pagos_influencers WHERE numero_oc=? AND estado='Pagada'",
                    (oc_num,)
                ).fetchone()[0] or 0
            except sqlite3.OperationalError:
                n_pagos_inf_pagados = 0
            if n_pagos_oc > 0 or n_pagos_inf_pagados > 0:
                razon_skip = f'OC {oc_num} tiene {n_pagos_oc} pagos_oc + {n_pagos_inf_pagados} pagos_inf Pagados'

        # Extraer beneficiario de obs si existe
        benef = ''
        if obs:
            import re as _re
            m = _re.search(r'BENEFICIARIO:\s*([^|]+)', obs, _re.IGNORECASE)
            if m: benef = m.group(1).strip()

        candidatos.append({
            'numero': numero,
            'solicitante': solicitante,
            'beneficiario': benef,
            'valor': valor or 0,
            'estado': estado,
            'numero_oc': oc_num,
            'fecha': fecha,
            'categoria': cat,
            'safe_to_delete': razon_skip is None,
            'razon_skip': razon_skip,
        })

    elegibles = [x for x in candidatos if x['safe_to_delete']]
    omitidos = [x for x in candidatos if not x['safe_to_delete']]

    if not confirm:
        return jsonify({
            'dry_run': True,
            'total_candidatos': len(candidatos),
            'a_borrar': len(elegibles),
            'omitidos_por_pagos': len(omitidos),
            'candidatos': elegibles,
            'omitidos': omitidos,
            'mensaje': f'Dry-run. {len(elegibles)} se borrarian, {len(omitidos)} omitidos por tener pagos. POST con {{"confirm":true}} para ejecutar.',
        })

    # Modo confirm — borrar
    eliminados = []
    for cand in elegibles:
        numero = cand['numero']
        oc_num = cand['numero_oc']
        # Borrar pagos_influencers Pendiente (preservar Pagada en otra OC, no aplica aqui)
        if oc_num:
            try:
                c.execute("DELETE FROM pagos_influencers WHERE numero_oc=? AND estado != 'Pagada'", (oc_num,))
            except sqlite3.OperationalError:
                pass
            # Borrar items
            try:
                c.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc_num,))
            except sqlite3.OperationalError:
                pass
            # Borrar OC si no esta pagada
            try:
                c.execute("DELETE FROM ordenes_compra WHERE numero_oc=? AND estado != 'Pagada'", (oc_num,))
            except sqlite3.OperationalError:
                pass
        # Borrar SOL items + SOL
        try:
            c.execute("DELETE FROM solicitudes_compra_items WHERE numero_solicitud=?", (numero,))
        except sqlite3.OperationalError:
            pass
        c.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
        eliminados.append(numero)

    conn.commit()
    return jsonify({
        'ok': True,
        'eliminados': eliminados,
        'total_eliminados': len(eliminados),
        'omitidos_por_pagos': len(omitidos),
    })


@bp.route('/api/solicitudes-compra/<numero>', methods=['DELETE'])
def eliminar_solicitud(numero):
    """Elimina una solicitud de compra y limpia OC asociada cuando aplica.

    Reglas:
    - OC en estado Borrador/Rechazada → se borra junto con sus items.
    - OC en estado Aprobada Y categoría es Influencer/Marketing/CC Y NO tiene
      pagos en pagos_oc Y NO tiene pago en pagos_influencers con estado='Pagada'
        → se borra todo (OC + items + pagos_influencers pendientes).
    - OC en cualquier otro estado o con pagos hechos → se borra SOLO la
      solicitud, la OC se conserva (mantiene historial).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT estado, numero_oc, categoria FROM solicitudes_compra WHERE numero=?",
              (numero.upper(),))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'No encontrada'}), 404
    estado, numero_oc, categoria = row[0], row[1], (row[2] or '').strip()

    oc_borrada = False
    pagos_inf_borrados = 0
    is_intangible = categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro')

    if numero_oc and numero_oc.strip():
        cur = conn.cursor()
        cur.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
        oc_row = cur.fetchone()
        if oc_row:
            oc_estado = oc_row[0]
            puede_borrar_oc = False
            if oc_estado in ('Borrador', 'Rechazada'):
                puede_borrar_oc = True
            elif oc_estado == 'Aprobada' and is_intangible:
                # Verificar que NO haya pagos efectivos
                try:
                    cur.execute("SELECT COUNT(*) FROM pagos_oc WHERE numero_oc=?", (numero_oc,))
                    n_pagos_oc = cur.fetchone()[0] or 0
                except sqlite3.OperationalError:
                    n_pagos_oc = 0
                try:
                    cur.execute("SELECT COUNT(*) FROM pagos_influencers WHERE numero_oc=? AND estado='Pagada'",
                                (numero_oc,))
                    n_pagos_inf_pagados = cur.fetchone()[0] or 0
                except sqlite3.OperationalError:
                    n_pagos_inf_pagados = 0
                if n_pagos_oc == 0 and n_pagos_inf_pagados == 0:
                    puede_borrar_oc = True
            if puede_borrar_oc:
                # Borrar pagos_influencers pendientes asociados (no Pagados)
                try:
                    d = cur.execute(
                        "DELETE FROM pagos_influencers WHERE numero_oc=? AND COALESCE(estado,'') != 'Pagada'",
                        (numero_oc,)
                    )
                    pagos_inf_borrados = d.rowcount or 0
                except sqlite3.OperationalError:
                    pass
                try:
                    cur.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
                except sqlite3.OperationalError:
                    pass
                cur.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
                oc_borrada = True
    try:
        c.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
    except sqlite3.OperationalError:
        pass
    c.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
    conn.commit()
    return jsonify({
        'ok': True,
        'eliminada': numero.upper(),
        'oc_borrada': oc_borrada,
        'numero_oc': numero_oc or '',
        'pagos_influencers_borrados': pagos_inf_borrados,
    })

@bp.route('/api/ordenes-compra', methods=['GET','POST'])
def handle_ordenes_compra():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        usuario, err, code = _require_compras_write()
        if err:
            return err, code
        d = request.get_json(silent=True) or {}
        if not d.get('proveedor'): return jsonify({'error': 'Proveedor requerido'}), 400
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) FROM ordenes_compra WHERE numero_oc LIKE ?", (f"OC-{datetime.now().strftime('%Y')}-%",)); num = (c.fetchone()[0] or 0) + 1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        categoria = d.get('categoria', 'MP')
        c.execute("INSERT INTO ordenes_compra (numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est,categoria) VALUES (?,?,?,?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Borrador', d['proveedor'],
                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est',''), categoria))

        # ── FIX Catalina: auto-persistir proveedor en tabla proveedores
        # Antes el proveedor solo quedaba como string en ordenes_compra.proveedor.
        # Cuando creaba la siguiente OC tenia que volver a escribir todo.
        # Ahora si el proveedor no existe, se crea con datos basicos (Catalina
        # puede enriquecerlo despues en /compras → Proveedores). Si ya existe,
        # solo se hace upsert de campos no-vacios para no pisar datos buenos.
        try:
            existe = c.execute(
                "SELECT id FROM proveedores WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?)) AND activo=1",
                (d['proveedor'],)
            ).fetchone()
            if not existe:
                c.execute("""INSERT INTO proveedores
                             (nombre, categoria, condiciones_pago, activo, fecha_creacion)
                             VALUES (?,?,?,1,?)""",
                          (d['proveedor'], categoria, '30 dias',
                           datetime.now().isoformat()))
                try:
                    audit_log(c, usuario=usuario, accion='CREAR_PROVEEDOR',
                              tabla='proveedores', registro_id=c.lastrowid,
                              despues={'nombre': d['proveedor'][:200],
                                        'categoria': categoria,
                                        'origen': 'auto_oc',
                                        'oc_origen': numero_oc},
                              detalle=f"Auto-creado al crear OC {numero_oc} · {d['proveedor'][:80]}")
                except Exception:
                    pass
        except Exception:
            pass

        # ── FIX Catalina: persistir precios en precios_mp_historico
        # para que la proxima vez que cree OC con el mismo MP, el precio
        # aparezca como sugerencia en autocomplete.
        for it in (d.get('items') or []):
            cantidad_g = float(it.get('cantidad_g', 0))
            precio_u = float(it.get('precio_unitario', 0))
            subtotal = round(cantidad_g * precio_u, 2)
            codigo = it.get('codigo_mp', '')
            nombre = it.get('nombre_mp', '')
            c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero_oc, codigo, nombre, cantidad_g, precio_u, subtotal))
            # Persistir en historico de precios + actualizar referencia en maestro
            if codigo and precio_u > 0:
                try:
                    c.execute("""INSERT OR IGNORE INTO precios_mp_historico
                                 (codigo_mp, nombre_mp, precio_unitario, proveedor,
                                  fecha, numero_oc, cantidad_g)
                                 VALUES (?,?,?,?,?,?,?)""",
                              (codigo, nombre, precio_u, d['proveedor'],
                               datetime.now().isoformat()[:10], numero_oc, cantidad_g))
                except Exception:
                    pass
                try:
                    c.execute("""UPDATE maestro_mps
                                 SET precio_referencia=?, proveedor=COALESCE(NULLIF(proveedor,''),?)
                                 WHERE codigo_mp=?""",
                              (precio_u, d['proveedor'], codigo))
                except Exception:
                    pass

        valor_total_calc = sum(
            round((it.get('cantidad_g',0))*(it.get('precio_unitario',0)),2)
            for it in (d.get('items') or [])
        )
        if valor_total_calc > 0:
            c.execute("UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?", (valor_total_calc, numero_oc))
        try:
            audit_log(c, usuario=usuario, accion='CREAR_OC',
                      tabla='ordenes_compra', registro_id=numero_oc,
                      despues={'proveedor': d['proveedor'][:200],
                                'categoria': categoria,
                                'estado': 'Borrador',
                                'items_count': len(d.get('items') or []),
                                'valor_total': valor_total_calc,
                                'fecha_entrega_est': d.get('fecha_entrega_est','')[:30]},
                      detalle=f"Creó OC {numero_oc} · {d['proveedor']} · "
                              f"{len(d.get('items') or [])} items · total {valor_total_calc:.0f}")
        except Exception as e:
            log.warning('audit_log CREAR_OC fallo: %s', e)
        conn.commit()
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
    rows = c.fetchall()
    return jsonify({'ordenes': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/ordenes-compra/<numero_oc>', methods=['GET','PUT','DELETE'])
def handle_oc_detalle(numero_oc):
    conn = get_db(); c = conn.cursor()
    if request.method == 'DELETE':
        c.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
        _row = c.fetchone()
        if not _row:
            return jsonify({'error': 'OC no encontrada'}), 404
        if _row[0] not in ('Borrador', 'Rechazada'):
            return jsonify({'error': f'No se puede eliminar una OC en estado {_row[0]}. Solo Borrador o Rechazada.'}), 400
        c.execute('DELETE FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
        c.execute('DELETE FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
        conn.commit()
        return jsonify({'ok': True, 'message': f'OC {numero_oc} eliminada'})

    if request.method == 'PUT':
        u, err, code = _require_compras_write()
        if err:
            return err, code
        d = request.get_json(silent=True) or {}
        if d.get('estado'):
            c.execute("UPDATE ordenes_compra SET estado=? WHERE numero_oc=?",
                      (d['estado'], numero_oc))
        conn.commit()
        return jsonify({'message': f'OC {numero_oc} actualizada'})
    c.execute("SELECT * FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = c.fetchone()
    oc_cols = [d[0] for d in c.description] if c.description else []
    c.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items = [dict(row) for row in c.fetchall()]
    if not oc_row: return jsonify({'error': 'OC no encontrada'}), 404
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
    return jsonify({'oc': oc_dict, 'items': items, 'prov_data': prov_data})

@bp.route('/api/ordenes-compra/<numero_oc>/editar', methods=['PATCH'])
def editar_oc(numero_oc):
    """Edita una OC. Permisos por estado (decision Sebastian + Catalina 2026-04-28):

      - Borrador / Pendiente / Revisada / Aprobada / Autorizada:
          edicion COMPLETA (proveedor, categoria, observaciones, fechas, items)
      - Recibida / Parcial:
          solo observaciones + observaciones_recepcion + fecha_entrega_est
          (NO items, NO proveedor — la mercancia ya llego, no se cambia)
      - Pagada:
          solo observaciones (auditable)
      - Cancelada / Rechazada:
          bloqueado (la OC esta muerta)

    Esto resuelve la queja real de Catalina: una vez la OC pasaba de Borrador
    quedaba congelada y no podia ajustar ni el precio si el proveedor cambiaba
    despues.
    """
    # Audit zero-error 2-may-2026: RBAC mínimo (era cualquier sesión)
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(COMPRAS_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Compras/Admin pueden editar OC'}), 403
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT estado FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado = row[0] or 'Borrador'

    # Bloqueos absolutos
    if estado in ('Cancelada', 'Rechazada'):
        return jsonify({
            'error': f'OC en estado {estado} no se puede editar. '
                     f'Crea una nueva OC en su lugar.'
        }), 400

    d = request.json or {}
    EDITABLE_FULL = {'Borrador', 'Pendiente', 'Revisada', 'Aprobada', 'Autorizada'}
    EDITABLE_LIMITED = {'Recibida', 'Parcial'}
    EDITABLE_OBS_ONLY = {'Pagada'}

    # ─── Edicion completa ────────────────────────────────────────────────
    # PATCH semántico: solo se actualiza lo que VIENE en el body. Lo que no se
    # especifique mantiene su valor actual en BD. Esto permite PATCH parciales
    # (ej. solo togglear con_iva desde el Consolidado sin reenviar proveedor).
    if estado in EDITABLE_FULL:
        # Leer estado actual para fallback en campos no especificados
        cur_row = c.execute("""
            SELECT proveedor, COALESCE(categoria,'MP'), COALESCE(observaciones,''),
                   COALESCE(fecha_entrega_est,''), COALESCE(con_iva,0),
                   COALESCE(valor_sin_iva,0)
            FROM ordenes_compra WHERE numero_oc=?
        """, (numero_oc,)).fetchone()
        cur_prov, cur_cat, cur_obs, cur_fent, cur_iva, cur_vsi = cur_row
        proveedor = d['proveedor'] if 'proveedor' in d and d.get('proveedor') else cur_prov
        if not proveedor:
            return jsonify({'error': 'Proveedor requerido (no hay valor actual y no vino en body)'}), 400
        categoria = d.get('categoria', cur_cat)
        observaciones = d.get('observaciones', cur_obs) if 'observaciones' in d else cur_obs
        fecha_entrega_est = d.get('fecha_entrega_est', cur_fent) if 'fecha_entrega_est' in d else cur_fent
        con_iva = (1 if d.get('con_iva') else 0) if 'con_iva' in d else int(cur_iva or 0)
        valor_sin_iva = float(d.get('valor_sin_iva', cur_vsi)) if 'valor_sin_iva' in d else float(cur_vsi or 0)
        c.execute("""
            UPDATE ordenes_compra SET
                proveedor=?, categoria=?, observaciones=?,
                fecha_entrega_est=?, con_iva=?, valor_sin_iva=?
            WHERE numero_oc=?""",
            (proveedor, categoria, observaciones,
             fecha_entrega_est, con_iva, valor_sin_iva, numero_oc))
        # Si vinieron items, reemplazar completo y recalcular valor_total con IVA
        if 'items' in d:
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
        else:
            # Sin items en body → recalcular valor_total respetando con_iva sobre items existentes
            # (importante cuando solo se togglea IVA sin tocar items)
            sub = c.execute(
                'SELECT COALESCE(SUM(subtotal),0) FROM ordenes_compra_items WHERE numero_oc=?',
                (numero_oc,)
            ).fetchone()[0] or 0.0
            valor_total = round(sub * 1.19, 2) if con_iva else round(sub, 2)
            c.execute('UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?', (valor_total, numero_oc))
        try:
            audit_log(c, usuario=user, accion='EDITAR_OC',
                      tabla='ordenes_compra', registro_id=numero_oc,
                      antes={'proveedor': cur_prov, 'categoria': cur_cat,
                              'con_iva': cur_iva, 'valor_sin_iva': cur_vsi},
                      despues={k: d.get(k) for k in d
                                if k in ('proveedor','categoria','observaciones',
                                         'fecha_entrega_est','con_iva','valor_sin_iva',
                                         'items')},
                      detalle=f"Editó OC {numero_oc} ({estado})")
        except Exception as e:
            log.warning('audit_log EDITAR_OC fallo: %s', e)
        conn.commit()
        return jsonify({'ok': True, 'message': f'OC {numero_oc} ({estado}) actualizada'})

    # ─── Edicion limitada (Recibida/Parcial): solo metadata sin tocar mercancia ─
    if estado in EDITABLE_LIMITED:
        sets, params = [], []
        for f in ('observaciones', 'observaciones_recepcion', 'fecha_entrega_est'):
            if f in d:
                sets.append(f'{f}=?'); params.append(d[f])
        if not sets:
            return jsonify({'error': f'En estado {estado} solo se puede editar observaciones / fecha_entrega_est'}), 400
        params.append(numero_oc)
        c.execute(f'UPDATE ordenes_compra SET {", ".join(sets)} WHERE numero_oc=?', params)
        try:
            audit_log(c, usuario=user, accion='EDITAR_OC',
                      tabla='ordenes_compra', registro_id=numero_oc,
                      despues={k: d.get(k) for k in d
                                if k in ('observaciones','observaciones_recepcion','fecha_entrega_est')},
                      detalle=f"Editó OC {numero_oc} ({estado}) — campos limitados")
        except Exception as e:
            log.warning('audit_log EDITAR_OC fallo: %s', e)
        conn.commit()
        return jsonify({'ok': True, 'message': f'OC {numero_oc} ({estado}) — campos limitados actualizados',
                        'campos_actualizados': [s.split('=')[0] for s in sets]})

    # ─── Edicion mínima (Pagada): solo observaciones para audit trail ─────
    if estado in EDITABLE_OBS_ONLY:
        if 'observaciones' not in d:
            return jsonify({'error': 'En estado Pagada solo se permite editar observaciones'}), 400
        # Append en lugar de sobreescribir (audit trail)
        nueva_obs = (d.get('observaciones') or '').strip()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        usuario = session.get('compras_user', '')
        nota = f'\n[{ts} {usuario}] {nueva_obs}'
        c.execute("""UPDATE ordenes_compra
                     SET observaciones = COALESCE(observaciones,'') || ?
                     WHERE numero_oc=?""", (nota, numero_oc))
        conn.commit()
        return jsonify({'ok': True, 'message': f'Nota agregada al historial de OC {numero_oc}'})

    return jsonify({'error': f'Estado {estado} no soportado para edicion'}), 400


@bp.route('/api/ordenes-compra/<numero_oc>/items', methods=['POST'])
def agregar_item_oc(numero_oc):
    """Agrega un item a una OC existente sin tener que recrearla.

    Body: {codigo_mp, nombre_mp, cantidad_g, precio_unitario}

    Permitido en estados: Borrador, Pendiente, Revisada, Aprobada, Autorizada.
    Bloqueado en Recibida/Pagada/Cancelada/Rechazada.
    """
    # Audit zero-error 2-may-2026: RBAC mínimo
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(COMPRAS_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Compras/Admin pueden agregar items'}), 403
    conn = get_db(); c = conn.cursor()
    row = c.execute('SELECT estado, con_iva FROM ordenes_compra WHERE numero_oc=?',
                    (numero_oc,)).fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado, con_iva = row[0], row[1]
    if estado not in ('Borrador', 'Pendiente', 'Revisada', 'Aprobada', 'Autorizada'):
        return jsonify({'error': f'No se pueden agregar items en estado {estado}'}), 400
    d = request.json or {}
    nombre_mp = (d.get('nombre_mp') or '').strip()
    if not nombre_mp:
        return jsonify({'error': 'nombre_mp requerido'}), 400
    if len(nombre_mp) > 300:
        return jsonify({'error': 'nombre_mp excede 300 chars'}), 400
    # Audit zero-error 2-may-2026: usar validate_money para sanity check completo
    # (NaN/Infinity/cap). Antes solo se validaba >0 y <1B gramos.
    cantidad_g, err = validate_money(d.get('cantidad_g', 0), allow_zero=False,
                                       max_value=1_000_000_000, field_name='cantidad_g')
    if err:
        return jsonify(err), 400
    precio, err = validate_money(d.get('precio_unitario', 0), allow_zero=True,
                                   field_name='precio_unitario')
    if err:
        return jsonify(err), 400
    subtotal = round(cantidad_g * precio, 2)
    c.execute("""INSERT INTO ordenes_compra_items
                 (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
                 VALUES (?,?,?,?,?,?)""",
              (numero_oc, d.get('codigo_mp', ''), nombre_mp, cantidad_g, precio, subtotal))
    item_id = c.lastrowid
    # Recalcular total OC
    suma = c.execute("SELECT COALESCE(SUM(subtotal),0) FROM ordenes_compra_items WHERE numero_oc=?",
                     (numero_oc,)).fetchone()[0]
    if con_iva:
        suma = round(suma * 1.19, 2)
    c.execute('UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?', (suma, numero_oc))
    try:
        audit_log(c, usuario=user, accion='AGREGAR_ITEM_OC',
                  tabla='ordenes_compra_items', registro_id=numero_oc,
                  despues={'item_id': item_id, 'codigo_mp': d.get('codigo_mp',''),
                            'nombre_mp': nombre_mp[:200], 'cantidad_g': cantidad_g,
                            'precio_unitario': precio, 'subtotal': subtotal,
                            'estado_oc': estado},
                  detalle=f"Agregó item {nombre_mp[:60]} a OC {numero_oc} · "
                          f"{cantidad_g}g @ {precio:.0f}")
    except Exception as e:
        log.warning('audit_log AGREGAR_ITEM_OC fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'item_id': item_id, 'valor_total': suma})


@bp.route('/api/ordenes-compra/<numero_oc>/items/<int:item_id>', methods=['PATCH', 'DELETE'])
def modificar_item_oc(numero_oc, item_id):
    """PATCH: actualiza precio/cantidad/nombre de un item.
    DELETE: elimina un item.

    Estados permitidos: Borrador, Pendiente, Revisada, Aprobada, Autorizada.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    row = c.execute('SELECT estado, con_iva FROM ordenes_compra WHERE numero_oc=?',
                    (numero_oc,)).fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado, con_iva = row[0], row[1]
    if estado not in ('Borrador', 'Pendiente', 'Revisada', 'Aprobada', 'Autorizada'):
        return jsonify({'error': f'No se pueden modificar items en estado {estado}'}), 400

    if request.method == 'DELETE':
        c.execute('DELETE FROM ordenes_compra_items WHERE id=? AND numero_oc=?',
                  (item_id, numero_oc))
        if c.rowcount == 0:
            return jsonify({'error': 'Item no encontrado'}), 404
    else:
        d = request.json or {}
        sets, params = [], []
        if 'codigo_mp' in d:
            sets.append('codigo_mp=?'); params.append(d['codigo_mp'])
        if 'nombre_mp' in d:
            sets.append('nombre_mp=?'); params.append(d['nombre_mp'])
        if 'cantidad_g' in d or 'precio_unitario' in d:
            # Recalcular subtotal con valores actualizados
            cur_row = c.execute("""SELECT cantidad_g, precio_unitario
                                   FROM ordenes_compra_items
                                   WHERE id=? AND numero_oc=?""",
                                (item_id, numero_oc)).fetchone()
            if not cur_row:
                return jsonify({'error': 'Item no encontrado'}), 404
            cant = float(d.get('cantidad_g', cur_row[0] or 0))
            prec = float(d.get('precio_unitario', cur_row[1] or 0))
            sets += ['cantidad_g=?', 'precio_unitario=?', 'subtotal=?']
            params += [cant, prec, round(cant * prec, 2)]
        if not sets:
            return jsonify({'error': 'Nada que actualizar'}), 400
        params += [item_id, numero_oc]
        c.execute(f"""UPDATE ordenes_compra_items SET {', '.join(sets)}
                      WHERE id=? AND numero_oc=?""", params)

    # Recalcular total OC
    suma = c.execute("SELECT COALESCE(SUM(subtotal),0) FROM ordenes_compra_items WHERE numero_oc=?",
                     (numero_oc,)).fetchone()[0]
    if con_iva:
        suma = round(suma * 1.19, 2)
    c.execute('UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?', (suma, numero_oc))
    try:
        usuario_act = session.get('compras_user', '')
        accion_audit = 'ELIMINAR_ITEM_OC' if request.method == 'DELETE' else 'MODIFICAR_ITEM_OC'
        audit_log(c, usuario=usuario_act, accion=accion_audit,
                  tabla='ordenes_compra_items', registro_id=numero_oc,
                  despues={'item_id': item_id,
                            'valor_total_nuevo': suma,
                            'estado_oc': estado},
                  detalle=f"{accion_audit.replace('_',' ').title()} item {item_id} en OC {numero_oc}")
    except Exception as e:
        log.warning('audit_log MODIFICAR_ITEM_OC fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'valor_total': suma})

@bp.route('/api/ordenes-compra/<numero_oc>/proveedor', methods=['PATCH'])
def confirmar_proveedor_oc(numero_oc):
    """Confirma o cambia el proveedor de una OC.

    Body: { proveedor: 'Nombre Proveedor', confirmado: true }

    Pensado para el flujo donde Catalina revisa la solicitud pendiente y:
      - Si el proveedor sugerido es correcto → confirma con click (proveedor
        sigue igual, solo actualiza fecha y marca confirmacion).
      - Si quiere cambiarlo → escribe el nuevo nombre y se actualiza.

    NO requiere estado Borrador — confirmacion también es válida en
    Aprobada (siempre que no haya pagos hechos).

    Cuando se confirma o cambia, alimentamos el catálogo: si el proveedor
    es nuevo y no existe en `proveedores`, se crea con datos mínimos para
    que aparezca en futuros selectores. Esto es lo que el user pidió:
    'sirve para confirmar y que el sistema se alimente'.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    nuevo_prov = (d.get('proveedor') or '').strip()
    if not nuevo_prov:
        return jsonify({'error': 'proveedor requerido'}), 400

    conn = get_db(); c = conn.cursor()
    row = c.execute(
        'SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?',
        (numero_oc,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado_oc, proveedor_actual, categoria = row[0], (row[1] or ''), (row[2] or 'MP')

    # No permitir cambio si ya hay pagos (audit trail)
    try:
        n_pagos = c.execute(
            'SELECT COUNT(*) FROM pagos_oc WHERE numero_oc=?', (numero_oc,)
        ).fetchone()[0] or 0
        if n_pagos > 0 and proveedor_actual.lower() != nuevo_prov.lower():
            return jsonify({
                'error': 'No se puede cambiar proveedor de una OC con pagos registrados',
                'codigo': 'OC_CON_PAGOS'
            }), 400
    except Exception:
        pass

    # Si el proveedor no existe en catálogo, crearlo (alimenta sistema)
    creado_nuevo = False
    try:
        existe = c.execute(
            'SELECT 1 FROM proveedores WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?))',
            (nuevo_prov,)
        ).fetchone()
        if not existe:
            c.execute(
                """INSERT INTO proveedores (nombre, categoria, fecha_creacion)
                   VALUES (?, ?, ?)""",
                (nuevo_prov, categoria, datetime.now().isoformat())
            )
            creado_nuevo = True
            try:
                audit_log(c, usuario=session.get('compras_user', 'sistema'),
                          accion='CREAR_PROVEEDOR', tabla='proveedores',
                          registro_id=c.lastrowid,
                          despues={'nombre': nuevo_prov[:200],
                                    'categoria': categoria,
                                    'origen': 'auto_cambio_proveedor_oc',
                                    'oc': numero_oc},
                          detalle=f"Auto-creado al cambiar proveedor de OC {numero_oc}")
            except Exception:
                pass
    except sqlite3.OperationalError:
        pass

    # Actualizar la OC
    c.execute(
        'UPDATE ordenes_compra SET proveedor=? WHERE numero_oc=?',
        (nuevo_prov, numero_oc)
    )
    try:
        usuario_act = session.get('compras_user', '')
        cambio = proveedor_actual.lower() != nuevo_prov.lower()
        audit_log(c, usuario=usuario_act, accion='CONFIRMAR_PROVEEDOR_OC',
                  tabla='ordenes_compra', registro_id=numero_oc,
                  antes={'proveedor': proveedor_actual},
                  despues={'proveedor': nuevo_prov, 'creado_catalogo': creado_nuevo,
                            'cambio': cambio},
                  detalle=f"{'Cambió' if cambio else 'Confirmó'} proveedor OC {numero_oc} "
                          f"de '{proveedor_actual}' a '{nuevo_prov}'")
    except Exception as e:
        log.warning('audit_log CONFIRMAR_PROVEEDOR_OC fallo: %s', e)
    conn.commit()
    return jsonify({
        'ok': True,
        'numero_oc': numero_oc,
        'proveedor_anterior': proveedor_actual,
        'proveedor_nuevo': nuevo_prov,
        'creado_en_catalogo': creado_nuevo,
        'cambio': proveedor_actual.lower() != nuevo_prov.lower(),
    })


@bp.route('/api/ordenes-compra/<numero_oc>/items-precios', methods=['PATCH'])
def actualizar_precios_items_oc(numero_oc):
    """Actualiza precios unitarios de items de una OC + alimenta histórico.

    Body: { items: [{ codigo_mp, precio_unitario, cantidad_g? }, ...] }

    Para que Catalina (en el flujo de confirmar solicitud) cargue precios
    por item — esto:
      1. Actualiza precio_unitario y subtotal en ordenes_compra_items
      2. Alimenta precios_mp_historico para que aparezca en próximos
         pedidos como precio sugerido
      3. Recalcula valor_total de la OC

    El user pidió: 'que catalina coloque el valor de cada cosa y guardar
    asi empezamos a tener almacenado los valores de las cosas para que
    sea mas automatico'.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    items_in = d.get('items') or []
    if not items_in:
        return jsonify({'error': 'items requerido'}), 400

    conn = get_db(); c = conn.cursor()
    row = c.execute(
        'SELECT estado, proveedor FROM ordenes_compra WHERE numero_oc=?', (numero_oc,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    proveedor = row[1] or ''

    # Actualizar cada item por codigo_mp (y opcionalmente cantidad_g)
    actualizados = 0
    for it in items_in:
        cod = (it.get('codigo_mp') or '').strip()
        if not cod:
            continue
        precio = float(it.get('precio_unitario', 0) or 0)
        # Cantidad: si la pasan, la actualizamos; si no, la dejamos como está
        cant = it.get('cantidad_g')
        if cant is not None:
            try:
                cant = float(cant)
                # subtotal = cantidad * precio
                subtotal = round(cant * precio, 2)
                c.execute(
                    """UPDATE ordenes_compra_items
                       SET precio_unitario=?, cantidad_g=?, subtotal=?
                       WHERE numero_oc=? AND codigo_mp=?""",
                    (precio, cant, subtotal, numero_oc, cod)
                )
            except (ValueError, TypeError):
                continue
        else:
            # Solo precio: recalcula subtotal con la cantidad existente
            c.execute(
                """UPDATE ordenes_compra_items
                   SET precio_unitario=?,
                       subtotal=ROUND(COALESCE(cantidad_g,0)*?, 2)
                   WHERE numero_oc=? AND codigo_mp=?""",
                (precio, precio, numero_oc, cod)
            )
        actualizados += 1

        # Alimentar histórico de precios (si la tabla existe)
        if precio > 0:
            try:
                c.execute(
                    """INSERT OR IGNORE INTO precios_mp_historico
                       (codigo_mp, precio_kg, proveedor, fecha)
                       VALUES (?, ?, ?, datetime('now'))""",
                    (cod, precio, proveedor)
                )
            except sqlite3.OperationalError:
                pass

    # Recalcular valor_total de la OC
    total = c.execute(
        'SELECT COALESCE(SUM(COALESCE(subtotal,0)),0) FROM ordenes_compra_items WHERE numero_oc=?',
        (numero_oc,)
    ).fetchone()[0] or 0
    c.execute(
        'UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?',
        (round(float(total), 2), numero_oc)
    )
    try:
        usuario_act = session.get('compras_user', '')
        audit_log(c, usuario=usuario_act, accion='ACTUALIZAR_PRECIOS_OC',
                  tabla='ordenes_compra_items', registro_id=numero_oc,
                  despues={'items_actualizados': actualizados,
                            'valor_total_nuevo': round(float(total), 2),
                            'proveedor': proveedor[:200]},
                  detalle=f"Actualizó precios de {actualizados} items en OC {numero_oc} "
                          f"· nuevo total {float(total):.0f}")
    except Exception as e:
        log.warning('audit_log ACTUALIZAR_PRECIOS_OC fallo: %s', e)
    conn.commit()
    return jsonify({
        'ok': True,
        'numero_oc': numero_oc,
        'items_actualizados': actualizados,
        'valor_total_nuevo': round(float(total), 2),
    })


@bp.route('/api/compras/sugerir-mp/<path:codigo_mp>')
def sugerir_mp(codigo_mp):
    """Devuelve datos sugeridos para autocompletar un MP en una OC.
    Resuelve la queja de Catalina: 'pongo precios y proveedor y no quedan
    guardados — siempre me los vuelve a pedir'.

    Devuelve:
      - nombre_mp (de maestro_mps)
      - precio_referencia (ultimo precio en maestro_mps)
      - precio_ultimo (de precios_mp_historico, mas reciente)
      - proveedor_ultimo (de precios_mp_historico, mas reciente)
      - top_proveedores: lista de proveedores que han vendido este MP
        ordenados por uso (top 5) con su precio promedio
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    out = {'codigo_mp': codigo_mp}
    try:
        mp = c.execute("""SELECT nombre_inci, nombre_comercial, proveedor,
                                COALESCE(precio_referencia,0)
                         FROM maestro_mps WHERE codigo_mp=?""", (codigo_mp,)).fetchone()
        if mp:
            out['nombre_inci'] = mp[0]
            out['nombre_comercial'] = mp[1]
            out['proveedor_default'] = mp[2]
            out['precio_referencia'] = mp[3]
    except Exception:
        pass

    try:
        # Ultimo precio en historial
        ult = c.execute("""SELECT precio_unitario, proveedor, fecha, numero_oc
                          FROM precios_mp_historico
                          WHERE codigo_mp=?
                          ORDER BY fecha DESC, id DESC LIMIT 1""",
                       (codigo_mp,)).fetchone()
        if ult:
            out['precio_ultimo'] = ult[0]
            out['proveedor_ultimo'] = ult[1]
            out['fecha_ultimo'] = ult[2]
            out['oc_ultima'] = ult[3]
    except Exception:
        pass

    try:
        # Top proveedores por uso historico (ultimas 50 compras del MP)
        rows = c.execute("""
            SELECT proveedor, COUNT(*) as veces, AVG(precio_unitario) as precio_avg
            FROM precios_mp_historico
            WHERE codigo_mp=? AND COALESCE(proveedor,'') != ''
            GROUP BY proveedor
            ORDER BY veces DESC, precio_avg ASC
            LIMIT 5
        """, (codigo_mp,)).fetchall()
        out['top_proveedores'] = [
            {'proveedor': r[0], 'veces_usado': r[1], 'precio_promedio': round(r[2] or 0, 2)}
            for r in rows
        ]
    except Exception:
        out['top_proveedores'] = []

    return jsonify(out)


@bp.route('/api/proveedores-compras', methods=['GET','POST'])
def handle_proveedores_compras():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        u = session.get('compras_user', '')
        d = request.get_json(silent=True) or {}
        nombre = (d.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'Nombre requerido'}), 400
        # Detectar duplicado exacto (case + trim) · Catalina 4-may-2026
        existe = c.execute(
            "SELECT id, nombre FROM proveedores WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?)) AND activo=1",
            (nombre,)
        ).fetchone()
        if existe:
            return jsonify({
                'error': f'Ya existe proveedor "{existe[1]}" (case-insensitive). Selecciona del dropdown.',
                'existente': {'id': existe[0], 'nombre': existe[1]},
            }), 409
        try:
            c.execute("""INSERT INTO proveedores
                (nombre,contacto,email,telefono,categoria,condiciones_pago,
                 nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (nombre,d.get('contacto',''),d.get('email',''),d.get('telefono',''),
                 d.get('categoria',''),d.get('condiciones_pago','30 dias'),
                 d.get('nit',''),d.get('direccion',''),d.get('num_cuenta',''),
                 d.get('tipo_cuenta',''),d.get('banco',''),d.get('concepto_compra',d.get('concepto','')),
                 datetime.now().isoformat()))
            new_id = c.lastrowid
            try:
                audit_log(c, usuario=u, accion='CREAR_PROVEEDOR',
                          tabla='proveedores', registro_id=new_id,
                          despues={'nombre': nombre[:200],
                                    'nit': (d.get('nit','') or '')[:50],
                                    'banco': (d.get('banco','') or '')[:80],
                                    'condiciones_pago': d.get('condiciones_pago','30 dias')[:50]},
                          detalle=f"Creó proveedor '{nombre[:80]}'")
            except Exception:
                pass
            conn.commit()
            return jsonify({'ok': True, 'message': f"Proveedor '{nombre}' creado",
                             'id': new_id, 'nombre': nombre}), 201
        except Exception as e: return jsonify({'error': str(e)}), 400
    c.execute("""SELECT nombre,contacto,email,telefono,categoria,condiciones_pago,
                       nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra
                FROM proveedores WHERE activo=1 ORDER BY nombre""")
    cols = ['nombre','contacto','email','telefono','categoria','condiciones_pago',
            'nit','direccion','num_cuenta','tipo_cuenta','banco','concepto_compra']
    provs = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'proveedores': provs})

@bp.route('/api/proveedores-compras/<path:nombre>', methods=['PATCH','DELETE'])
def handle_proveedor(nombre):
    conn = get_db(); c = conn.cursor()
    if request.method == 'DELETE':
        d = request.json or {}
        motivo = (d.get('motivo') or '').strip()
        if not motivo:
            return jsonify({'error': 'El motivo de baja es requerido'}), 400
        c.execute("SELECT id FROM proveedores WHERE nombre=? AND activo=1", (nombre,))
        if not c.fetchone():
            return jsonify({'error': 'Proveedor no encontrado'}), 404
        c.execute(
            "UPDATE proveedores SET activo=0, motivo_baja=?, fecha_baja=? WHERE nombre=?",
            (motivo, datetime.now().isoformat(), nombre)
        )
        conn.commit()
        return jsonify({'ok': True, 'message': f"Proveedor '{nombre}' dado de baja"})
    # PATCH — edit
    d = request.json or {}
    fields = ['contacto','email','telefono','nit','direccion',
              'banco','tipo_cuenta','num_cuenta','concepto_compra',
              'condiciones_pago','categoria']

    # Renombrar proveedor con propagacion automatica a OCs/historico.
    # Antes Catalina debia darlo de baja y crear uno nuevo, perdiendo
    # historial. Ahora si viene 'nombre' nuevo distinto al actual,
    # se actualiza en proveedores + en TODAS las tablas que lo referencian
    # por nombre (ordenes_compra, solicitudes_compra, precios_mp_historico,
    # cotizaciones, pedidos como cliente cuando aplique).
    nuevo_nombre = (d.get('nombre') or '').strip()
    rename_propagado = {}
    if nuevo_nombre and nuevo_nombre != nombre:
        # Verificar que no exista ya un proveedor activo con ese nombre
        existe = c.execute(
            "SELECT 1 FROM proveedores WHERE nombre=? AND activo=1",
            (nuevo_nombre,)
        ).fetchone()
        if existe:
            return jsonify({
                'error': f"Ya existe otro proveedor activo con el nombre '{nuevo_nombre}'"
            }), 409
        # Hacer el rename en transaccion
        c.execute("UPDATE proveedores SET nombre=? WHERE nombre=? AND activo=1",
                  (nuevo_nombre, nombre))
        if c.rowcount == 0:
            return jsonify({'error': 'Proveedor no encontrado'}), 404
        # Propagar a tablas referentes
        propagar = [
            ('ordenes_compra',     'proveedor'),
            ('solicitudes_compra', 'proveedor_sugerido'),
            ('precios_mp_historico', 'proveedor'),
        ]
        for tabla, col in propagar:
            try:
                c.execute(f"UPDATE {tabla} SET {col}=? WHERE {col}=?",
                          (nuevo_nombre, nombre))
                rename_propagado[tabla] = c.rowcount
            except Exception:
                pass
        # cotizaciones (3 columnas de proveedor)
        try:
            for col in ('proveedor_a', 'proveedor_b', 'proveedor_c'):
                c.execute(f"UPDATE cotizaciones SET {col}=? WHERE {col}=?",
                          (nuevo_nombre, nombre))
            rename_propagado['cotizaciones'] = 'OK'
        except Exception:
            pass
        # Despues del rename, las queries deben usar el nuevo nombre
        nombre = nuevo_nombre

    sets = [f"{f}=?" for f in fields if f in d]
    vals = [d[f] for f in fields if f in d]
    if not sets and not rename_propagado:
        return jsonify({'error': 'No hay campos para actualizar'}), 400

    if sets:
        vals.append(nombre)
        c.execute(f"UPDATE proveedores SET {', '.join(sets)} WHERE nombre=? AND activo=1", vals)
        if c.rowcount == 0:
            return jsonify({'error': 'Proveedor no encontrado'}), 404
    conn.commit()
    msg = f"Proveedor actualizado"
    if rename_propagado:
        msg += f" — nombre cambiado a '{nuevo_nombre}', propagado en: {rename_propagado}"
    return jsonify({'ok': True, 'message': msg, 'rename_propagado': rename_propagado,
                    'nombre_actual': nombre})

@bp.route('/api/proveedores-compras/<path:nombre>/ficha')
def proveedor_ficha_360(nombre):
    """Proveedor 360: datos completos + historial OCs + scoring."""
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, nombre, contacto, email, telefono, categoria,
                        nit, direccion, num_cuenta, tipo_cuenta, banco, concepto_compra,
                        id_interno, estado_lpa, ultima_evaluacion, vencimiento_docs,
                        acuerdo_calidad, condiciones_pago
                 FROM proveedores WHERE nombre=? AND activo=1""", (nombre,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Proveedor no encontrado'}), 404
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
    if request.method == 'POST':
        conn = None
        try:
            conn = get_db(); c = conn.cursor()
            d = request.json or {}
            c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM solicitudes_compra WHERE numero LIKE ?", (f"SOL-{datetime.now().strftime('%Y')}-%",)); num = (c.fetchone()[0] or 0) + 1
            numero = f"SOL-{datetime.now().strftime('%Y')}-{num:04d}"
            emp = d.get('empresa','Espagiria')
            cat = d.get('categoria','Materia Prima')
            tip = d.get('tipo','Compra')
            area = d.get('area','Produccion')
            email_sol = d.get('email_solicitante', '').strip().lower()
            fecha_req = d.get('fecha_requerida', '').strip()
            val_sol = float(d.get('valor') or 0)
            c.execute("""INSERT INTO solicitudes_compra
                         (numero,fecha,estado,solicitante,urgencia,observaciones,area,empresa,categoria,tipo,email_solicitante,fecha_requerida,valor)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (numero, datetime.now().isoformat(), 'Pendiente',
                       d.get('solicitante',''), d.get('urgencia','Normal'), d.get('observaciones',''),
                       area, emp, cat, tip, email_sol, fecha_req, val_sol))
            for it in (d.get('items') or []):
                # proveedor_sugerido es opcional. Migración 19xx aseguró que la
                # columna exista. Si por alguna razón no, fallback al INSERT
                # mínimo. Solicitudes generadas desde Plan MP rolling envían
                # proveedor_sugerido tomado de mp_lead_time_config.
                try:
                    c.execute("""INSERT INTO solicitudes_compra_items
                                 (numero,codigo_mp,nombre_mp,cantidad_g,unidad,justificacion,valor_estimado,proveedor_sugerido)
                                 VALUES (?,?,?,?,?,?,?,?)""",
                              (numero, it.get('codigo_mp',''), it.get('nombre_mp',''),
                               it.get('cantidad_g',0), it.get('unidad','g'),
                               it.get('justificacion',''), it.get('valor_estimado',0),
                               it.get('proveedor_sugerido','')))
                except sqlite3.OperationalError:
                    # Esquema antiguo sin proveedor_sugerido — fallback
                    c.execute("""INSERT INTO solicitudes_compra_items
                                 (numero,codigo_mp,nombre_mp,cantidad_g,unidad,justificacion,valor_estimado)
                                 VALUES (?,?,?,?,?,?,?)""",
                              (numero, it.get('codigo_mp',''), it.get('nombre_mp',''),
                               it.get('cantidad_g',0), it.get('unidad','g'),
                               it.get('justificacion',''), it.get('valor_estimado',0)))
            try:
                usuario_act = session.get('compras_user', '') or d.get('solicitante','')
                audit_log(c, usuario=usuario_act, accion='CREAR_SOLICITUD',
                          tabla='solicitudes_compra', registro_id=numero,
                          despues={'empresa': emp, 'categoria': cat, 'tipo': tip,
                                    'area': area,
                                    'solicitante': d.get('solicitante','')[:100],
                                    'urgencia': d.get('urgencia','Normal'),
                                    'valor': val_sol,
                                    'items_count': len(d.get('items') or [])},
                          detalle=f"Creó solicitud {numero} · {emp} · {cat} · "
                                  f"{len(d.get('items') or [])} items · valor {val_sol:.0f}")
            except Exception as e:
                log.warning('audit_log CREAR_SOLICITUD fallo: %s', e)
            conn.commit()
            return jsonify({'message': f'Solicitud {numero} creada', 'numero': numero}), 201
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    # Rollback puede fallar si no había transacción abierta —
                    # no es crítico, ya estamos en error path.
                    pass
            import traceback as _tb
            return jsonify({'error': str(e), 'detail': _tb.format_exc()[-500:]}), 500
    conn = get_db(); c = conn.cursor()
    # GET: listar todas las solicitudes
    filtro_estado = request.args.get('estado', '')
    filtro_empresa = request.args.get('empresa', '')
    # SELECT con LEFT JOIN a marketing_influencers para enriquecer con datos
    # bancarios. Las columnas ciudad/instagram las garantiza la migración 31.
    # Si por alguna razón no existen (esquema pre-migración 31), caemos al
    # SELECT sin esas columnas en el except más abajo.
    sql_with_extras = """
        SELECT sc.numero, sc.fecha, sc.estado, sc.solicitante, sc.urgencia,
               sc.observaciones, sc.empresa, sc.categoria, sc.tipo, sc.area,
               sc.email_solicitante, sc.fecha_requerida, sc.numero_oc,
               COALESCE(NULLIF(oc.valor_total,0), sc.valor, 0) as valor_oc,
               COALESCE(mi.nombre, '')           as inf_nombre,
               COALESCE(mi.banco, '')            as inf_banco,
               COALESCE(mi.cuenta_bancaria, '')  as inf_cuenta,
               COALESCE(mi.tipo_cuenta, '')      as inf_tipo_cuenta,
               COALESCE(mi.cedula_nit, '')       as inf_cedula,
               COALESCE(mi.email, '')            as inf_email,
               COALESCE(mi.ciudad, '')           as inf_ciudad,
               COALESCE(mi.instagram, '')        as inf_instagram
        FROM solicitudes_compra sc
        LEFT JOIN ordenes_compra oc ON oc.numero_oc = sc.numero_oc
        LEFT JOIN marketing_influencers mi ON mi.id = sc.influencer_id
        WHERE 1=1"""
    sql_minimal = """
        SELECT sc.numero, sc.fecha, sc.estado, sc.solicitante, sc.urgencia,
               sc.observaciones, sc.empresa, sc.categoria, sc.tipo, sc.area,
               sc.email_solicitante, sc.fecha_requerida, sc.numero_oc,
               COALESCE(NULLIF(oc.valor_total,0), sc.valor, 0) as valor_oc,
               COALESCE(mi.nombre, '')           as inf_nombre,
               COALESCE(mi.banco, '')            as inf_banco,
               COALESCE(mi.cuenta_bancaria, '')  as inf_cuenta,
               COALESCE(mi.tipo_cuenta, '')      as inf_tipo_cuenta,
               COALESCE(mi.cedula_nit, '')       as inf_cedula,
               COALESCE(mi.email, '')            as inf_email,
               '' as inf_ciudad,
               '' as inf_instagram
        FROM solicitudes_compra sc
        LEFT JOIN ordenes_compra oc ON oc.numero_oc = sc.numero_oc
        LEFT JOIN marketing_influencers mi ON mi.id = sc.influencer_id
        WHERE 1=1"""
    sql = sql_with_extras
    params = []
    if filtro_estado: sql += " AND sc.estado=?"; params.append(filtro_estado)
    if filtro_empresa: sql += " AND sc.empresa=?"; params.append(filtro_empresa)
    filtro_categoria = request.args.get('categoria', '')
    # Sebastian (29-abr-2026): cuando se pide 'Influencer/Marketing Digital'
    # tambien incluir 'Cuenta de Cobro' — el tab Influencers de /compras
    # gestiona ambas porque tienen el mismo flujo (pago directo a personas).
    # Antes solo traia una categoria y SOLs de 'Cuenta de Cobro' quedaban
    # invisibles aunque /admin/influencers-hoy SI las mostraba.
    if filtro_categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro'):
        sql += " AND sc.categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
    elif filtro_categoria:
        sql += " AND sc.categoria=?"; params.append(filtro_categoria)
    else:
        sql += " AND sc.categoria NOT IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
    if filtro_categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro'):
        # Cadena de prioridad para ordenar:
        #  1. pi.fecha_publicacion (fecha del contenido cuando se agendó en marketing)
        #  2. sc.fecha_requerida   (fecha tope cuando el pago debe hacerse)
        #  3. sc.fecha             (fecha en que se creó la solicitud)
        # Estado: Aprobadas (por pagar) primero, luego el resto.
        # Más antiguas arriba (urgentes primero).
        sql = sql.replace(
            "FROM solicitudes_compra sc",
            "FROM solicitudes_compra sc LEFT JOIN pagos_influencers pi ON pi.numero_oc = sc.numero_oc"
        )
        sql += (
            " ORDER BY "
            " CASE sc.estado WHEN 'Aprobada' THEN 0 WHEN 'Pendiente' THEN 1 "
            "                WHEN 'Pagada' THEN 2 ELSE 3 END, "
            " COALESCE(NULLIF(pi.fecha_publicacion,''), "
            "          NULLIF(sc.fecha_requerida,''), "
            "          sc.fecha) ASC, "
            " sc.numero ASC LIMIT 300"
        )
    else:
        sql += " ORDER BY sc.fecha DESC LIMIT 200"
    try:
        c.execute(sql, params)
    except sqlite3.OperationalError as _e:
        # Fallback: si las columnas ciudad/instagram no existen aún (DB sin
        # migración 31 aplicada), usar versión minimal del SELECT.
        if 'no such column' in str(_e).lower() and sql.startswith(sql_with_extras.split('WHERE')[0][:50]):
            # Reaplicar reemplazos de la rama Influencer si correspondía
            sql_fb = sql_minimal
            if filtro_categoria == 'Influencer/Marketing Digital':
                sql_fb = sql_fb.replace(
                    "FROM solicitudes_compra sc",
                    "FROM solicitudes_compra sc LEFT JOIN pagos_influencers pi ON pi.numero_oc = sc.numero_oc"
                )
            for cond in [
                ("estado", filtro_estado), ("empresa", filtro_empresa),
                ("categoria", filtro_categoria),
            ]:
                pass  # los WHEREs y ORDER BY ya están aplicados via sql_with_extras
            # Reconstruir condiciones
            sql_fb_full = sql_fb
            params_fb = []
            if filtro_estado:
                sql_fb_full += " AND sc.estado=?"; params_fb.append(filtro_estado)
            if filtro_empresa:
                sql_fb_full += " AND sc.empresa=?"; params_fb.append(filtro_empresa)
            if filtro_categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro'):
                sql_fb_full += " AND sc.categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
            elif filtro_categoria:
                sql_fb_full += " AND sc.categoria=?"; params_fb.append(filtro_categoria)
            else:
                sql_fb_full += " AND sc.categoria NOT IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
            if filtro_categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro'):
                sql_fb_full += (
                    " ORDER BY CASE sc.estado WHEN 'Aprobada' THEN 0 "
                    "WHEN 'Pendiente' THEN 1 WHEN 'Pagada' THEN 2 ELSE 3 END, "
                    "COALESCE(NULLIF(sc.fecha_requerida,''), sc.fecha) ASC, "
                    "sc.numero ASC LIMIT 300"
                )
            else:
                sql_fb_full += " ORDER BY sc.fecha DESC LIMIT 200"
            __import__('logging').getLogger('compras').warning(
                "SELECT con extras falló (%s) — fallback a sql_minimal", _e
            )
            c.execute(sql_fb_full, params_fb)
        else:
            raise
    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area','email_solicitante','fecha_requerida','numero_oc','valor',
                'inf_nombre','inf_banco','inf_cuenta','inf_tipo_cuenta','inf_cedula','inf_email','inf_ciudad','inf_instagram']
    rows_sol = []
    for r in c.fetchall():
        row = dict(zip(cols_sol, r))
        # valor comes from OC join; fallback to items sum if still 0
        if not row.get('valor'):
            c2 = conn.cursor()
            c2.execute("SELECT COALESCE(SUM(valor_estimado),0) FROM solicitudes_compra_items WHERE numero=?", (row['numero'],))
            row['valor'] = c2.fetchone()[0] or 0
        # Last fallback: parse VALOR from OBS string (influencer SOLs without OC)
        if not row.get('valor'):
            obs_str = row.get('observaciones') or ''
            if 'VALOR:' in obs_str:
                try:
                    v_str = obs_str.split('VALOR:')[1].split('|')[0].strip().replace('$','').replace(',','').replace('.','')
                    row['valor'] = float(v_str)
                except (ValueError, IndexError):
                    # Observaciones malformadas — fallback silencioso aceptable
                    # (es solo enriquecimiento de display, no flujo crítico).
                    pass
        rows_sol.append(row)
    return jsonify({'solicitudes': rows_sol})


# ── Sebastián 4-may-2026 (Catalina): agrupar solicitudes por proveedor ────
# Catalina recibe 200+ solicitudes AUTO-PLAN desde planta (cada una es 1 MP
# en déficit). En vez de gestionarlas una por una, las quiere agrupadas
# por proveedor sugerido para procesar todas las del mismo proveedor en
# UNA sola OC. Endpoint que devuelve el agrupamiento + items consolidados.
@bp.route('/api/compras/solicitudes-agrupadas-por-proveedor', methods=['GET'])
def solicitudes_agrupadas_por_proveedor():
    """Agrupa solicitudes_compra Pendientes por proveedor sugerido.

    Querystring:
      ?estado=Pendiente|Aprobada|all  (default: Pendiente)
      ?categoria=Mat. Primas|Empaque|...  (default: todas excepto Influencer/CC)

    Returns:
      {
        "grupos": [
          {
            "proveedor": "Colquimicos",
            "solicitudes_count": 12,
            "items_count": 12,
            "valor_total": 1234567.89,
            "solicitudes": [{numero, fecha, urgencia, area, items: [...]}, ...],
            "items_consolidados": [{codigo_mp, nombre_mp, cantidad_g, valor_estimado}],
            "urgencia_max": "Urgente",
          }, ...
        ],
        "sin_proveedor": [...],   # mismo shape (proveedor='')
        "total_solicitudes": 204,
        "total_grupos": 18
      }

    Items se consolidan por codigo_mp dentro de cada grupo (suma de
    cantidad_g + valor_estimado). Esto es lo que Catalina usa para
    crear UNA OC por proveedor.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    estado_filtro = (request.args.get('estado') or 'Pendiente').strip()
    categoria_filtro = (request.args.get('categoria') or '').strip()

    conn = get_db(); c = conn.cursor()
    sql = """
        SELECT s.numero, s.fecha, s.estado, s.solicitante, s.urgencia,
               COALESCE(s.observaciones,''), s.empresa, s.categoria,
               s.tipo, s.area, s.fecha_requerida, COALESCE(s.numero_oc,''),
               COALESCE(s.valor, 0)
        FROM solicitudes_compra s
        WHERE 1=1
    """
    params = []
    if estado_filtro and estado_filtro.lower() != 'all':
        sql += " AND s.estado=?"
        params.append(estado_filtro)
    # Excluir Influencer/CC siempre — esos tienen flujo aparte
    sql += " AND s.categoria NOT IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
    if categoria_filtro:
        sql += " AND s.categoria=?"
        params.append(categoria_filtro)
    sql += " ORDER BY s.fecha DESC LIMIT 500"

    c.execute(sql, params)
    sol_cols = ['numero','fecha','estado','solicitante','urgencia','observaciones',
                'empresa','categoria','tipo','area','fecha_requerida','numero_oc','valor']
    solicitudes = [dict(zip(sol_cols, r)) for r in c.fetchall()]
    if not solicitudes:
        return jsonify({
            'grupos': [], 'sin_proveedor': [],
            'total_solicitudes': 0, 'total_grupos': 0,
        })

    # Cargar items de todas las solicitudes en 1 query (evita N+1)
    nums = [s['numero'] for s in solicitudes]
    placeholders = ','.join(['?'] * len(nums))
    try:
        c.execute(f"""
            SELECT id, numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                   COALESCE(valor_estimado, 0),
                   COALESCE(justificacion, ''),
                   COALESCE(precio_unit_g, 0),
                   COALESCE(proveedor_sugerido, '')
            FROM solicitudes_compra_items
            WHERE numero IN ({placeholders})
        """, nums)
        item_cols = ['id','numero','codigo_mp','nombre_mp','cantidad_g','unidad',
                     'valor_estimado','justificacion','precio_unit_g','proveedor_sugerido']
        items_all = [dict(zip(item_cols, r)) for r in c.fetchall()]
    except sqlite3.OperationalError:
        # Fallback sin proveedor_sugerido (esquema viejo)
        c.execute(f"""
            SELECT id, numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                   COALESCE(valor_estimado, 0)
            FROM solicitudes_compra_items
            WHERE numero IN ({placeholders})
        """, nums)
        items_all = []
        for r in c.fetchall():
            d = dict(zip(['id','numero','codigo_mp','nombre_mp','cantidad_g',
                          'unidad','valor_estimado'], r))
            d['justificacion'] = ''
            d['precio_unit_g'] = 0
            d['proveedor_sugerido'] = ''
            items_all.append(d)

    # Indexar items por solicitud
    items_por_sol = {}
    for it in items_all:
        items_por_sol.setdefault(it['numero'], []).append(it)

    # Determinar proveedor de cada solicitud (el primer item con proveedor_sugerido != '')
    # Si todos los items tienen el mismo proveedor → ese es el proveedor del grupo.
    # Si hay mezcla, marcar como 'Mixto' para que Catalina los revise individualmente.
    URG_RANK = {'Critico': 4, 'Urgente': 3, 'Alta': 2, 'Media': 1, 'Normal': 0}

    def _prov_dominante(items_lista):
        provs = {(it.get('proveedor_sugerido') or '').strip() for it in items_lista}
        provs.discard('')
        if not provs:
            return ''  # sin proveedor sugerido
        if len(provs) == 1:
            return provs.pop()
        return '__MIXTO__'

    # Agrupar
    grupos_dict = {}
    sin_proveedor = []
    for s in solicitudes:
        items = items_por_sol.get(s['numero'], [])
        s['items'] = items
        s['valor_calc'] = sum(float(it.get('valor_estimado') or 0) for it in items)
        prov = _prov_dominante(items)
        if not prov or prov == '__MIXTO__':
            target = sin_proveedor
            if prov == '__MIXTO__':
                s['_motivo_sin_grupo'] = 'mixto'
            else:
                s['_motivo_sin_grupo'] = 'sin_sugerencia'
            target.append(s)
        else:
            grupos_dict.setdefault(prov, []).append(s)

    # Construir output
    grupos = []
    for prov, sols in sorted(grupos_dict.items()):
        # Consolidar items por codigo_mp (suma)
        consolidados = {}
        for s in sols:
            for it in s['items']:
                k = (it.get('codigo_mp') or '').upper().strip() or it.get('nombre_mp', '')[:50]
                if k not in consolidados:
                    consolidados[k] = {
                        'codigo_mp': it.get('codigo_mp', ''),
                        'nombre_mp': it.get('nombre_mp', ''),
                        'unidad': it.get('unidad', 'g'),
                        'cantidad_g': 0.0,
                        'valor_estimado': 0.0,
                        'precio_unit_g': float(it.get('precio_unit_g') or 0),
                        'solicitudes_origen': [],
                    }
                consolidados[k]['cantidad_g'] += float(it.get('cantidad_g') or 0)
                consolidados[k]['valor_estimado'] += float(it.get('valor_estimado') or 0)
                consolidados[k]['solicitudes_origen'].append(s['numero'])
        urg_max = 'Normal'
        for s in sols:
            if URG_RANK.get(s.get('urgencia') or 'Normal', 0) > URG_RANK.get(urg_max, 0):
                urg_max = s.get('urgencia') or 'Normal'
        grupos.append({
            'proveedor': prov,
            'solicitudes_count': len(sols),
            'items_count': len(consolidados),
            'valor_total': round(sum(float(s.get('valor_calc') or 0) for s in sols), 2),
            'urgencia_max': urg_max,
            'solicitudes': sols,
            'items_consolidados': sorted(consolidados.values(),
                                          key=lambda x: -float(x.get('valor_estimado') or 0)),
        })

    # Ordenar grupos por urgencia max → solicitudes_count desc
    grupos.sort(key=lambda g: (-URG_RANK.get(g['urgencia_max'], 0),
                                -g['solicitudes_count']))

    return jsonify({
        'grupos': grupos,
        'sin_proveedor': sin_proveedor,
        'total_solicitudes': len(solicitudes),
        'total_grupos': len(grupos),
        'estado_filtro': estado_filtro,
        'categoria_filtro': categoria_filtro,
    })


# ── Sebastián 4-may-2026 (Catalina): convertir N solicitudes en 1 OC ──
@bp.route('/api/compras/oc-desde-solicitudes', methods=['POST'])
def crear_oc_desde_solicitudes():
    """Convierte un lote de solicitudes_compra Pendientes en UNA sola OC.

    Body JSON:
      {
        "proveedor": "Colquimicos",       # requerido
        "solicitudes": ["AUTO-0946",...],  # requerido (lista de numeros)
        "observaciones": "...",            # opcional
        "fecha_entrega_est": "2026-05-15", # opcional
        "consolidar_iguales": true,        # default true (suma cant por codigo_mp)
        "categoria": "MP"                  # default "MP"
      }

    Atomico: si cualquier paso falla, rollback completo. La OC no queda
    creada y las solicitudes no cambian de estado.

    Returns:
      201 {numero_oc, items_creados, solicitudes_vinculadas, valor_total}
      400 si validacion falla (proveedor faltante, solicitudes vacias)
      404 si alguna solicitud no existe
      409 si alguna solicitud no esta Pendiente o ya tiene OC
    """
    usuario, err, code = _require_compras_write()
    if err:
        return err, code

    d = request.get_json(silent=True) or {}
    proveedor = (d.get('proveedor') or '').strip()
    nums = d.get('solicitudes') or []
    if not proveedor:
        return jsonify({'error': 'proveedor requerido'}), 400
    if not isinstance(nums, list) or not nums:
        return jsonify({'error': 'solicitudes (lista) requerido'}), 400
    nums = [str(n).strip().upper() for n in nums if str(n).strip()]
    if not nums:
        return jsonify({'error': 'solicitudes lista vacia'}), 400
    if len(nums) > 100:
        return jsonify({'error': 'maximo 100 solicitudes por OC'}), 400

    consolidar = bool(d.get('consolidar_iguales', True))
    categoria = (d.get('categoria') or 'MP').strip()
    obs_extra = (d.get('observaciones') or '').strip()
    fecha_entrega_est = (d.get('fecha_entrega_est') or '').strip()

    conn = get_db(); c = conn.cursor()
    try:
        # 1. Validar todas las solicitudes
        placeholders = ','.join(['?'] * len(nums))
        c.execute(f"""
            SELECT numero, estado, COALESCE(numero_oc,'')
            FROM solicitudes_compra
            WHERE numero IN ({placeholders})
        """, nums)
        rows = c.fetchall()
        existentes = {r[0]: (r[1], r[2]) for r in rows}
        faltantes = [n for n in nums if n not in existentes]
        if faltantes:
            return jsonify({
                'error': 'Solicitudes no encontradas',
                'faltantes': faltantes,
            }), 404
        no_pendientes = [n for n, (est, oc) in existentes.items() if est != 'Pendiente']
        if no_pendientes:
            return jsonify({
                'error': 'Hay solicitudes que no estan Pendientes',
                'no_pendientes': no_pendientes,
            }), 409
        ya_oc = [n for n, (est, oc) in existentes.items() if oc]
        if ya_oc:
            return jsonify({
                'error': 'Hay solicitudes que ya tienen OC asociada',
                'ya_con_oc': ya_oc,
            }), 409

        # 2. Cargar items de todas las solicitudes
        try:
            c.execute(f"""
                SELECT numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                       COALESCE(valor_estimado, 0),
                       COALESCE(precio_unit_g, 0),
                       COALESCE(proveedor_sugerido, '')
                FROM solicitudes_compra_items
                WHERE numero IN ({placeholders})
            """, nums)
            items_raw = [
                {'numero': r[0], 'codigo_mp': r[1] or '', 'nombre_mp': r[2] or '',
                 'cantidad_g': float(r[3] or 0), 'unidad': r[4] or 'g',
                 'valor_estimado': float(r[5] or 0),
                 'precio_unit_g': float(r[6] or 0),
                 'proveedor_sugerido': r[7] or ''}
                for r in c.fetchall()
            ]
        except sqlite3.OperationalError:
            c.execute(f"""
                SELECT numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                       COALESCE(valor_estimado, 0)
                FROM solicitudes_compra_items
                WHERE numero IN ({placeholders})
            """, nums)
            items_raw = [
                {'numero': r[0], 'codigo_mp': r[1] or '', 'nombre_mp': r[2] or '',
                 'cantidad_g': float(r[3] or 0), 'unidad': r[4] or 'g',
                 'valor_estimado': float(r[5] or 0),
                 'precio_unit_g': 0.0,
                 'proveedor_sugerido': ''}
                for r in c.fetchall()
            ]

        if not items_raw:
            return jsonify({'error': 'Las solicitudes no tienen items'}), 400

        # 3. Consolidar items por codigo_mp si se pidio
        if consolidar:
            consolidados = {}
            for it in items_raw:
                k = (it['codigo_mp'] or '').upper().strip() or it['nombre_mp'][:50]
                if k not in consolidados:
                    consolidados[k] = {
                        'codigo_mp': it['codigo_mp'],
                        'nombre_mp': it['nombre_mp'],
                        'cantidad_g': 0.0,
                        'precio_unitario': it['precio_unit_g'] or 0.0,
                        'unidad': it['unidad'],
                    }
                consolidados[k]['cantidad_g'] += it['cantidad_g']
                # Si llega un precio_unit_g distinto, dejar el primero no-cero
                if not consolidados[k]['precio_unitario'] and it['precio_unit_g']:
                    consolidados[k]['precio_unitario'] = it['precio_unit_g']
            items_oc = list(consolidados.values())
        else:
            items_oc = [
                {'codigo_mp': it['codigo_mp'], 'nombre_mp': it['nombre_mp'],
                 'cantidad_g': it['cantidad_g'],
                 'precio_unitario': it['precio_unit_g'],
                 'unidad': it['unidad']}
                for it in items_raw
            ]

        # 4. Crear la OC
        c.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) "
            "FROM ordenes_compra WHERE numero_oc LIKE ?",
            (f"OC-{datetime.now().strftime('%Y')}-%",),
        )
        next_n = (c.fetchone()[0] or 0) + 1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{next_n:04d}"
        obs = f"OC consolidada desde {len(nums)} solicitudes"
        if obs_extra:
            obs = obs_extra + ' · ' + obs
        c.execute(
            """INSERT INTO ordenes_compra
               (numero_oc, fecha, estado, proveedor, observaciones,
                creado_por, fecha_entrega_est, categoria)
               VALUES (?,?,?,?,?,?,?,?)""",
            (numero_oc, datetime.now().isoformat(), 'Borrador', proveedor,
             obs, usuario, fecha_entrega_est, categoria),
        )

        # 5. Auto-crear proveedor si no existe (con audit_log)
        try:
            existe = c.execute(
                "SELECT id FROM proveedores WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?)) AND activo=1",
                (proveedor,),
            ).fetchone()
            if not existe:
                c.execute(
                    """INSERT INTO proveedores (nombre, categoria, condiciones_pago,
                                                 activo, fecha_creacion)
                       VALUES (?,?,?,1,?)""",
                    (proveedor, categoria, '30 dias', datetime.now().isoformat()),
                )
                try:
                    audit_log(
                        c, usuario=usuario, accion='CREAR_PROVEEDOR',
                        tabla='proveedores', registro_id=c.lastrowid,
                        despues={'nombre': proveedor[:200], 'categoria': categoria,
                                  'origen': 'auto_oc_desde_solicitudes',
                                  'oc_origen': numero_oc},
                        detalle=f"Auto-creado al consolidar {len(nums)} solicitudes en {numero_oc}",
                    )
                except Exception:
                    pass
        except Exception:
            pass

        # 6. Insertar items en la OC
        valor_total = 0.0
        for it in items_oc:
            cant_g = float(it.get('cantidad_g') or 0)
            pu = float(it.get('precio_unitario') or 0)
            subt = round(cant_g * pu, 2)
            valor_total += subt
            c.execute(
                """INSERT INTO ordenes_compra_items
                   (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
                   VALUES (?,?,?,?,?,?)""",
                (numero_oc, it.get('codigo_mp', ''), it.get('nombre_mp', ''),
                 cant_g, pu, subt),
            )
            # Historico de precios + ref maestro_mps
            cod_mp = it.get('codigo_mp', '')
            if cod_mp and pu > 0:
                try:
                    c.execute(
                        """INSERT OR IGNORE INTO precios_mp_historico
                           (codigo_mp, nombre_mp, precio_unitario, proveedor,
                            fecha, numero_oc, cantidad_g)
                           VALUES (?,?,?,?,?,?,?)""",
                        (cod_mp, it.get('nombre_mp', ''), pu, proveedor,
                         datetime.now().isoformat()[:10], numero_oc, cant_g),
                    )
                except Exception:
                    pass
                try:
                    c.execute(
                        """UPDATE maestro_mps
                           SET precio_referencia=?,
                               proveedor=COALESCE(NULLIF(proveedor,''),?)
                           WHERE codigo_mp=?""",
                        (pu, proveedor, cod_mp),
                    )
                except Exception:
                    pass

        if valor_total > 0:
            c.execute(
                "UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?",
                (valor_total, numero_oc),
            )

        # 7. Vincular las solicitudes a la nueva OC y marcarlas Aprobada
        c.execute(
            f"""UPDATE solicitudes_compra
                SET estado='Aprobada', numero_oc=?
                WHERE numero IN ({placeholders}) AND estado='Pendiente'
                  AND COALESCE(numero_oc,'')=''""",
            [numero_oc] + nums,
        )
        vinculadas = c.rowcount

        # 8. Audit log
        try:
            audit_log(
                c, usuario=usuario, accion='CREAR_OC_BULK',
                tabla='ordenes_compra', registro_id=numero_oc,
                despues={
                    'proveedor': proveedor[:200],
                    'categoria': categoria,
                    'items_count': len(items_oc),
                    'valor_total': round(valor_total, 2),
                    'solicitudes_vinculadas': vinculadas,
                    'solicitudes_origen': nums[:50],  # cap a 50 en audit
                    'consolidar_iguales': consolidar,
                },
                detalle=(f"Creó OC {numero_oc} consolidada desde "
                         f"{vinculadas} solicitudes · {proveedor} · "
                         f"{len(items_oc)} items · total {valor_total:.0f}"),
            )
        except Exception as e:
            log.warning('audit_log CREAR_OC_BULK fallo: %s', e)

        conn.commit()
        return jsonify({
            'ok': True,
            'numero_oc': numero_oc,
            'proveedor': proveedor,
            'items_creados': len(items_oc),
            'solicitudes_vinculadas': vinculadas,
            'valor_total': round(valor_total, 2),
            'estado': 'Borrador',
        }), 201
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        log.exception('crear_oc_desde_solicitudes fallo: %s', e)
        return jsonify({'error': str(e)}), 500


# ── Sebastián 4-may-2026 (Catalina): consolidar AUTO-XXXX pendientes ────
# Una sola pasada que toma las 200+ AUTO-XXXX Pendientes (1-MP-cada-una)
# y las transforma en ~15-20 solicitudes consolidadas por proveedor.
# El generador ya consolida desde aqui (auto_plan.py:936) pero hay datos
# legacy que necesitan limpieza. Idempotente: si vuelve a correr cuando
# ya esta consolidado, no rompe nada.
@bp.route('/api/compras/consolidar-auto-pendientes', methods=['POST'])
def consolidar_auto_pendientes():
    """Consolida solicitudes AUTO-XXXX Pendientes existentes por proveedor.

    Body JSON (opcional):
      {
        "dry_run": false,        # default false. Si true, solo retorna
                                  el plan de consolidacion sin ejecutar.
        "min_para_consolidar": 5 # solo consolida si hay >=5 SOLs sueltas
                                  con el mismo proveedor (default 1 = todas)
      }

    Algoritmo:
      1. SELECT de AUTO-XXXX Pendientes con sus items
      2. Identifica las que tienen 1 item (sospechosas de ser legacy)
      3. Agrupa por (proveedor_sugerido, categoria)
      4. Si grupo tiene >= min_para_consolidar SOLs → crear UNA nueva
         AUTO-XXXX consolidada con todos los items + delete las viejas
      5. Atomico: rollback completo si algo falla
      6. audit_log CONSOLIDAR_AUTO_PENDIENTES con conteos

    Returns:
      200 {ok, antes, despues, grupos: [...], eliminadas, creadas}
      403 si no tiene permisos
    """
    usuario, err, code = _require_compras_write()
    if err:
        return err, code

    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get('dry_run', False))
    try:
        min_para_consolidar = int(body.get('min_para_consolidar', 1))
    except (ValueError, TypeError):
        min_para_consolidar = 1
    if min_para_consolidar < 1:
        min_para_consolidar = 1

    conn = get_db(); c = conn.cursor()

    # 1. Cargar AUTO-XXXX Pendientes (sin OC) y sus items
    c.execute("""
        SELECT numero, urgencia, COALESCE(observaciones,''), categoria, fecha
        FROM solicitudes_compra
        WHERE numero LIKE 'AUTO-%' AND estado='Pendiente'
          AND COALESCE(numero_oc,'') = ''
        ORDER BY numero
    """)
    auto_sols = c.fetchall()
    if not auto_sols:
        return jsonify({
            'ok': True, 'antes': 0, 'despues': 0,
            'mensaje': 'Sin AUTO-XXXX pendientes para consolidar',
            'grupos': [], 'eliminadas': 0, 'creadas': 0,
        })

    nums = [r[0] for r in auto_sols]
    placeholders = ','.join(['?'] * len(nums))

    try:
        c.execute(f"""
            SELECT numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                   COALESCE(valor_estimado,0), COALESCE(justificacion,''),
                   COALESCE(precio_unit_g,0), COALESCE(proveedor_sugerido,'')
            FROM solicitudes_compra_items
            WHERE numero IN ({placeholders})
        """, nums)
        items_all = [
            {'numero': r[0], 'codigo_mp': r[1] or '', 'nombre_mp': r[2] or '',
             'cantidad_g': float(r[3] or 0), 'unidad': r[4] or 'g',
             'valor_estimado': float(r[5] or 0), 'justificacion': r[6] or '',
             'precio_unit_g': float(r[7] or 0),
             'proveedor_sugerido': r[8] or ''}
            for r in c.fetchall()
        ]
    except sqlite3.OperationalError:
        c.execute(f"""
            SELECT numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                   COALESCE(valor_estimado,0), COALESCE(justificacion,'')
            FROM solicitudes_compra_items
            WHERE numero IN ({placeholders})
        """, nums)
        items_all = []
        for r in c.fetchall():
            items_all.append({
                'numero': r[0], 'codigo_mp': r[1] or '',
                'nombre_mp': r[2] or '', 'cantidad_g': float(r[3] or 0),
                'unidad': r[4] or 'g', 'valor_estimado': float(r[5] or 0),
                'justificacion': r[6] or '', 'precio_unit_g': 0.0,
                'proveedor_sugerido': '',
            })

    items_por_sol = {}
    for it in items_all:
        items_por_sol.setdefault(it['numero'], []).append(it)

    # Sebastian 4-may-2026 (Catalina): si el item NO tiene proveedor_sugerido
    # (legacy de aplicar_plan que leia solo mp_lead_time_config), buscarlo en
    # maestro_mps.proveedor por codigo_mp. Asi no aparecen "sin proveedor".
    cods_sin_prov = {it['codigo_mp'].upper() for it in items_all
                      if it['codigo_mp'] and not (it.get('proveedor_sugerido') or '').strip()}
    prov_lookup = {}
    if cods_sin_prov:
        ph_cod = ','.join(['?'] * len(cods_sin_prov))
        try:
            for r in c.execute(
                f"SELECT UPPER(codigo_mp), COALESCE(proveedor,'') "
                f"FROM maestro_mps WHERE UPPER(codigo_mp) IN ({ph_cod})",
                list(cods_sin_prov),
            ).fetchall():
                if r[1]:
                    prov_lookup[r[0]] = r[1]
        except Exception:
            pass
    # Aplicar fallback in-place a items_all
    for it in items_all:
        if not (it.get('proveedor_sugerido') or '').strip():
            cod_up = (it.get('codigo_mp') or '').upper()
            fallback = prov_lookup.get(cod_up, '')
            if fallback:
                it['proveedor_sugerido'] = fallback
                it['_proveedor_fallback'] = True  # marca para audit/observ

    # 2. Agrupar por (proveedor_sugerido, categoria) las que SOLO tienen 1 item
    # (legacy 1-MP-por-AUTO-XXXX). Las que ya tienen N>1 items son las nuevas
    # consolidadas - se respetan tal cual.
    URG_RANK = {'Critico': 4, 'Urgente': 3, 'Alta': 2, 'Media': 1, 'Normal': 0}
    grupos = {}
    intactas = []  # AUTO-XXXX con >=2 items (ya consolidadas)
    sol_meta = {r[0]: {'urgencia': r[1] or 'Normal', 'observ': r[2] or '',
                        'categoria': r[3] or 'Materia Prima',
                        'fecha': r[4]} for r in auto_sols}
    for num in nums:
        items = items_por_sol.get(num, [])
        if len(items) >= 2:
            intactas.append(num)
            continue
        if not items:
            # SOL sin items — caso raro. La preservamos.
            intactas.append(num)
            continue
        prov = (items[0].get('proveedor_sugerido') or '').strip()
        cat = sol_meta[num]['categoria']
        key = (prov, cat)
        grupos.setdefault(key, []).append(num)

    # 3. Construir plan de consolidacion
    plan_grupos = []
    for (prov, cat), sols in grupos.items():
        if len(sols) < min_para_consolidar:
            # No vale la pena consolidar
            continue
        # Sumar urgencia max
        rank_max = 0
        for n in sols:
            r = URG_RANK.get(sol_meta[n]['urgencia'], 0)
            if r > rank_max:
                rank_max = r
        urg_label = {4: 'Critico', 3: 'Urgente', 2: 'Alta',
                      1: 'Media', 0: 'Normal'}[rank_max]
        # Items de todas las SOLs del grupo
        items_grupo = []
        for n in sols:
            for it in items_por_sol.get(n, []):
                items_grupo.append(it)
        plan_grupos.append({
            'proveedor': prov,
            'proveedor_label': prov or '(Sin proveedor sugerido)',
            'categoria': cat,
            'urgencia': urg_label,
            'sols_origen': sols,
            'items_count': len(items_grupo),
            'total_g': round(sum(it['cantidad_g'] for it in items_grupo), 0),
            '_items_payload': items_grupo,  # se elimina antes de retornar JSON
        })

    if dry_run:
        # Retornar el plan sin tocar DB
        for g in plan_grupos:
            g.pop('_items_payload', None)
        return jsonify({
            'ok': True,
            'dry_run': True,
            'antes': len(nums),
            'intactas': len(intactas),
            'despues': len(plan_grupos) + len(intactas),
            'grupos': plan_grupos,
            'eliminadas': 0,
            'creadas': 0,
            'mensaje': (f'Plan: consolidar {sum(len(g["sols_origen"]) for g in plan_grupos)} '
                         f'SOLs en {len(plan_grupos)} grupos · {len(intactas)} '
                         f'quedan intactas (ya consolidadas)'),
        })

    if not plan_grupos:
        return jsonify({
            'ok': True,
            'antes': len(nums),
            'intactas': len(intactas),
            'despues': len(nums),
            'grupos': [],
            'eliminadas': 0,
            'creadas': 0,
            'mensaje': f'Nada que consolidar · {len(intactas)} ya estan consolidadas',
        })

    # 4. Ejecutar atomicamente
    creadas_nums = []
    sols_a_eliminar = []
    try:
        for g in plan_grupos:
            # Generar numero AUTO-XXXX nuevo
            next_n = c.execute("""
                SELECT COALESCE(MAX(CAST(SUBSTR(numero, 6) AS INTEGER)), 0) + 1
                FROM solicitudes_compra WHERE numero LIKE 'AUTO-%'
            """).fetchone()[0] or 1
            new_num = f'AUTO-{next_n:04d}'

            top = sorted(g['_items_payload'], key=lambda x: -float(x.get('cantidad_g') or 0))[:3]
            resumen = ', '.join(
                f"{(it.get('nombre_mp') or '')[:25]} {round(float(it.get('cantidad_g') or 0)/1000.0,1)}kg"
                for it in top
            )
            if g['items_count'] > 3:
                resumen += f", +{g['items_count'] - 3} mas"
            obs = (
                f"AUTO-PLAN consolidado · proveedor: {g['proveedor_label']} · "
                f"{g['items_count']} MPs · {round(g['total_g']/1000.0,1)}kg total · "
                f"{resumen} · (consolidacion legacy {datetime.now().date().isoformat()})"
            )

            c.execute("""
                INSERT INTO solicitudes_compra
                  (numero, fecha, estado, solicitante, urgencia,
                   observaciones, area, empresa, categoria, tipo, valor)
                VALUES (?, date('now'), 'Pendiente', 'AUTO-PLAN', ?, ?,
                        'Producción', 'Espagiria', ?, 'Compra', 0)
            """, (new_num, g['urgencia'], obs, g['categoria']))
            for it in g['_items_payload']:
                try:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado, proveedor_sugerido,
                           precio_unit_g)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_num, it['codigo_mp'], it['nombre_mp'],
                          it['cantidad_g'], it['unidad'],
                          it['justificacion'], it['valor_estimado'],
                          g['proveedor'], it['precio_unit_g']))
                except sqlite3.OperationalError:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (new_num, it['codigo_mp'], it['nombre_mp'],
                          it['cantidad_g'], it['unidad'],
                          it['justificacion'], it['valor_estimado']))
            creadas_nums.append(new_num)
            sols_a_eliminar.extend(g['sols_origen'])

        # Eliminar las legacy
        if sols_a_eliminar:
            ph_del = ','.join(['?'] * len(sols_a_eliminar))
            c.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph_del})",
                      sols_a_eliminar)
            c.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph_del})",
                      sols_a_eliminar)

        # Audit
        try:
            audit_log(
                c, usuario=usuario, accion='CONSOLIDAR_AUTO_PENDIENTES',
                tabla='solicitudes_compra', registro_id='bulk',
                despues={
                    'antes': len(nums), 'intactas': len(intactas),
                    'eliminadas': len(sols_a_eliminar),
                    'creadas': len(creadas_nums),
                    'creadas_nums': creadas_nums[:50],
                    'min_para_consolidar': min_para_consolidar,
                },
                detalle=(f"Consolido {len(sols_a_eliminar)} AUTO-XXXX legacy "
                          f"en {len(creadas_nums)} solicitudes por proveedor"),
            )
        except Exception as _e:
            log.warning('audit_log CONSOLIDAR_AUTO_PENDIENTES fallo: %s', _e)

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        log.exception('consolidar_auto_pendientes fallo: %s', e)
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'ok': True,
        'antes': len(nums),
        'intactas': len(intactas),
        'eliminadas': len(sols_a_eliminar),
        'creadas': len(creadas_nums),
        'creadas_nums': creadas_nums,
        'despues': len(creadas_nums) + len(intactas),
        'mensaje': (f'Consolidadas {len(sols_a_eliminar)} solicitudes legacy en '
                     f'{len(creadas_nums)} agrupadas por proveedor'),
    })


# ── Sebastián 4-may-2026 (Catalina): limpiar y regenerar AUTO-PLAN ────
@bp.route('/api/compras/limpiar-y-regenerar-auto-plan', methods=['POST'])
def limpiar_y_regenerar_auto_plan():
    """Borra TODAS las AUTO-XXXX Pendientes (sin OC) y vuelve a generar.

    Caso de uso: los AUTO-XXXX existentes vienen del cron que leia
    mp_lead_time_config sin fallback a maestro_mps.proveedor → muchas
    quedaban sin proveedor. Con el fix de aplicar_plan() (4-may-2026)
    ahora SI tienen fallback. Este endpoint deja todo limpio y
    regenera con la logica nueva → Catalina ve solicitudes consolidadas
    por proveedor real.

    Body JSON (opcional):
      {
        "horizonte_dias": 60,        # default 60d
        "dry_run": false,            # si true, solo cuenta lo que borraria
        "regenerar": true            # default true. Si false, solo borra y
                                      # deja que el cron de planta regenere
                                      # agrupado en la siguiente corrida.
      }

    Returns:
      200 {ok, eliminadas, creadas, mensaje}
    """
    usuario, err, code = _require_compras_write()
    if err:
        return err, code

    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get('dry_run', False))
    regenerar = bool(body.get('regenerar', True))
    try:
        horizonte = int(body.get('horizonte_dias', 60))
    except (ValueError, TypeError):
        horizonte = 60
    if not (7 <= horizonte <= 365):
        return jsonify({'error': 'horizonte_dias fuera de rango (7-365)'}), 400

    conn = get_db(); c = conn.cursor()
    # Contar AUTO-XXXX Pendientes sin OC vinculada
    c.execute("""
        SELECT numero FROM solicitudes_compra
        WHERE numero LIKE 'AUTO-%' AND estado='Pendiente'
          AND COALESCE(numero_oc,'') = ''
    """)
    nums_a_borrar = [r[0] for r in c.fetchall()]

    if dry_run:
        plan_txt = f'Plan: borrar {len(nums_a_borrar)} AUTO-XXXX Pendientes'
        if regenerar:
            plan_txt += f' + regenerar con horizonte {horizonte}d'
        else:
            plan_txt += ' (sin regenerar — cron de planta lo hara despues agrupado)'
        return jsonify({
            'ok': True,
            'dry_run': True,
            'eliminaria': len(nums_a_borrar),
            'horizonte_dias': horizonte,
            'regenerar': regenerar,
            'mensaje': plan_txt,
        })

    try:
        # 1. Borrar items + solicitudes
        eliminadas_items = 0
        if nums_a_borrar:
            ph = ','.join(['?'] * len(nums_a_borrar))
            r1 = c.execute(
                f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})",
                nums_a_borrar,
            )
            eliminadas_items = r1.rowcount or 0
            c.execute(
                f"DELETE FROM solicitudes_compra WHERE numero IN ({ph})",
                nums_a_borrar,
            )

        # 2. Audit del borrado
        try:
            audit_log(
                c, usuario=usuario, accion='LIMPIAR_AUTO_PLAN',
                tabla='solicitudes_compra', registro_id='bulk',
                despues={'eliminadas': len(nums_a_borrar),
                          'items_eliminados': eliminadas_items,
                          'horizonte_dias': horizonte},
                detalle=f"Limpio {len(nums_a_borrar)} AUTO-XXXX Pendientes para regenerar",
            )
        except Exception:
            pass

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        log.exception('limpiar_y_regenerar_auto_plan borrado fallo: %s', e)
        return jsonify({'error': f'Borrado fallido: {e}'}), 500

    # 3. Regenerar con generar_plan + aplicar_plan (solo si regenerar=true)
    if not regenerar:
        return jsonify({
            'ok': True,
            'eliminadas': len(nums_a_borrar),
            'creadas': 0,
            'regenerar': False,
            'horizonte_dias': horizonte,
            'grupos': [],
            'mensaje': (f'✓ Limpiadas {len(nums_a_borrar)} AUTO-XXXX legacy. '
                         f'El cron de planta regenerara agrupado por proveedor '
                         f'en la proxima corrida (o usa Regenerar manual).'),
        })

    try:
        from blueprints.auto_plan import generar_plan, aplicar_plan
        plan = generar_plan(horizonte_dias=horizonte, tipo='manual', usuario=usuario)
        resultado = aplicar_plan(plan, usuario=usuario)
    except Exception as e:
        log.exception('limpiar_y_regenerar_auto_plan regeneracion fallo: %s', e)
        return jsonify({
            'error': f'Borrado OK pero falló la regeneración: {e}',
            'eliminadas': len(nums_a_borrar),
            'creadas': 0,
        }), 500

    creadas = resultado.get('compras_creadas', []) or []
    grupos_resumen = []
    for cc in creadas[:30]:
        grupos_resumen.append({
            'numero': cc.get('numero'),
            'proveedor': cc.get('proveedor', ''),
            'items_count': cc.get('items_count', 0),
            'total_g': cc.get('total_g', 0),
        })

    return jsonify({
        'ok': True,
        'eliminadas': len(nums_a_borrar),
        'creadas': len(creadas),
        'horizonte_dias': horizonte,
        'grupos': grupos_resumen,
        'mensaje': (f'✓ Eliminadas {len(nums_a_borrar)} AUTO-XXXX legacy · '
                     f'Regeneradas {len(creadas)} consolidadas por proveedor '
                     f'(horizonte {horizonte}d)'),
    })


@bp.route('/api/solicitudes-compra/mis', methods=['GET'])
def mis_solicitudes_con_ciclo():
    """Devuelve las solicitudes del usuario logueado con el ciclo COMPLETO
    consolidado: estado de la solicitud + estado de la OC vinculada + si
    fue recibida fisicamente. Pensado para que el SOLICITANTE (Hernando,
    Luz, etc) pueda hacer seguimiento sin depender de Catalina.

    Sebastian (29-abr-2026): "si alguien pide papel, lo hace en
    solicitudes, pero quizas alli mismo deberia aparecer todo el listado
    de solicitudes que sean generales para que vean como va, si ya fue
    aceptada pagada en transito y cuando lleguen coloquen recibido asi
    hacemos el cierre de todo".

    Querystring:
      ?usuario=<user>  → fuerza el filtro (admin puede pasar otro)
                         Si no se pasa, usa el session user.
      ?estado=todas|abiertas|cerradas (default abiertas)
        - abiertas: solicitudes en cualquier paso del ciclo no Recibida/Cancelada
        - cerradas: Recibida, Cancelada, Rechazada
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    usuario_filtro = (request.args.get('usuario') or user).strip().lower()
    estado_q = (request.args.get('estado') or 'abiertas').strip().lower()

    conn = get_db(); c = conn.cursor()
    # Sebastián 1-may-2026: las solicitudes de Influencer/Marketing
    # (Cuenta de Cobro · empresa ANIMUS · area Marketing) NO deben aparecer
    # acá — entran a Compras directo en pestaña "Influencer" para que
    # Catalina no se enrede mezclándolas con producción.
    incluir_influencer = request.args.get('incluir_influencer', '0').strip() in ('1','true','yes')
    sql_solic = """
        SELECT s.numero, s.fecha, s.estado as estado_sol, s.solicitante,
               s.urgencia, s.observaciones, s.numero_oc, s.area, s.empresa,
               s.categoria, s.tipo, s.fecha_requerida, s.valor,
               oc.estado as estado_oc, oc.proveedor as oc_proveedor,
               oc.fecha_pago, oc.fecha_recepcion, oc.fecha_entrega_est,
               oc.valor_total as oc_valor, oc.recibido_por
        FROM solicitudes_compra s
        LEFT JOIN ordenes_compra oc ON oc.numero_oc = s.numero_oc
        WHERE LOWER(COALESCE(s.solicitante,''))=?"""
    params_solic = [usuario_filtro]
    if not incluir_influencer:
        sql_solic += """
          AND COALESCE(s.categoria,'') NOT IN ('Cuenta de Cobro','Influencer/Marketing Digital')
          AND LOWER(COALESCE(s.area,'')) NOT IN ('marketing','marketing/animus')"""
    sql_solic += " ORDER BY s.fecha DESC LIMIT 200"
    rows = c.execute(sql_solic, params_solic).fetchall()

    cols = [d[0] for d in c.description]
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        # Determinar el "paso" del ciclo y badge consolidado.
        # Orden de prioridad: lo mas avanzado del ciclo manda.
        oc_estado = (d.get('estado_oc') or '').strip()
        sol_estado = (d.get('estado_sol') or '').strip()
        paso = 1
        paso_label = 'Pendiente aprobación'
        paso_color = '#a16207'
        cerrado = False
        if oc_estado == 'Recibida':
            paso, paso_label, paso_color = 6, '✅ Recibida en bodega', '#15803d'
            cerrado = True
        elif oc_estado == 'Parcial':
            paso, paso_label, paso_color = 5, '📦 Recepción parcial — esperando resto', '#f59e0b'
        elif oc_estado == 'Pagada':
            paso, paso_label, paso_color = 4, '💸 Pagada — en tránsito hacia bodega', '#1e40af'
        elif oc_estado == 'Autorizada':
            paso, paso_label, paso_color = 3, '🟢 OC autorizada — pendiente pago', '#0891b2'
        elif oc_estado in ('Aprobada', 'Revisada'):
            paso, paso_label, paso_color = 3, f'📋 OC {oc_estado.lower()}', '#0891b2'
        elif oc_estado == 'Borrador':
            paso, paso_label, paso_color = 2, '📝 OC en borrador', '#6b7280'
        elif oc_estado == 'Pendiente':
            paso, paso_label, paso_color = 2, '📝 OC pendiente revisión', '#6b7280'
        elif oc_estado in ('Cancelada', 'Rechazada'):
            paso, paso_label, paso_color = 0, f'❌ OC {oc_estado.lower()}', '#dc2626'
            cerrado = True
        elif sol_estado == 'Aprobada':
            paso, paso_label, paso_color = 2, '🟢 Solicitud aprobada — generando OC', '#0891b2'
        elif sol_estado == 'Rechazada':
            paso, paso_label, paso_color = 0, '❌ Solicitud rechazada', '#dc2626'
            cerrado = True
        else:
            paso, paso_label, paso_color = 1, '⏳ Pendiente aprobación de Catalina', '#a16207'
        d['paso'] = paso
        d['paso_label'] = paso_label
        d['paso_color'] = paso_color
        d['cerrado'] = cerrado
        # Habilitar boton "Marcar recibido" cuando la OC esta Pagada/Autorizada
        # (la mercancia esta en transito) o si no hay OC pero la solicitud
        # fue aprobada y nunca se genero OC formal (caso simple).
        d['puede_marcar_recibido'] = (
            oc_estado in ('Pagada', 'Autorizada', 'Parcial')
            or (not oc_estado and sol_estado == 'Aprobada')
        )
        out.append(d)

    if estado_q == 'cerradas':
        out = [x for x in out if x['cerrado']]
    elif estado_q == 'abiertas':
        out = [x for x in out if not x['cerrado']]

    abiertas_count = sum(1 for x in out if not x.get('cerrado'))
    return jsonify({'solicitudes': out, 'usuario': usuario_filtro,
                    'total': len(out), 'abiertas': abiertas_count})


@bp.route('/api/solicitudes-compra/<numero>/marcar-recibido-solicitante', methods=['POST'])
def marcar_recibido_solicitante(numero):
    """El solicitante confirma que la mercancia ya llego (sin pasar por
    Catalina). Cierra la cadena en su lado: actualiza la OC a 'Recibida'
    si esta en Autorizada/Pagada/Parcial.

    Solo puede hacerlo el solicitante original (o admin).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json() or {}
    obs = (d.get('observaciones') or '').strip()
    conn = get_db(); c = conn.cursor()
    # Verificar autoria
    sol = c.execute(
        "SELECT solicitante, numero_oc, estado FROM solicitudes_compra WHERE numero=?",
        (numero.upper(),)
    ).fetchone()
    if not sol:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    solicitante_orig = (sol[0] or '').lower()
    es_admin = user in ADMIN_USERS
    if solicitante_orig != user.lower() and not es_admin:
        return jsonify({
            'error': 'Solo el solicitante original o un admin puede marcar recibido'
        }), 403

    numero_oc = sol[1] or ''
    if numero_oc:
        oc_row = c.execute(
            "SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)
        ).fetchone()
        if not oc_row:
            return jsonify({'error': f'OC {numero_oc} no encontrada'}), 404
        oc_estado = oc_row[0] or ''
        if oc_estado not in ('Autorizada', 'Pagada', 'Parcial'):
            return jsonify({
                'error': f'OC en estado {oc_estado} — no se puede marcar recibida desde solicitante'
            }), 409
        c.execute("""
            UPDATE ordenes_compra SET
              estado='Recibida',
              fecha_recepcion=COALESCE(fecha_recepcion, datetime('now')),
              recibido_por=?,
              observaciones_recepcion=COALESCE(observaciones_recepcion,'') || ?
            WHERE numero_oc=?
        """, (user, f' [Confirmado por solicitante {user}: {obs}]' if obs else f' [Confirmado por solicitante {user}]', numero_oc))
        # Cerrar items del checklist linkeados (si aplica)
        try:
            c.execute("""
                UPDATE produccion_checklist SET
                  estado='recibido',
                  fecha_recibido=date('now'),
                  actualizado_at=datetime('now')
                WHERE oc_numero=? AND estado IN ('solicitado','en_transito','pendiente')
            """, (numero_oc,))
        except sqlite3.OperationalError:
            pass
        try:
            audit_log(c, usuario=user, accion='MARCAR_RECIBIDO_SOLICITANTE',
                      tabla='ordenes_compra', registro_id=numero_oc,
                      antes={'estado': oc_estado},
                      despues={'estado': 'Recibida', 'recibido_por': user,
                                'observaciones': obs[:300] if obs else None},
                      detalle=f"Solicitante {user} marcó OC {numero_oc} como Recibida (desde SOL {numero})")
        except Exception as e:
            log.warning('audit_log MARCAR_RECIBIDO_SOLICITANTE fallo: %s', e)
    conn.commit()
    return jsonify({
        'ok': True,
        'numero': numero.upper(),
        'numero_oc': numero_oc,
        'mensaje': 'Recepción confirmada. La OC quedó marcada como Recibida.',
    })


@bp.route('/api/solicitudes-compra/<numero>/aprobar-influencer', methods=['POST'])
def aprobar_solicitud_influencer(numero):
    """Aprueba una SOL Pendiente de Influencer/CC, completa el valor, crea
    la OC vinculada y registra en pagos_influencers.

    Sebastian (29-abr-2026): Jefferson crea SOLs desde /solicitudes con
    valor=0 y Pendiente. Este endpoint cierra el ciclo: define el valor,
    auto-aprueba, crea OC y entrada en pagos_influencers — listo para
    pagar desde /compras tab Influencers.

    Body: {valor: 1500000}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin (Sebastian/Alejandro)'}), 403
    d = request.get_json() or {}
    # Money sanity validation · audit zero-error
    monto, err = validate_money(d.get('valor'), allow_zero=False, field_name='valor')
    if err:
        return jsonify(err), 400
    numero = numero.upper()
    conn = get_db(); cur = conn.cursor()
    sol = cur.execute(
        "SELECT estado, categoria, observaciones, numero_oc, influencer_id, solicitante "
        "FROM solicitudes_compra WHERE numero=?", (numero,)
    ).fetchone()
    if not sol:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    sol_estado, categoria, obs_orig, numero_oc_actual, infl_id, solicitante = sol
    cat_low = (categoria or '').lower()
    if not ('influencer' in cat_low or 'cuenta de cobro' in cat_low or 'marketing' in cat_low):
        return jsonify({'error': 'Esta solicitud no es de influencer/CC'}), 400

    # Buscar nombre del beneficiario
    benef_nombre = ''
    if infl_id:
        try:
            r = cur.execute("SELECT nombre FROM marketing_influencers WHERE id=?", (infl_id,)).fetchone()
            if r: benef_nombre = r[0] or ''
        except Exception as _e:
            __import__('logging').getLogger('compras').warning('lookup beneficiario infl_id=%s fallo: %s', infl_id, _e)
    if not benef_nombre and obs_orig:
        m = __import__('re').search(r'BENEFICIARIO:\s*([^|]+)', obs_orig, __import__('re').IGNORECASE)
        if m: benef_nombre = m.group(1).strip()
    if not benef_nombre:
        benef_nombre = solicitante or 'Sin beneficiario'

    # 1. Update SOL: valor + estado=Aprobada
    cur.execute(
        "UPDATE solicitudes_compra SET valor=?, estado='Aprobada', "
        "aprobado_por=?, fecha_aprobacion=datetime('now') WHERE numero=?",
        (monto, user, numero)
    )

    # 2. Crear OC si no existe
    if not numero_oc_actual:
        oc_num = numero.replace('SOL', 'OC')
        # Si ya hay una OC con ese numero (raro pero posible), generar uno con sufijo
        existing_oc = cur.execute(
            "SELECT 1 FROM ordenes_compra WHERE numero_oc=?", (oc_num,)
        ).fetchone()
        if existing_oc:
            from datetime import datetime as _dt
            oc_num = oc_num + '-' + _dt.now().strftime('%H%M%S')
        cur.execute("""
            INSERT INTO ordenes_compra
            (numero_oc, fecha, estado, proveedor, observaciones, creado_por,
             categoria, valor_total)
            VALUES (?, date('now'), 'Aprobada', ?, ?, ?, ?, ?)
        """, (oc_num, benef_nombre, obs_orig or '', user, categoria, monto))
        cur.execute(
            "UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?",
            (oc_num, numero)
        )
    else:
        oc_num = numero_oc_actual
        # Si la OC existe pero estaba en valor 0, actualizarla
        cur.execute(
            "UPDATE ordenes_compra SET valor_total=?, estado='Aprobada', "
            "proveedor=COALESCE(NULLIF(proveedor,''),?) WHERE numero_oc=?",
            (monto, benef_nombre, oc_num)
        )

    # 3. Registrar en pagos_influencers (si no existe ya)
    try:
        existing_pi = cur.execute(
            "SELECT 1 FROM pagos_influencers WHERE numero_oc=?", (oc_num,)
        ).fetchone()
        if not existing_pi:
            cur.execute("""
                INSERT INTO pagos_influencers
                (influencer_id, influencer_nombre, valor, fecha, estado,
                 concepto, numero_oc)
                VALUES (?, ?, ?, date('now'), 'Pendiente', ?, ?)
            """, (infl_id, benef_nombre, int(monto),
                  obs_orig[:200] if obs_orig else 'Cuenta de cobro', oc_num))
    except sqlite3.OperationalError:
        pass  # tabla puede no existir en instancias muy viejas
    try:
        audit_log(cur, usuario=user, accion='APROBAR_SOLICITUD_INFLUENCER',
                  tabla='solicitudes_compra', registro_id=numero,
                  antes={'estado': sol_estado, 'numero_oc': numero_oc_actual},
                  despues={'estado': 'Aprobada', 'valor': monto,
                            'numero_oc': oc_num, 'beneficiario': benef_nombre[:200],
                            'aprobado_por': user},
                  detalle=f"Aprobó solicitud {numero} influencer · OC {oc_num} · "
                          f"beneficiario {benef_nombre[:60]} · ${monto:,.0f}")
    except Exception as e:
        log.warning('audit_log APROBAR_SOLICITUD_INFLUENCER fallo: %s', e)
    conn.commit()
    return jsonify({
        'ok': True,
        'numero': numero,
        'numero_oc': oc_num,
        'valor': monto,
        'mensaje': f'Aprobada — OC {oc_num} creada por ${monto:,.0f}'
    })


@bp.route('/api/solicitudes-compra/<numero>/rechazar', methods=['POST'])
def rechazar_solicitud(numero):
    """Marca una SOL como Rechazada y notifica al solicitante por email.
    Sin tocar OC asociada (si la tiene). Solo admin.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin'}), 403
    d = request.get_json() or {}
    motivo = (d.get('motivo') or '').strip() or 'Sin motivo'
    numero = numero.upper()
    conn = get_db(); cur = conn.cursor()
    sol = cur.execute(
        "SELECT solicitante, email_solicitante, observaciones, categoria "
        "FROM solicitudes_compra WHERE numero=?",
        (numero,)
    ).fetchone()
    if not sol:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    cur.execute(
        "UPDATE solicitudes_compra SET estado='Rechazada', "
        "observaciones=COALESCE(observaciones,'') || ' | RECHAZADA: ' || ? "
        "WHERE numero=?",
        (motivo, numero)
    )
    try:
        audit_log(cur, usuario=user, accion='RECHAZAR_SOLICITUD',
                  tabla='solicitudes_compra', registro_id=numero,
                  antes={'solicitante': sol[0], 'categoria': sol[3]},
                  despues={'estado': 'Rechazada', 'motivo': motivo[:300]},
                  detalle=f"Rechazó solicitud {numero} · motivo: {motivo}")
    except Exception as e:
        log.warning('audit_log RECHAZAR_SOLICITUD fallo: %s', e)
    conn.commit()
    # Notificar al solicitante. Sebastian (29-abr-2026): "cuando doy rechazar
    # en compras a una cuenta de influencer me esta llegando a mi deberia
    # llegarle a jeferson". Para SOLs de Influencer/CC el destinatario SIEMPRE
    # debe ser Jefferson (responsable de marketing) — no el solicitante real
    # que puede haber sido Sebastián cargando bulk.
    try:
        _sol_user = (sol[0] or '').strip().lower()
        _categoria = (sol[3] or '').strip()
        _es_influencer = _categoria in ('Influencer/Marketing Digital', 'Cuenta de Cobro')
        if _es_influencer:
            # Forzar Jefferson como destinatario para SOLs de marketing
            _dest = USER_EMAILS.get('jefferson', '')
            # Fallback solo si Jefferson no está configurado: usar email de la SOL
            if not _dest:
                _dest = (sol[1] or '').strip() or USER_EMAILS.get(_sol_user, '')
        else:
            _dest = (sol[1] or '').strip() or USER_EMAILS.get(_sol_user, '')
        if _dest:
            _asunto = f"❌ Solicitud {numero} rechazada"
            _body = (
                f"<h2>Tu solicitud de pago fue rechazada</h2>"
                f"<p>Solicitud: <b>{numero}</b></p>"
                f"<p>Motivo: <i>{motivo}</i></p>"
                f"<p style='color:#94a3b8;font-size:11px'>Mensaje automatico HHA Group</p>"
            )
            _notificar_solicitante_email(_dest, _asunto, _body)
    except Exception:
        pass
    return jsonify({'ok': True, 'numero': numero, 'estado': 'Rechazada', 'motivo': motivo})


@bp.route('/api/solicitudes-compra/<numero>', methods=['GET'])
def get_solicitud_estado(numero):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,solicitante,urgencia,observaciones,numero_oc FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'No encontrada'}), 404
    cols = ['numero','fecha','estado','solicitante','urgencia','observaciones','numero_oc']
    sol = dict(zip(cols, row))
    # Cargar columnas opcionales (pueden no existir en versiones antiguas
    # de la DB). Whitelist hardcoded — nunca de input — así el f-string es
    # seguro contra SQL injection.
    for col in ['area', 'empresa', 'categoria', 'tipo', 'aprobado_por', 'fecha_aprobacion']:
        try:
            c.execute(f"SELECT {col} FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
            r2 = c.fetchone()
            if r2:
                sol[col] = r2[0]
        except sqlite3.OperationalError as _e:
            # "no such column" es benigno (versión vieja de schema).
            # Otros errores SÍ los logueamos.
            if 'no such column' not in str(_e).lower():
                __import__('logging').getLogger('compras').error(
                    "SELECT %s en solicitudes_compra falló: %s", col, _e
                )
    # IMPORTANTE: incluir id (PK) y campos editables nuevos para que el modal
    # pueda hacer PATCH /api/solicitudes-compra/<numero>/items
    try:
        c.execute("""SELECT id, codigo_mp, nombre_mp, cantidad_g, unidad,
                            COALESCE(valor_estimado, 0),
                            COALESCE(justificacion, ''),
                            COALESCE(precio_unit_g, 0),
                            COALESCE(proveedor_sugerido, '')
                     FROM solicitudes_compra_items WHERE numero=?""",
                  (numero.upper(),))
        items = [
            dict(zip(['id','codigo_mp','nombre_mp','cantidad_g','unidad',
                      'valor_estimado','justificacion',
                      'precio_unit_g','proveedor_sugerido'], r))
            for r in c.fetchall()
        ]
    except sqlite3.OperationalError:
        # Fallback si migration #43 todavia no aplicada
        c.execute("""SELECT id, codigo_mp, nombre_mp, cantidad_g, unidad,
                            COALESCE(valor_estimado, 0),
                            COALESCE(justificacion, '')
                     FROM solicitudes_compra_items WHERE numero=?""",
                  (numero.upper(),))
        items = [
            dict(zip(['id','codigo_mp','nombre_mp','cantidad_g','unidad',
                      'valor_estimado','justificacion'], r))
            for r in c.fetchall()
        ]
        for it in items:
            it['precio_unit_g'] = 0
            it['proveedor_sugerido'] = ''

    # Enriquecer cada item con stock_actual_g (suma de movimientos) +
    # precio_referencia + proveedor de maestro_mps. Para que el modal de
    # solicitud muestre 'Tienes X, faltan Y' y el contexto financiero.
    for it in items:
        cod = (it.get('codigo_mp') or '').strip()
        nombre = (it.get('nombre_mp') or '').strip()
        it['stock_actual_g'] = 0
        if not cod and not nombre:
            continue
        # Estrategia de búsqueda escalonada:
        # 1. material_id exacto con código
        # 2. material_nombre LIKE con nombre (caso-insensitive)
        # Si la primera tiene resultado, no probamos la segunda.
        stock_total = 0
        try:
            if cod:
                r = c.execute("""SELECT
                    COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0),
                    COUNT(*)
                    FROM movimientos WHERE material_id=?""", (cod,)).fetchone()
                if r and r[1] > 0:  # hubo movimientos con ese código
                    stock_total = float(r[0] or 0)
                elif nombre:
                    # Fallback: buscar por nombre exacto upper
                    r2 = c.execute("""SELECT
                        COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0)
                        FROM movimientos
                        WHERE UPPER(TRIM(material_nombre)) = UPPER(TRIM(?))""",
                        (nombre,)).fetchone()
                    stock_total = float(r2[0] or 0) if r2 else 0
            elif nombre:
                r = c.execute("""SELECT
                    COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0)
                    FROM movimientos
                    WHERE UPPER(TRIM(material_nombre)) = UPPER(TRIM(?))""",
                    (nombre,)).fetchone()
                stock_total = float(r[0] or 0) if r else 0
            it['stock_actual_g'] = max(0, stock_total)  # nunca negativo en display
        except sqlite3.OperationalError:
            pass
        try:
            r = c.execute("""SELECT COALESCE(proveedor,''),
                                    COALESCE(precio_referencia,0)
                             FROM maestro_mps WHERE codigo_mp=?""", (cod,)).fetchone()
            if r:
                it['proveedor'] = r[0]
                it['precio_referencia'] = float(r[1] or 0)
                # Si no hay valor estimado pero tenemos precio referencia, calcular
                if not it.get('valor_estimado') and it['precio_referencia'] > 0:
                    cant_g = float(it.get('cantidad_g') or 0)
                    it['valor_estimado_calculado'] = round(cant_g / 1000.0 * it['precio_referencia'], 0)
        except sqlite3.OperationalError:
            pass

    # Datos de la OC asociada (proveedor, valor_total, estado) si existe
    oc_info = None
    if sol.get('numero_oc'):
        try:
            r = c.execute("""SELECT proveedor, COALESCE(valor_total, 0), estado, observaciones
                             FROM ordenes_compra WHERE numero_oc=?""",
                          (sol['numero_oc'],)).fetchone()
            if r:
                oc_info = {
                    'numero_oc': sol['numero_oc'],
                    'proveedor': r[0] or '',
                    'valor_total': float(r[1] or 0),
                    'estado': r[2] or '',
                    'observaciones': r[3] or '',
                }
        except sqlite3.OperationalError:
            pass

    return jsonify({'solicitud': sol, 'items': items, 'oc': oc_info})

@bp.route('/solicitudes')
def solicitudes_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/solicitudes')
    return Response(SOLICITUDES_HTML, mimetype='text/html')

@bp.route('/api/solicitudes-compra/<numero>/estado', methods=['PATCH'])
def actualizar_estado_solicitud(numero):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user_act = session.get('compras_user', '')
    d = request.get_json() or {}
    nuevo = d.get('estado', 'Aprobada')
    numero_oc_param = d.get('numero_oc', '')
    obs = d.get('observaciones', '')
    conn = get_db(); cur = conn.cursor()
    # Capturar antes para audit (estado anterior y SOL existence check)
    antes_row = cur.execute(
        "SELECT estado, numero_oc, categoria FROM solicitudes_compra WHERE numero=?",
        (numero.upper(),)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    antes = {'estado': antes_row[0], 'numero_oc': antes_row[1], 'categoria': antes_row[2]}
    cur.execute("""UPDATE solicitudes_compra SET estado=?, aprobado_por=?, fecha_aprobacion=?
                 WHERE numero=?""",
              (nuevo, user_act, datetime.now().isoformat(), numero.upper()))
    if numero_oc_param:
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (numero_oc_param, numero.upper()))
    if nuevo == 'Rechazada' and obs:
        cur.execute("UPDATE solicitudes_compra SET observaciones=? WHERE numero=?", (obs, numero.upper()))
    try:
        audit_log(cur, usuario=user_act, accion='ACTUALIZAR_ESTADO_SOL',
                  tabla='solicitudes_compra', registro_id=numero.upper(),
                  antes=antes,
                  despues={'estado': nuevo, 'numero_oc': numero_oc_param or antes_row[1],
                            'observaciones': obs[:300] if obs else None,
                            'aprobado_por': user_act},
                  detalle=f"Solicitud {numero.upper()}: {antes['estado']} → {nuevo}")
    except Exception as e:
        log.warning('audit_log ACTUALIZAR_ESTADO_SOL fallo: %s', e)
    conn.commit()
    oc_creada = ''
    if d.get('crear_oc'):
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
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
        proveedor_oc = (d.get('proveedor') or '').strip()
        valor_oc = float(d.get('valor_total') or 0)
        # Sebastian (29-abr-2026): "OC sale Por definir y $0 aunque la
        # solicitud trae 150.000". Si el frontend no manda proveedor/valor,
        # los inferimos desde la solicitud para que la OC no quede vacia.
        if not proveedor_oc or proveedor_oc.lower() == 'por definir':
            try:
                _r = cur.execute(
                    "SELECT influencer_id, solicitante FROM solicitudes_compra WHERE numero=?",
                    (numero.upper(),)
                ).fetchone()
                inf_id = _r[0] if _r else None
                solic_nombre = (_r[1] if _r else '') or ''
                if inf_id:
                    _ri = cur.execute(
                        "SELECT nombre FROM marketing_influencers WHERE id=?", (inf_id,)
                    ).fetchone()
                    if _ri and _ri[0]:
                        proveedor_oc = _ri[0]
                if not proveedor_oc:
                    _rp = cur.execute(
                        "SELECT proveedor_sugerido FROM solicitudes_compra_items "
                        "WHERE numero=? AND COALESCE(proveedor_sugerido,'') != '' LIMIT 1",
                        (numero.upper(),)
                    ).fetchone()
                    if _rp and _rp[0]:
                        proveedor_oc = _rp[0]
                if not proveedor_oc and categoria_oc in ('SVC', 'CC') and solic_nombre:
                    proveedor_oc = solic_nombre
            except Exception:
                pass
        if not proveedor_oc:
            proveedor_oc = 'Por definir'
        if valor_oc <= 0:
            try:
                _r = cur.execute(
                    "SELECT COALESCE(valor,0) FROM solicitudes_compra WHERE numero=?",
                    (numero.upper(),)
                ).fetchone()
                if _r and (_r[0] or 0) > 0:
                    valor_oc = float(_r[0])
                else:
                    _r2 = cur.execute(
                        "SELECT COALESCE(SUM(COALESCE(valor_estimado,0)),0), "
                        "       COALESCE(SUM(COALESCE(precio_unit_g,0)*COALESCE(cantidad_g,0)),0) "
                        "FROM solicitudes_compra_items WHERE numero=?",
                        (numero.upper(),)
                    ).fetchone()
                    if _r2:
                        valor_oc = float(_r2[0] or 0) or float(_r2[1] or 0)
            except Exception:
                pass
        fent_oc = d.get('fecha_entrega_est', '')
        obs_oc = d.get('observaciones_oc') or f'Generado desde {numero.upper()}'
        cur.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) FROM ordenes_compra WHERE numero_oc LIKE ?", (f"OC-{datetime.now().year}-%",))
        n_oc = (cur.fetchone()[0] or 0) + 1
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
    conn.commit()
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
    # Audit zero-error 2-may-2026: RBAC mínimo (era cualquier sesión)
    # Recepción mueve stock e impacta valoración · debe ser Compras/Bodega/Admin
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(COMPRAS_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Compras/Admin pueden registrar recepción'}), 403
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        return jsonify({'error': 'OC no encontrada'}), 404
    if oc_row[0] not in ('Autorizada', 'Parcial'):
        return jsonify({'error': f'OC en estado {oc_row[0]} no permite recepcion'}), 409
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
        # Money sanity validation · audit zero-error 2-may-2026
        # cantidad_recibida puede ser 0 (item rechazado) · allow_zero=True
        cant_raw = ir.get('cantidad_recibida', 0)
        if cant_raw is None or cant_raw == '' or cant_raw == 0:
            cant_recibida = float(cantidad_pedida or 0)
        else:
            cant_validada, err = validate_money(cant_raw, allow_zero=True,
                                                  max_value=10_000_000_000,
                                                  field_name='cantidad_recibida')
            if err:
                return jsonify(err), 400
            cant_recibida = cant_validada
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
                     prov_nombre, operador, lote_num or None, fv or None, 'CUARENTENA', numero_oc))
            ingresos += 1
        # Actualizar item OC · audit zero-error 2-may-2026: usar += en
        # cantidad_recibida_g para soportar recepciones múltiples parciales
        # sobre el mismo item. Antes era SET = ? que pisaba el acumulado.
        try:
            cur.execute(
                "UPDATE ordenes_compra_items "
                "SET cantidad_recibida_g = COALESCE(cantidad_recibida_g, 0) + ?, "
                "    estado_recepcion=?, notas_recepcion=?, "
                "    lote_asignado=COALESCE(lote_asignado, ?) "
                " WHERE numero_oc=? AND codigo_mp=?",
                (cant_recibida, estado_item, notas_item, lote_num, numero_oc, codigo))
        except Exception as e:
            log.warning('UPDATE oci en recibir_oc fallo: %s', e)
    # Estado final de la OC
    nuevo_estado = 'Parcial' if es_parcial else 'Recibida'
    try:
        cur.execute(
            "UPDATE ordenes_compra SET estado=?, fecha_recepcion=?,"
            " observaciones_recepcion=?, tiene_discrepancias=?, recibido_por=? WHERE numero_oc=?",
            (nuevo_estado, fecha, obs_r, disc_r, receptor_nombre, numero_oc))
    except Exception:
        cur.execute("UPDATE ordenes_compra SET estado=?, fecha_recepcion=? WHERE numero_oc=?", (nuevo_estado, fecha, numero_oc))
    # Cierre automatico de cadena: si la OC esta linkeada a items del checklist
    # Pre-Produccion (via produccion_checklist.oc_numero) o solicitudes anticipadas,
    # marcarlos como 'recibido'. Solo cuando recepcion es completa, no parcial.
    items_checklist_actualizados = 0
    if not es_parcial:
        try:
            cur.execute("""
                UPDATE produccion_checklist SET
                  estado='recibido',
                  fecha_recibido=date('now'),
                  actualizado_at=datetime('now')
                WHERE oc_numero=? AND estado IN ('solicitado','en_transito','pendiente')
            """, (numero_oc,))
            items_checklist_actualizados = cur.rowcount or 0
            cur.execute("""
                UPDATE solicitudes_compra_anticipada SET estado='completada'
                WHERE oc_numero=? AND estado IN ('decidida','pendiente')
            """, (numero_oc,))
        except Exception:
            pass
    try:
        audit_log(cur, usuario=operador, accion='RECIBIR_OC',
                  tabla='ordenes_compra', registro_id=numero_oc,
                  despues={'estado': nuevo_estado, 'fecha_recepcion': fecha,
                            'parcial': es_parcial, 'ingresos': ingresos,
                            'tiene_discrepancias': bool(disc_r),
                            'receptor': receptor_nombre[:200],
                            'observaciones_recepcion': (obs_r or '')[:200]},
                  detalle=f"Recibió OC {numero_oc} ({'PARCIAL' if es_parcial else 'COMPLETA'}) "
                          f"· {ingresos} items · receptor {receptor_nombre[:60]}")
    except Exception as e:
        log.warning('audit_log RECIBIR_OC fallo: %s', e)
    conn.commit()
    return jsonify({
        'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos,
        'estado': nuevo_estado, 'parcial': es_parcial,
        'checklist_actualizados': items_checklist_actualizados,
    })

# ============================================================
# Compras — Flujo de autorizacion y pago
# ============================================================

@bp.route('/api/ordenes-compra/<numero_oc>/revisar', methods=['PATCH'])
def revisar_oc(numero_oc):
    # Audit zero-error 2-may-2026: RBAC + bloqueo si OC ya pagada
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(COMPRAS_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Compras/Admin pueden revisar OC'}), 403
    d = request.get_json() or {}
    conn = get_db(); cur = conn.cursor()
    # Bloquear revisión si OC ya pagada o cancelada (volver de Pagada a Revisada
    # creaba inconsistencia auditiva)
    estado_row = cur.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?",
                              (numero_oc,)).fetchone()
    if estado_row and estado_row[0] in ('Pagada', 'Cancelada', 'Rechazada'):
        return jsonify({'error': f'No se puede revisar OC en estado {estado_row[0]}'}), 409
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
    try:
        audit_log(cur, usuario=user, accion='REVISAR_OC',
                  tabla='ordenes_compra', registro_id=numero_oc,
                  antes={'estado': estado_row[0] if estado_row else None},
                  despues={'estado': 'Revisada',
                            'proveedor': d.get('proveedor'),
                            'valor_total': d.get('valor_total'),
                            'con_iva': bool(d.get('con_iva'))},
                  detalle=f"Revisó OC {numero_oc}")
    except Exception as e:
        log.warning('audit_log REVISAR_OC fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'estado': 'Revisada'})

@bp.route('/api/ordenes-compra/<numero_oc>/autorizar', methods=['PATCH'])
def autorizar_oc(numero_oc):
    usuario_actual, err, code = _require_authorize_oc()
    if err:
        return err, code
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT estado, valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado_ant = row[0]
    valor = float(row[1] or 0)
    # Sprint 4: límite de aprobación por usuario
    err_lim, code_lim = _check_monto_limit(usuario_actual, valor)
    if err_lim:
        return err_lim, code_lim
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    cur.execute("SELECT remision_code FROM ordenes_compra WHERE remision_code LIKE ? ORDER BY remision_code DESC LIMIT 1",
                (f'REM-ESP-{fecha_hoy}-%',))
    last = cur.fetchone()
    n = int(last[0].split('-')[-1]) + 1 if last and last[0] else 1
    remision_code = f'REM-ESP-{fecha_hoy}-{n:03d}'
    fecha_aut = datetime.now().isoformat()
    cur.execute("UPDATE ordenes_compra SET estado='Autorizada', remision_code=?, autorizado_por=?, fecha_autorizacion=? WHERE numero_oc=?",
                (remision_code, usuario_actual, fecha_aut, numero_oc))
    # Audit log · autorización es decisión regulatoria/financiera
    try:
        audit_log(cur, usuario=usuario_actual, accion='AUTORIZAR_OC',
                  tabla='ordenes_compra', registro_id=numero_oc,
                  antes={'estado': estado_ant, 'valor_total': valor},
                  despues={'estado': 'Autorizada', 'remision_code': remision_code})
    except Exception as e:
        log.warning('audit_log AUTORIZAR_OC fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'estado': 'Autorizada', 'remision_code': remision_code})

@bp.route('/api/ordenes-compra/<numero_oc>/pagar', methods=['PATCH'])
def pagar_oc(numero_oc):
    """Registra un pago de una OC.

    Mejoras Sprint 2:
      - Soporta pagos PARCIALES: registra cada pago en tabla `pagos_oc`
        (auditoría completa). Estado de la OC se calcula:
          - 'Pagada' si suma pagos >= valor_total
          - 'Parcial' si 0 < suma pagos < valor_total
      - 3-way matching: campo `numero_factura_proveedor` con UNIQUE soft.
        Si la factura ya fue usada en otro pago → 409 Conflict (anti doble pago).
      - Alimenta `precios_mp_historico` por cada item de la OC con el precio
        efectivamente pagado (incluyendo prorrateo si fue parcial).
    """
    usuario_actual, err, code = _require_authorize_oc()
    if err:
        return err, code
    d = request.get_json() or {}
    # Money sanity validation · audit zero-error 2-may-2026
    raw_monto = d.get('monto', 0) or 0
    if raw_monto:
        monto_validado, err = validate_money(raw_monto, allow_zero=False, field_name='monto')
        if err:
            return jsonify(err), 400
        monto = monto_validado
    else:
        monto = 0  # se completará con valor_total_oc después si viene 0
    medio = d.get('medio', 'Transferencia')
    obs = d.get('observaciones', '')
    numero_factura = (d.get('numero_factura_proveedor') or '').strip()
    comprobante_imagen = d.get('comprobante_imagen', '') or ''
    # Toggles fiscales (default OFF, ver Opcion A en SECURITY notes)
    aplicar_retefuente = bool(d.get('aplicar_retefuente', False))
    aplicar_retica = bool(d.get('aplicar_retica', False))
    aplicar_iva = bool(d.get('aplicar_iva', False))
    # Limit image size to ~4MB base64 to avoid DB bloat
    if len(comprobante_imagen) > 4_000_000:
        comprobante_imagen = comprobante_imagen[:4_000_000]
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT estado, categoria, proveedor, valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    estado_oc = row[0] or ''
    categoria = row[1] or 'MP'
    proveedor = row[2] or ''
    valor_total_oc = float(row[3] or 0)
    # Audit zero-error 2-may-2026: respetar LIMITES_APROBACION_OC en pagos
    # Antes _check_monto_limit solo se aplicaba en autorizar_oc · ahora también
    # en pagos (segregation of duties: si Catalina autoriza, otro paga).
    if not monto:
        monto_para_limit = valor_total_oc
    else:
        monto_para_limit = float(monto)
    err_lim, code_lim = _check_monto_limit(usuario_actual, monto_para_limit)
    if err_lim:
        return err_lim, code_lim
    # Audit zero-error 2-may-2026: bloquear pagos sobre OC en estado inválido
    if estado_oc in ('Cancelada', 'Rechazada', 'Borrador'):
        return jsonify({
            'error': f"OC {numero_oc} en estado '{estado_oc}' no admite pagos",
            'codigo': 'ESTADO_INVALIDO'
        }), 409
    if not monto:
        monto = valor_total_oc
    if monto <= 0:
        return jsonify({'error': 'monto debe ser > 0', 'codigo': 'MONTO_INVALIDO'}), 400
    # Audit zero-error 2-may-2026: validar over-payment ANTES de insertar
    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos_oc WHERE numero_oc=?", (numero_oc,))
    total_pagado_actual = float(cur.fetchone()[0] or 0)
    if (total_pagado_actual + monto) > (valor_total_oc + 0.01):
        return jsonify({
            'error': f"Over-payment: pagado actual {total_pagado_actual:.0f} + nuevo {monto:.0f} "
                       f"excede valor OC {valor_total_oc:.0f}",
            'pagado_actual': total_pagado_actual,
            'valor_oc': valor_total_oc,
            'codigo': 'OVER_PAYMENT'
        }), 422
    cat_map = {'MPs':'MPs','MP':'MPs','Envase':'MEE','Insumos':'MEE','MEE':'MEE','SVC':'Servicios','Servicios':'Servicios','Analisis':'Servicios','Ánalisis':'Servicios','Acondicionamiento':'Servicios','Admin':'Administrativo','Nomina':'Administrativo','ADM':'Administrativo','Infraestructura':'Infraestructura','INF':'Infraestructura','CC':'Cuentas de Cobro'}
    cat_egreso = cat_map.get(categoria, 'Compras')
    fecha_pago = datetime.now().isoformat()

    # 3-way matching: validar que la factura no haya sido usada en otro pago
    if numero_factura:
        cur.execute(
            "SELECT numero_oc FROM pagos_oc WHERE numero_factura_proveedor=? LIMIT 1",
            (numero_factura,)
        )
        prev = cur.fetchone()
        if prev and prev[0] != numero_oc:
            return jsonify({
                'error': f"Factura '{numero_factura}' ya fue registrada en pago de OC {prev[0]}",
                'detail': 'Anti doble pago — verifica antes de continuar.',
                'codigo': 'FACTURA_DUPLICADA'
            }), 409

    # Registrar el pago en pagos_oc (auditoría completa)
    try:
        cur.execute("""
            INSERT INTO pagos_oc (numero_oc, monto, medio, fecha_pago,
                                  registrado_por, numero_factura_proveedor,
                                  comprobante_imagen, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (numero_oc, monto, medio, fecha_pago, usuario_actual,
              numero_factura, comprobante_imagen, obs))
    except sqlite3.IntegrityError as _e:
        # UNIQUE de factura disparó (race con check anterior — defense in depth)
        return jsonify({
            'error': 'Factura duplicada en otro pago concurrente',
            'detail': str(_e)[:200],
            'codigo': 'FACTURA_DUPLICADA'
        }), 409

    # Calcular estado actualizado de la OC según la suma de pagos
    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos_oc WHERE numero_oc=?", (numero_oc,))
    total_pagado = float(cur.fetchone()[0] or 0)
    if total_pagado >= valor_total_oc - 0.01:  # tolerance redondeo
        nuevo_estado = 'Pagada'
    else:
        nuevo_estado = 'Parcial'

    cur.execute("""UPDATE ordenes_compra SET estado=?, pagado_por=?, fecha_pago=?,
                       medio_pago=?, comprobante_imagen=?
                   WHERE numero_oc=?""",
                (nuevo_estado, usuario_actual, fecha_pago, medio,
                 comprobante_imagen, numero_oc))
    # Audit log INVIMA · Resolución 2214/2021 · pago de OC es operación financiera regulada
    try:
        audit_log(cur, usuario=usuario_actual, accion='PAGAR_OC',
                  tabla='pagos_oc', registro_id=numero_oc,
                  antes={'estado_oc': estado_oc,
                         'total_pagado_antes': total_pagado_actual},
                  despues={'monto': monto, 'medio': medio,
                           'numero_factura': numero_factura,
                           'estado_nuevo': nuevo_estado,
                           'total_pagado_despues': total_pagado})
    except Exception as e:
        log.warning('audit_log PAGAR_OC fallo: %s · operación NO se aborta (audit es defense-in-depth)', e)
    # Sync solicitudes_compra estado → Pagada so it leaves the pending list.
    # Sebastian (30-abr-2026): bulletproof fix — antes el WHERE filtraba por
    # estado='Aprobada' y si la SOL estaba en otro estado (ej. Pendiente
    # despues de un flujo abortado, o ya Pagada por sync previo) NO se
    # actualizaba y quedaba pegada en la lista. Ahora actualizamos cualquier
    # estado != 'Pagada' al pagar la OC vinculada.
    cur.execute(
        "UPDATE solicitudes_compra SET estado='Pagada' "
        "WHERE numero_oc=? AND estado != 'Pagada'",
        (numero_oc,)
    )
    # Push notif in-app al solicitante (Jefferson en este caso) para que sepa
    # que su pago se procesó. Sebastian (30-abr-2026): "tampoco le estara
    # notificando a el, revisa si pueden llegar a marketing o como seria".
    try:
        sol_notif = cur.execute(
            "SELECT numero, solicitante, valor FROM solicitudes_compra "
            "WHERE numero_oc=? LIMIT 1", (numero_oc,)
        ).fetchone()
        if sol_notif:
            from blueprints.notif import push_notif
            sol_num_n, solicitante_n, valor_n = sol_notif
            destinatario = (solicitante_n or '').lower().strip()
            if destinatario:
                push_notif(
                    destinatario, 'oc_estado',
                    f'✅ Pago procesado: {sol_num_n}',
                    body=f'OC {numero_oc} pagada por ${(valor_n or monto or 0):,.0f} · medio {medio}',
                    link='/marketing',
                    remitente=usuario_actual,
                    importante=True
                )
                # Tambien notif a otros usuarios de marketing para visibilidad
                # (Daniela suele ver, etc) — non-blocking, best effort.
                try:
                    from blueprints.marketing import MARKETING_USERS as _MK
                except Exception:
                    _MK = ()
                for _u in (_MK or ()):
                    if _u.lower() != destinatario:
                        push_notif(_u.lower(), 'oc_estado',
                                   f'💸 Pago procesado a {sol_num_n}',
                                   body=f'OC {numero_oc} pagada · ${(valor_n or monto or 0):,.0f}',
                                   link='/marketing', remitente=usuario_actual)
    except Exception as _e:
        __import__('logging').getLogger('compras').warning(
            'push_notif Pagada SOL fallo OC %s: %s', numero_oc, _e
        )
    # Sync marketing payment status:
    # 1. Si ya existe un row en pagos_influencers para esta OC → marcar Pagada
    #    SIEMPRE (sin importar categoria — la existencia del row es señal
    #    suficiente; el bug previo era que si categoria estaba mal/vacía, no
    #    se actualizaba y quedaba como Pendiente).
    # 2. Si no existe row pero categoria sugiere influencer → crearlo Pagada.
    try:
        cat_low = (categoria or '').lower()
        is_influencer_cat = 'influencer' in cat_low or 'marketing' in cat_low
        existing = cur.execute(
            "SELECT id FROM pagos_influencers WHERE numero_oc=? LIMIT 1",
            (numero_oc,)
        ).fetchone()

        # Recolectar info del influencer para enriquecer (best-effort)
        inf_id = None
        inf_name = proveedor  # fallback
        try:
            sol_row = cur.execute(
                "SELECT influencer_id, solicitante FROM solicitudes_compra WHERE numero_oc=? LIMIT 1",
                (numero_oc,)
            ).fetchone()
            if sol_row:
                inf_id = sol_row[0] if sol_row[0] else None
                if inf_id:
                    inf_row = cur.execute(
                        "SELECT nombre FROM marketing_influencers WHERE id=?", (inf_id,)
                    ).fetchone()
                    if inf_row:
                        inf_name = inf_row[0]
                elif sol_row[1]:
                    inf_name = sol_row[1]  # solicitante name as fallback
        except sqlite3.OperationalError:
            pass  # columnas pueden no existir en instancias viejas

        if existing:
            # Update SIEMPRE: si la fila existe, este pago la marca como Pagada
            cur.execute(
                "UPDATE pagos_influencers SET estado='Pagada', "
                "influencer_id=COALESCE(influencer_id,?), "
                "influencer_nombre=CASE WHEN influencer_nombre IN ('','Pago') "
                "THEN ? ELSE influencer_nombre END "
                "WHERE numero_oc=?",
                (inf_id, inf_name, numero_oc)
            )
        elif is_influencer_cat:
            # No hay fila pero la categoría dice influencer → crear Pagada
            cur.execute("""
                INSERT INTO pagos_influencers
                (influencer_id, influencer_nombre, valor, fecha, estado, concepto, numero_oc)
                VALUES (?,?,?,date('now'),'Pagada',?,?)
            """, (inf_id, inf_name, monto, f'Pago OC {numero_oc}', numero_oc))
    except Exception as _e:
        __import__('logging').getLogger('compras').warning(
            "sync pagos_influencers falló para OC %s: %s", numero_oc, _e
        )
    try:
        # Detectar empresa pagadora con la misma logica multi-señal que usan los
        # comprobantes de egreso. Influencers / marketing / cuenta de cobro →
        # ANIMUS; mercancia/MPs/servicios tecnicos → ESPAGIRIA. Antes estaba
        # hardcoded a 'Espagiria' y por eso pagos a influencers (Ana Sofia,
        # Maria Camila Soto, daisy lopez, etc.) aparecian mal categorizados
        # en el Historial de Egresos del Financiero. Sebastian 2026-04-29.
        empresa_egreso = 'Animus' if _is_animus_payment(
            cur,
            numero_oc=numero_oc,
            beneficiario_nombre=proveedor,
            observaciones=obs,
            categoria=cat_egreso,
        ) else 'Espagiria'
        cur.execute("INSERT INTO flujo_egresos (fecha, empresa, concepto, categoria, monto, periodo, fuente, referencia, creado_por, observaciones) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (fecha_pago, empresa_egreso, f'Pago OC {numero_oc} - {proveedor}',
                    cat_egreso, monto, datetime.now().strftime('%Y-%m'),
                    'compras', numero_oc, usuario_actual, f'{medio}. {obs}'))
    except sqlite3.OperationalError as _e:
        if 'no such table' not in str(_e).lower():
            __import__('logging').getLogger('compras').error(
                "INSERT flujo_egresos falló: %s", _e
            )

    # Alimentar historial de precios (Sprint 2): por cada item de la OC,
    # registrar el precio efectivo en precios_mp_historico. Útil para detectar
    # variaciones de precio en Sprint 4 (reporte ejecutivo).
    try:
        cur.execute("""SELECT codigo_mp, precio_unitario
                       FROM ordenes_compra_items
                       WHERE numero_oc=? AND codigo_mp IS NOT NULL AND codigo_mp != ''""",
                    (numero_oc,))
        items_oc = cur.fetchall()
        for codigo_mp, precio in items_oc:
            if precio and precio > 0:
                cur.execute("""INSERT OR IGNORE INTO precios_mp_historico
                               (codigo_mp, precio_kg, numero_factura, proveedor, fecha)
                               VALUES (?, ?, ?, ?, datetime('now'))""",
                            (codigo_mp, precio, numero_factura, proveedor))
    except sqlite3.OperationalError as _e:
        if 'no such table' not in str(_e).lower():
            __import__('logging').getLogger('compras').error(
                "Alimentar precios_mp_historico falló: %s", _e
            )

    # ── Generar Comprobante de Egreso (CE) — formato fiscal-compatible ─────
    # Para todo pago: genera PDF + guarda en comprobantes_pago. La contadora
    # accede a estos PDFs desde /contabilidad para sus cuentas.
    comprobante_info = None
    try:
        from comprobante_pago import crear_comprobante_y_pdf

        # Recoger último pago_oc_id (el que acabamos de insertar)
        cur.execute("SELECT MAX(id) FROM pagos_oc WHERE numero_oc=?", (numero_oc,))
        pago_oc_id_row = cur.fetchone()
        pago_oc_id = pago_oc_id_row[0] if pago_oc_id_row else None

        # Datos del beneficiario: si es influencer, jalar de marketing_influencers
        beneficiario = {
            'nombre': proveedor, 'cedula': '', 'banco': '',
            'cuenta': '', 'tipo_cuenta': '', 'ciudad': '', 'email': ''
        }
        cat_lower = (categoria or '').lower()
        if 'influencer' in cat_lower or 'marketing' in cat_lower:
            try:
                inf_row = cur.execute("""
                    SELECT mi.nombre, mi.cedula_nit, mi.banco, mi.cuenta_bancaria,
                           mi.tipo_cuenta, mi.ciudad, mi.email
                    FROM solicitudes_compra sc
                    LEFT JOIN marketing_influencers mi ON sc.influencer_id = mi.id
                    WHERE sc.numero_oc=? AND mi.id IS NOT NULL LIMIT 1
                """, (numero_oc,)).fetchone()
                if inf_row:
                    beneficiario = {
                        'nombre': inf_row[0] or proveedor,
                        'cedula': inf_row[1] or '',
                        'banco': inf_row[2] or '',
                        'cuenta': inf_row[3] or '',
                        'tipo_cuenta': inf_row[4] or '',
                        'ciudad': inf_row[5] or '',
                        'email': inf_row[6] or '',
                    }
            except sqlite3.OperationalError:
                pass
        else:
            # Proveedor regular: jalar datos de la tabla proveedores
            try:
                pv = cur.execute(
                    "SELECT contacto, nit, banco, num_cuenta, tipo_cuenta, email FROM proveedores WHERE nombre=? LIMIT 1",
                    (proveedor,)
                ).fetchone()
                if pv:
                    beneficiario.update({
                        'cedula': pv[1] or '', 'banco': pv[2] or '',
                        'cuenta': pv[3] or '', 'tipo_cuenta': pv[4] or '',
                        'email': pv[5] or '',
                    })
            except sqlite3.OperationalError:
                pass

        # Items: descripción consolidada de la OC (1 sola línea para servicios,
        # múltiples para mercancía con codigo_mp).
        try:
            items_db = cur.execute("""
                SELECT nombre_mp, cantidad_g, precio_unitario, subtotal
                FROM ordenes_compra_items WHERE numero_oc=?
            """, (numero_oc,)).fetchall()
        except sqlite3.OperationalError:
            items_db = []

        # Detectar si la OC es de servicio (no mercancia con peso real). Para
        # servicios/donaciones/cuentas de cobro/influencers, los items pueden
        # tener cantidad_g=1 como placeholder y subtotal=monto total — si los
        # tratamos como gramos el PDF muestra cant=0 (1g/1000=0.001 redondeado)
        # y valor_total = unit*0.001 = 1/1000 del valor real (bug Sebastian
        # 29-abr-2026: $1,200,000 aparecía como $1,200 en CE-2026-0008).
        cat_low_pdf = (categoria or '').lower()
        es_servicio_oc = any(k in cat_low_pdf for k in (
            'influencer', 'marketing', 'cuenta de cobro', 'servicio',
            'admin', 'infraestructura', 'cc', 'svc',
        ))
        if items_db and not es_servicio_oc:
            # Mercancia real (MPs, MEE): cantidad_g viene en gramos, subtotal
            # es valor del item completo. Mostrar en kg para legibilidad.
            items_pdf = []
            for r in items_db:
                cant_g = float(r[1] or 0)
                subt = float(r[3] or 0)
                cant_kg = cant_g / 1000.0
                if cant_kg <= 0.01:
                    # Cantidad insignificante → tratar como servicio: cant=1, unit=subtotal
                    items_pdf.append({
                        'descripcion': r[0] or '', 'fecha': '',
                        'cantidad': 1, 'valor_unit': subt,
                    })
                else:
                    p_unit = subt / cant_kg if cant_kg > 0 else 0
                    items_pdf.append({
                        'descripcion': r[0] or '', 'fecha': '',
                        'cantidad': cant_kg, 'valor_unit': p_unit,
                    })
        elif items_db:
            # Servicio CON items registrados (ej. una donacion con descripcion
            # "Donacion") — usar el subtotal directo como valor_unit con cant=1
            items_pdf = [{
                'descripcion': r[0] or f"Pago OC {numero_oc} - {categoria}",
                'fecha': fecha_pago[:10],
                'cantidad': 1,
                'valor_unit': float(r[3] or 0) or monto,
            } for r in items_db]
        else:
            # Servicio sin items detallados: 1 fila generica con el monto total
            items_pdf = [{
                'descripcion': f"Pago OC {numero_oc} - {categoria}",
                'fecha': fecha_pago[:10],
                'cantidad': 1,
                'valor_unit': monto,
            }]

        # Subtotal del comprobante: si aplican retenciones/IVA, el "monto"
        # registrado es el total a pagar; el subtotal_pre se calcula al revés.
        # Para simplicidad: subtotal = monto (el toggle aplica retenciones AL
        # GENERAR el comprobante, no al guardar el pago).
        subtotal_ce = monto
        if aplicar_iva:
            # Si IVA está prendido, asumimos que el "monto" del pago es el
            # subtotal y el IVA se suma — el contador recibe el comprobante
            # con el desglose correcto.
            pass

        # ── OBS string fallback: si aún faltan datos bancarios, parsear OBS ──
        # Ocurre cuando influencer_id era NULL en solicitudes antiguas
        # o cuando el registro en marketing_influencers no tiene banco/cuenta.
        if not beneficiario.get('banco') or not beneficiario.get('cuenta'):
            try:
                from comprobante_pago import parse_obs_beneficiario
                obs_row = cur.execute(
                    "SELECT observaciones FROM solicitudes_compra WHERE numero_oc=? LIMIT 1",
                    (numero_oc,)
                ).fetchone()
                if obs_row and obs_row[0]:
                    parsed = parse_obs_beneficiario(obs_row[0])
                    # Completar solo lo que falta (no pisar datos ya correctos)
                    if not beneficiario.get('banco') and parsed.get('banco'):
                        beneficiario['banco'] = parsed['banco']
                    if not beneficiario.get('tipo_cuenta') and parsed.get('tipo_cuenta'):
                        beneficiario['tipo_cuenta'] = parsed['tipo_cuenta']
                    if not beneficiario.get('cuenta') and parsed.get('cuenta'):
                        beneficiario['cuenta'] = parsed['cuenta']
                    if not beneficiario.get('cedula') and parsed.get('cedula'):
                        beneficiario['cedula'] = parsed['cedula']
                    if not beneficiario.get('nombre') and parsed.get('nombre'):
                        beneficiario['nombre'] = parsed['nombre']
            except Exception as _e_obs:
                __import__('logging').getLogger('compras').warning(
                    "OBS fallback para beneficiario falló: %s", _e_obs
                )

        # Empresa pagadora — detección multi-señal (ver _is_animus_payment).
        #   Influencer/Marketing/Cuenta de Cobro → ANIMUS LAB S.A.S.
        #   Resto (mercancía, MPs, planta, etc.) → ESPAGIRIA LABORATORIO S.A.S.
        obs_for_dispatch = None
        try:
            obs_row = cur.execute(
                "SELECT observaciones FROM solicitudes_compra "
                "WHERE numero_oc=? LIMIT 1", (numero_oc,)
            ).fetchone()
            if obs_row:
                obs_for_dispatch = obs_row[0]
        except sqlite3.OperationalError:
            pass
        if _is_animus_payment(
            cur, numero_oc=numero_oc,
            beneficiario_nombre=beneficiario.get('nombre', ''),
            observaciones=obs_for_dispatch,
            categoria=categoria,
        ):
            empresa_pagadora = 'Animus'
        else:
            empresa_pagadora = 'Espagiria'

        comp = crear_comprobante_y_pdf(
            conn, beneficiario=beneficiario, items=items_pdf,
            monto_subtotal=subtotal_ce,
            aplicar_retefuente=aplicar_retefuente,
            aplicar_retica=aplicar_retica,
            aplicar_iva=aplicar_iva,
            medio_pago=medio, observaciones=obs,
            pagado_por=usuario_actual, numero_oc=numero_oc,
            pago_oc_id=pago_oc_id, empresa=empresa_pagadora,
        )
        comprobante_info = {
            'numero_ce': comp['numero_ce'],
            'comprobante_id': comp['comprobante_id'],
            'subtotal': comp['subtotal'],
            'iva': comp['iva'],
            'retefuente': comp['retefuente'],
            'retica': comp['retica'],
            'total_pagado': comp['total_pagado'],
        }

        # Envío automático del comprobante por email al beneficiario.
        # Solo si: (a) hay email del beneficiario, (b) hay SMTP configurado.
        # Se ejecuta en background — no bloquea la respuesta de pago.
        email_dest = (beneficiario.get('email') or '').strip()
        if email_dest and '@' in email_dest:
            try:
                from notificaciones import SistemaNotificaciones
                sn = SistemaNotificaciones()
                if sn.email_remitente and sn.contraseña:
                    sn.enviar_en_background(
                        sn.enviar_comprobante_egreso,
                        destinatario=email_dest,
                        numero_ce=comp['numero_ce'],
                        beneficiario=beneficiario.get('nombre', ''),
                        total_pagado=comp['total_pagado'],
                        pdf_bytes=comp['pdf_bytes'],
                        fecha_emision=fecha_pago[:10],
                        numero_oc=numero_oc,
                        empresa=empresa_pagadora,
                    )
                    comprobante_info['email_enviado_a'] = email_dest
                else:
                    comprobante_info['email_pendiente'] = (
                        'SMTP no configurado en Render (EMAIL_REMITENTE/EMAIL_PASSWORD)'
                    )
            except Exception as _e_mail:
                __import__('logging').getLogger('compras').error(
                    "Email comprobante falló: %s", _e_mail
                )
        else:
            comprobante_info['email_pendiente'] = (
                'Beneficiario sin email — agrégalo en Marketing › Influencers'
            )
    except Exception as _e:
        __import__('logging').getLogger('compras').error(
            "No se pudo generar comprobante de egreso: %s", _e, exc_info=True
        )

    conn.commit()

    # ── Notificar al solicitante (Jefferson) cuando es OC influencer/CC ────
    # Sebastian (29-abr-2026): "le notificaba a jefer" — restaurar el ping
    # por email al solicitante cuando se le paga a uno de sus influencers.
    # Solo notifica cuando la OC pasa a Pagada (no Parcial).
    try:
        cat_low_n = (categoria or '').lower()
        es_influencer_oc = (
            'influencer' in cat_low_n
            or 'cuenta de cobro' in cat_low_n
            or 'marketing' in cat_low_n
        )
        if es_influencer_oc and nuevo_estado == 'Pagada':
            # Sebastian (29-abr-2026): "deberia llegarle a jeferson" no a quien
            # creó la SOL (puede haber sido Sebastian cargando bulk). Para OCs
            # de Influencer/CC el destinatario SIEMPRE es Jefferson.
            _dest = USER_EMAILS.get('jefferson', '')
            # Fallback: si Jefferson no está configurado, usar el solicitante
            # original (mejor algo que nada).
            if not _dest:
                sol_info = cur.execute(
                    "SELECT solicitante, email_solicitante FROM solicitudes_compra "
                    "WHERE numero_oc=? LIMIT 1", (numero_oc,)
                ).fetchone()
                if sol_info:
                    _sol_user = (sol_info[0] or '').strip().lower()
                    _dest = (sol_info[1] or '').strip() or USER_EMAILS.get(_sol_user, '')
            if _dest:
                _asunto = f"💸 Pago confirmado a {proveedor} — {numero_oc}"
                _body = (
                    f"<h2>Pago confirmado</h2>"
                    f"<p>Sebastian autorizó y registró el pago a <b>{proveedor}</b>:</p>"
                    f"<ul>"
                    f"<li><b>OC:</b> {numero_oc}</li>"
                    f"<li><b>Monto:</b> ${monto:,.0f} COP</li>"
                    f"<li><b>Medio:</b> {medio}</li>"
                    f"<li><b>Fecha:</b> {fecha_pago[:10]}</li>"
                    f"</ul>"
                    f"<p>El estado en Marketing → Influencers cambió a <b>Pagada</b>. "
                    f"El comprobante de egreso (CE) se adjuntó al beneficiario si tenía email.</p>"
                    f"<p style='color:#94a3b8;font-size:11px'>Mensaje automatico HHA Group</p>"
                )
                _notificar_solicitante_email(_dest, _asunto, _body)
    except Exception as _e_notif:
        __import__('logging').getLogger('compras').error(
            "Notificacion a Jefferson fallo (no critico): %s", _e_notif
        )

    return jsonify({
        'ok': True,
        'estado': nuevo_estado,
        'monto_este_pago': monto,
        'total_pagado_acumulado': round(total_pagado, 2),
        'valor_total_oc': round(valor_total_oc, 2),
        'pendiente': round(max(0, valor_total_oc - total_pagado), 2),
        'comprobante': comprobante_info,
    })


# ─── Endpoints comprobantes de egreso ────────────────────────────────────────


@bp.route('/api/comprobantes-pago', methods=['GET'])
def listar_comprobantes_pago():
    """Lista los comprobantes de egreso generados.

    Query: ?desde=&hasta=&beneficiario=  (filtros opcionales)
    """
    u, err, code = _require_compras_session()
    if err:
        return err, code
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    benef = (request.args.get('beneficiario') or '').strip()

    conn = get_db(); c = conn.cursor()
    sql = """
        SELECT id, numero_ce, fecha_emision, numero_oc, beneficiario_nombre,
               beneficiario_cedula, subtotal, iva, retefuente, retica,
               total_pagado, medio_pago, pagado_por, empresa
        FROM comprobantes_pago
        WHERE 1=1
    """
    params = []
    if desde:
        sql += " AND fecha_emision >= ?"; params.append(desde)
    if hasta:
        sql += " AND fecha_emision <= ?"; params.append(hasta + ' 23:59:59')
    if benef:
        sql += " AND beneficiario_nombre LIKE ?"; params.append(f"%{benef}%")
    sql += " ORDER BY fecha_emision DESC LIMIT 500"
    c.execute(sql, params)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'comprobantes': rows, 'count': len(rows)})


@bp.route('/api/comprobantes-pago/<int:comp_id>/pdf', methods=['GET'])
def descargar_comprobante_pdf(comp_id):
    """Descarga el PDF del comprobante."""
    u, err, code = _require_compras_session()
    if err:
        return err, code
    import base64
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT numero_ce, pdf_archivo FROM comprobantes_pago WHERE id=?", (comp_id,))
    row = c.fetchone()
    if not row or not row[1]:
        return jsonify({'error': 'Comprobante no encontrado'}), 404
    numero_ce, pdf_b64 = row[0], row[1]
    try:
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception:
        return jsonify({'error': 'PDF corrupto'}), 500
    return Response(
        pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{numero_ce}.pdf"'}
    )


def _regenerate_ce_internal(conn, c, comp_id, forzar_obs=False,
                            empresa_override=None):
    """Helper interno: regenera el PDF + actualiza DB de un comprobante.

    Centraliza la logica para ser invocada tanto desde:
      - POST /api/comprobantes-pago/<id>/regenerar (single, via UI)
      - POST /api/comprobantes-pago/regenerar-legacy (bulk admin)

    Args:
      conn, c: conexion + cursor de SQLite (se hace commit al final)
      comp_id: id del comprobantes_pago row
      forzar_obs: si True, fuerza re-parseo de OBS aunque ya tenga banco
      empresa_override: si no None, fuerza la empresa (skip multi-signal)

    Returns dict:
      {ok: True, numero_ce, empresa, beneficiario, subtotal_usado, pdf_size_kb}
      {ok: False, error}
    """
    c.execute("""
        SELECT id, numero_ce, numero_oc, beneficiario_nombre, beneficiario_cedula,
               beneficiario_banco, beneficiario_cuenta, beneficiario_tipo_cta,
               beneficiario_ciudad, subtotal, iva_pct, retefuente_pct, retica_pct,
               medio_pago, observaciones, pagado_por, empresa, pdf_archivo,
               fecha_emision
        FROM comprobantes_pago WHERE id=?
    """, (comp_id,))
    row = c.fetchone()
    if not row:
        return {'ok': False, 'error': 'Comprobante no encontrado'}

    (_, numero_ce, numero_oc, ben_nombre, ben_cedula, ben_banco, ben_cuenta,
     ben_tipo_cta, ben_ciudad, subtotal, iva_pct, rete_pct, retica_pct,
     medio_pago, observaciones, pagado_por, empresa_db, _, fecha_emision_str) = row

    # ── Empresa: usa override del caller, sino re-deriva multi-señal ──
    # _is_animus_payment cubre CEs legacy donde 'empresa_db' quedó en
    # 'Espagiria' por default histórico aunque era pago de influencer.
    if empresa_override is not None:
        empresa = empresa_override
    else:
        oc_row = c.execute(
            "SELECT categoria FROM ordenes_compra WHERE numero_oc=?",
            (numero_oc,)
        ).fetchone()
        cat = (oc_row[0] if oc_row else '') or ''
        if _is_animus_payment(
            c, numero_oc=numero_oc,
            beneficiario_nombre=ben_nombre,
            observaciones=observaciones,
            categoria=cat,
        ):
            empresa = 'Animus'
        else:
            empresa = empresa_db or 'Espagiria'

    # ── Beneficiario base ──
    beneficiario = {
        'nombre': ben_nombre or '',
        'cedula': ben_cedula or '',
        'banco': ben_banco or '',
        'cuenta': ben_cuenta or '',
        'tipo_cuenta': ben_tipo_cta or '',
        'ciudad': ben_ciudad or '',
        'email': '',
    }

    # ── Re-lookup desde marketing_influencers (autoritativo si es influencer) ──
    # Para Animus/Influencer pagos, los datos en marketing_influencers son
    # la fuente de verdad: nombre + cédula + banco + cuenta + tipo + ciudad +
    # email. Antes solo se completaba el email; ahora completamos todo lo
    # que esté vacío en el beneficiario, usando el nombre como key de match.
    es_influencer = (empresa or '').lower() == 'animus' or 'influencer' in (empresa or '').lower()
    if es_influencer or forzar_obs:
        try:
            mi = c.execute("""
                SELECT nombre, cedula_nit, banco, cuenta_bancaria,
                       tipo_cuenta, ciudad, email
                FROM marketing_influencers
                WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?)) LIMIT 1
            """, (beneficiario['nombre'],)).fetchone()
            if mi:
                # Completar campos vacíos (forzar_obs sobrescribe siempre)
                pairs = [
                    ('cedula', mi[1]), ('banco', mi[2]), ('cuenta', mi[3]),
                    ('tipo_cuenta', mi[4]), ('ciudad', mi[5]), ('email', mi[6]),
                ]
                for key, val in pairs:
                    if val and (forzar_obs or not beneficiario.get(key)):
                        beneficiario[key] = val
        except Exception:
            pass

    # ── Si aún faltan datos bancarios O forzar_obs: parsear OBS del comprobante ──
    if forzar_obs or not beneficiario['banco'] or not beneficiario['cuenta']:
        from comprobante_pago import parse_obs_beneficiario
        obs_src = observaciones  # OBS guardado en comprobante
        if not obs_src and numero_oc:
            obs_row = c.execute(
                "SELECT observaciones FROM solicitudes_compra WHERE numero_oc=? LIMIT 1",
                (numero_oc,)
            ).fetchone()
            if obs_row:
                obs_src = obs_row[0] or ''
        if obs_src:
            parsed = parse_obs_beneficiario(obs_src)
            if forzar_obs or not beneficiario['banco']:
                beneficiario['banco'] = parsed.get('banco') or beneficiario['banco']
                beneficiario['tipo_cuenta'] = parsed.get('tipo_cuenta') or beneficiario['tipo_cuenta']
            if forzar_obs or not beneficiario['cuenta']:
                beneficiario['cuenta'] = parsed.get('cuenta') or beneficiario['cuenta']
            if forzar_obs or not beneficiario['cedula']:
                beneficiario['cedula'] = parsed.get('cedula') or beneficiario['cedula']

    # ── Valor: re-leer del comprobante (subtotal ya almacenado) ──
    # Si el subtotal almacenado parece incorrecto (< 10000 para pesos COP),
    # intentar recuperarlo de la OC.
    monto = subtotal or 0
    if monto < 1000 and numero_oc:
        oc_val = c.execute(
            "SELECT valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)
        ).fetchone()
        if oc_val and oc_val[0] and float(oc_val[0]) > monto:
            monto = float(oc_val[0])
            __import__('logging').getLogger('compras').warning(
                "regenerar CE %s: subtotal almacenado=%s parece incorrecto, "
                "usando valor_total OC=%s", numero_ce, subtotal, monto
            )

    # ── Reconstruir items ──
    items_pdf = [{'descripcion': observaciones or f'Pago {numero_oc}',
                  'cantidad': 1, 'valor_unit': monto}]

    # ── Re-generar PDF ──
    from comprobante_pago import generar_comprobante_egreso_pdf
    import base64
    from datetime import datetime as _dt

    try:
        fecha_pago = _dt.fromisoformat(fecha_emision_str.replace('Z', '')) if fecha_emision_str else _dt.now()
    except Exception:
        fecha_pago = _dt.now()

    pdf_bytes = generar_comprobante_egreso_pdf(
        numero_ce=numero_ce,
        fecha_pago=fecha_pago,
        beneficiario=beneficiario,
        items=items_pdf,
        aplicar_retefuente=(rete_pct or 0) > 0,
        aplicar_retica=(retica_pct or 0) > 0,
        aplicar_iva=(iva_pct or 0) > 0,
        medio_pago=medio_pago or 'Transferencia',
        observaciones='',
        pagado_por=pagado_por or '',
        empresa_clave=empresa.lower(),
    )
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    # ── Actualizar DB ── (incluye ciudad, antes faltaba y quedaba NULL)
    c.execute("""
        UPDATE comprobantes_pago
        SET pdf_archivo=?, empresa=?,
            beneficiario_banco=?, beneficiario_cuenta=?,
            beneficiario_tipo_cta=?, beneficiario_cedula=?,
            beneficiario_ciudad=?
        WHERE id=?
    """, (
        pdf_b64, empresa,
        beneficiario['banco'], beneficiario['cuenta'],
        beneficiario['tipo_cuenta'], beneficiario['cedula'],
        beneficiario.get('ciudad') or '',
        comp_id,
    ))
    conn.commit()

    return {
        'ok': True,
        'numero_ce': numero_ce,
        'empresa': empresa,
        'beneficiario': {k: v for k, v in beneficiario.items() if k != 'email'},
        'subtotal_usado': monto,
        'pdf_size_kb': round(len(pdf_bytes) / 1024, 1),
    }


@bp.route('/api/comprobantes-pago/<int:comp_id>/regenerar', methods=['POST'])
def regenerar_comprobante_pdf(comp_id):
    """Re-genera el PDF de un comprobante existente con datos actualizados.

    Útil para corregir comprobantes generados antes de que se implementara:
      - Dispatch correcto empresa (Espagiria vs ANIMUS Lab)
      - Parseo OBS para datos bancarios
      - Formateo correcto de montos COP

    Body JSON (todos opcionales — si no se pasan, se re-derivan de la DB):
      empresa: "Animus" | "Espagiria"
      forzar_obs: true  — fuerza re-parseo OBS aunque ya haya banco en DB
    """
    d = request.get_json(silent=True) or {}
    forzar_obs = bool(d.get('forzar_obs', False))
    empresa_override = d.get('empresa') if 'empresa' in d else None

    conn = get_db(); c = conn.cursor()
    result = _regenerate_ce_internal(
        conn, c, comp_id,
        forzar_obs=forzar_obs,
        empresa_override=empresa_override,
    )
    if not result.get('ok'):
        return jsonify(result), 404
    return jsonify(result)


@bp.route('/api/comprobantes-pago/regenerar-legacy', methods=['POST'])
def regenerar_comprobantes_legacy():
    """Bulk-regenera CEs con dispatch Animus/Espagiria incorrecto.

    Detecta CEs marcados como 'Espagiria' que en realidad eran pagos a
    influencer (multi-señal _is_animus_payment) y regenera todos los
    PDFs con la empresa correcta (ANIMUS LAB).

    Util para corregir CEs creados antes del feature de 2 empresas
    pagadoras (commit 19443c9). Antes el flujo era: usuario va al
    modulo /marketing y hace clic en 'Regenerar' uno por uno; con este
    endpoint admin lo hace de un golpe.

    Body JSON (opcional):
      dry_run: bool (default false) — solo lista candidatos, no toca

    Solo admins. Audita en security_events cada CE corregido.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({
            'error': 'Solo administradores pueden bulk-regenerar comprobantes'
        }), 403

    d = request.get_json(silent=True) or {}
    dry_run = bool(d.get('dry_run', False))

    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, numero_ce, numero_oc, beneficiario_nombre, observaciones
        FROM comprobantes_pago
        WHERE LOWER(COALESCE(empresa,'')) != 'animus'
        ORDER BY id ASC
    """).fetchall()

    candidatos = []
    for cid, ce, oc, ben_nom, obs in rows:
        cat = ''
        if oc:
            oc_row = c.execute(
                "SELECT categoria FROM ordenes_compra WHERE numero_oc=?",
                (oc,)
            ).fetchone()
            cat = (oc_row[0] if oc_row else '') or ''
        if _is_animus_payment(
            c, numero_oc=oc, beneficiario_nombre=ben_nom,
            observaciones=obs, categoria=cat,
        ):
            candidatos.append({
                'id': cid, 'numero_ce': ce, 'numero_oc': oc or '',
                'beneficiario': ben_nom or '',
            })

    if dry_run:
        return jsonify({
            'ok': True, 'dry_run': True,
            'candidatos': candidatos,
            'count': len(candidatos),
        })

    fixed = []
    errors = []
    for cand in candidatos:
        try:
            result = _regenerate_ce_internal(
                conn, c, cand['id'],
                forzar_obs=False,
                empresa_override='Animus',
            )
            if result.get('ok'):
                fixed.append({
                    'id': cand['id'],
                    'numero_ce': cand['numero_ce'],
                    'pdf_size_kb': result.get('pdf_size_kb'),
                })
            else:
                errors.append({
                    'id': cand['id'],
                    'numero_ce': cand['numero_ce'],
                    'error': result.get('error', 'unknown'),
                })
        except Exception as _e:
            errors.append({
                'id': cand['id'],
                'numero_ce': cand['numero_ce'],
                'error': str(_e),
            })

    return jsonify({
        'ok': True, 'dry_run': False,
        'corregidos': fixed,
        'errores': errors,
        'count_corregidos': len(fixed),
        'count_errores': len(errors),
    })


@bp.route('/api/comprobantes-pago/<int:comp_id>/email', methods=['POST'])
def reenviar_comprobante_email(comp_id):
    """Reenvía el comprobante PDF por email.

    Body opcional: {"destinatario": "otro@correo.com"}
    Si no se especifica destinatario, busca el email del beneficiario en
    marketing_influencers o proveedores.
    """
    u, err, code = _require_compras_session()
    if err:
        return err, code
    import base64
    body = request.get_json(silent=True) or {}
    destinatario_override = (body.get('destinatario') or '').strip()

    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT numero_ce, pdf_archivo, beneficiario_nombre,
                        total_pagado, fecha_emision, numero_oc, empresa
                 FROM comprobantes_pago WHERE id=?""", (comp_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Comprobante no encontrado'}), 404
    numero_ce, pdf_b64, benef_nombre, total, fecha_em, num_oc, empresa = row
    if not pdf_b64:
        return jsonify({'error': 'PDF no disponible para este comprobante'}), 404

    # Resolver destinatario: override > marketing_influencers > proveedores
    destinatario = destinatario_override
    if not destinatario and benef_nombre:
        try:
            r2 = c.execute(
                "SELECT email FROM marketing_influencers WHERE LOWER(TRIM(nombre))=? LIMIT 1",
                (benef_nombre.strip().lower(),)
            ).fetchone()
            if r2 and r2[0]:
                destinatario = r2[0].strip()
        except sqlite3.OperationalError:
            pass
    if not destinatario and benef_nombre:
        try:
            r3 = c.execute(
                "SELECT email FROM proveedores WHERE LOWER(TRIM(nombre))=? LIMIT 1",
                (benef_nombre.strip().lower(),)
            ).fetchone()
            if r3 and r3[0]:
                destinatario = r3[0].strip()
        except sqlite3.OperationalError:
            pass

    if not destinatario or '@' not in destinatario:
        return jsonify({
            'error': 'Sin destinatario',
            'detalle': 'No se encontró email para el beneficiario. Pasa "destinatario" en el body o agrega el email al influencer/proveedor.'
        }), 400

    try:
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception:
        return jsonify({'error': 'PDF corrupto'}), 500

    try:
        from notificaciones import SistemaNotificaciones
        sn = SistemaNotificaciones()
        if not sn.email_remitente or not sn.contraseña:
            return jsonify({
                'error': 'SMTP no configurado',
                'detalle': 'Define EMAIL_REMITENTE y EMAIL_PASSWORD en Render → Environment.',
                'doc': 'https://myaccount.google.com/apppasswords (App Password de Gmail)'
            }), 503
        ok = sn.enviar_comprobante_egreso(
            destinatario=destinatario, numero_ce=numero_ce,
            beneficiario=benef_nombre or '', total_pagado=total or 0,
            pdf_bytes=pdf_bytes,
            fecha_emision=(fecha_em or '')[:10], numero_oc=num_oc or '',
            empresa=empresa or 'Espagiria',
        )
        if not ok:
            return jsonify({'error': 'Falló envío SMTP', 'detalle': 'Revisa logs y credenciales SMTP'}), 502
        return jsonify({'ok': True, 'destinatario': destinatario, 'numero_ce': numero_ce})
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@bp.route('/api/comprobantes-pago/oc/<numero_oc>', methods=['GET'])
def comprobantes_de_oc(numero_oc):
    """Lista comprobantes asociados a una OC específica."""
    u, err, code = _require_compras_session()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, numero_ce, fecha_emision, total_pagado, medio_pago,
                        pagado_por, beneficiario_nombre
                 FROM comprobantes_pago WHERE numero_oc=?
                 ORDER BY fecha_emision DESC""", (numero_oc,))
    cols = [d[0] for d in c.description]
    return jsonify({'comprobantes': [dict(zip(cols, r)) for r in c.fetchall()]})


@bp.route('/api/ordenes-compra/<numero_oc>/pagos', methods=['GET'])
def get_pagos_oc(numero_oc):
    """Histórico de pagos de UNA OC específica (Sprint 2).

    Útil para auditar pagos parciales o ver el detalle de quién pagó qué cuándo.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        SELECT id, monto, medio, fecha_pago, registrado_por,
               numero_factura_proveedor, observaciones,
               CASE WHEN comprobante_imagen != '' AND comprobante_imagen IS NOT NULL
                    THEN 1 ELSE 0 END as tiene_comprobante
        FROM pagos_oc WHERE numero_oc=?
        ORDER BY fecha_pago ASC
    """, (numero_oc,))
    cols = [d[0] for d in cur.description]
    pagos = [dict(zip(cols, row)) for row in cur.fetchall()]

    # Total + comparación con valor_total OC
    cur.execute("SELECT valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    valor_oc = float(row[0]) if row else 0
    total_pagado = sum(p.get('monto', 0) or 0 for p in pagos)

    return jsonify({
        'numero_oc': numero_oc,
        'pagos': pagos,
        'count': len(pagos),
        'total_pagado': round(total_pagado, 2),
        'valor_total_oc': round(valor_oc, 2),
        'pendiente': round(max(0, valor_oc - total_pagado), 2),
    })


@bp.route('/api/compras/pagos', methods=['GET'])
def get_pagos():
    """Return all paid OCs with payment metadata (no image data).

    Sebastian (29-abr-2026): "no salen los que he pagado". Antes excluiamos
    influencers/CC del listado pero rompia la visibilidad de los pagos hechos
    por Sebastian a influencers desde /compras tab Influencers. Ahora SI los
    devolvemos pero marcados con `es_influencer: true` para que el frontend
    los pueda destacar visualmente o filtrar.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.categoria, oc.valor_total,
               oc.medio_pago, oc.fecha_pago, oc.pagado_por, oc.estado,
               oc.observaciones,
               CASE WHEN oc.comprobante_imagen != '' AND oc.comprobante_imagen IS NOT NULL
                    THEN 1 ELSE 0 END as tiene_comprobante,
               COALESCE((SELECT SUM(monto) FROM pagos_oc WHERE numero_oc=oc.numero_oc), 0) as monto,
               oc.valor_total -
                 COALESCE((SELECT SUM(monto) FROM pagos_oc WHERE numero_oc=oc.numero_oc), 0)
                 as saldo_pendiente,
               CASE WHEN oc.categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')
                    OR EXISTS(SELECT 1 FROM pagos_influencers pi WHERE pi.numero_oc=oc.numero_oc)
                    OR EXISTS(SELECT 1 FROM solicitudes_compra sc
                              WHERE sc.numero_oc=oc.numero_oc AND sc.influencer_id IS NOT NULL)
                    THEN 1 ELSE 0 END as es_influencer
        FROM ordenes_compra oc
        WHERE oc.estado IN ('Pagada','Parcial')
        ORDER BY oc.fecha_pago DESC
        LIMIT 500
    """)
    cols = [d[0] for d in cur.description]
    pagos = [dict(zip(cols, row)) for row in cur.fetchall()]
    # Convertir es_influencer a bool para JSON
    for p in pagos:
        p['es_influencer'] = bool(p.get('es_influencer'))
    return jsonify({'pagos': pagos})


# ── Categorías que NO requieren recepción física: van directo a "por pagar" ──
# El contador ve estos como pagos directos (servicios, no mercancía).
# NOTA: 'Influencer/Marketing Digital' NO va aquí — Marketing tiene su propio
# panel para pagar influencers y no debe aparecer en /compras.
CATEGORIAS_PAGO_DIRECTO = (
    'Cuenta de Cobro',
    'Servicio',
    'SVC',
)


def _autorreparar_ocs_vacias(cur):
    """Sebastian (29-abr-2026): rellena proveedor / valor_total de OCs
    en estado pre-pago que quedaron sin datos al crearlas (caso 0119).
    Solo toca OCs NO pagadas con proveedor 'Por definir'/vacio o valor<=0
    Y que tengan solicitud asociada con datos. Devuelve lista de OCs
    reparadas. Pensado para correr al cargar /por-pagar y al iniciar
    Dashboard — idempotente.
    """
    reparadas = []
    rows = cur.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.valor_total, oc.categoria,
               s.numero, s.influencer_id, COALESCE(s.valor,0), s.solicitante
        FROM ordenes_compra oc
        LEFT JOIN solicitudes_compra s ON s.numero_oc = oc.numero_oc
        WHERE oc.estado NOT IN ('Pagada','Rechazada','Cancelada')
          AND (
                COALESCE(oc.proveedor,'') = ''
             OR LOWER(oc.proveedor) = 'por definir'
             OR COALESCE(oc.valor_total,0) <= 0
          )
          AND s.numero IS NOT NULL
    """).fetchall()
    for r in rows:
        oc_num, prov_act, val_act, cat_oc, sol_num, inf_id, sol_valor, solic = r
        prov_act = (prov_act or '').strip()
        nuevo_prov = prov_act
        nuevo_val = float(val_act or 0)
        # PROVEEDOR fallback
        if not nuevo_prov or nuevo_prov.lower() == 'por definir':
            if inf_id:
                _ri = cur.execute(
                    "SELECT nombre FROM marketing_influencers WHERE id=?",
                    (inf_id,)
                ).fetchone()
                if _ri and _ri[0]:
                    nuevo_prov = _ri[0]
            if not nuevo_prov or nuevo_prov.lower() == 'por definir':
                _rp = cur.execute(
                    "SELECT proveedor_sugerido FROM solicitudes_compra_items "
                    "WHERE numero=? AND COALESCE(proveedor_sugerido,'') != '' LIMIT 1",
                    (sol_num,)
                ).fetchone()
                if _rp and _rp[0]:
                    nuevo_prov = _rp[0]
            if (not nuevo_prov or nuevo_prov.lower() == 'por definir') \
               and (cat_oc or '') in ('SVC', 'CC') and solic:
                nuevo_prov = solic
        # VALOR fallback
        if nuevo_val <= 0:
            if (sol_valor or 0) > 0:
                nuevo_val = float(sol_valor)
            else:
                _r2 = cur.execute(
                    "SELECT COALESCE(SUM(COALESCE(valor_estimado,0)),0), "
                    "       COALESCE(SUM(COALESCE(precio_unit_g,0)*COALESCE(cantidad_g,0)),0) "
                    "FROM solicitudes_compra_items WHERE numero=?",
                    (sol_num,)
                ).fetchone()
                if _r2:
                    nuevo_val = float(_r2[0] or 0) or float(_r2[1] or 0)
        # Solo update si hay un cambio real
        cambios = []
        params = []
        if nuevo_prov and nuevo_prov != prov_act:
            cambios.append("proveedor=?")
            params.append(nuevo_prov)
        if nuevo_val > 0 and nuevo_val != float(val_act or 0):
            cambios.append("valor_total=?")
            params.append(nuevo_val)
        if cambios:
            params.append(oc_num)
            cur.execute(
                f"UPDATE ordenes_compra SET {', '.join(cambios)} WHERE numero_oc=?",
                params
            )
            reparadas.append(oc_num)
    return reparadas


@bp.route('/api/compras/oc/<numero_oc>/reparar-desde-solicitud', methods=['POST'])
def reparar_oc_desde_solicitud(numero_oc):
    """Repara una OC individual jalando datos de la solicitud asociada.
    Util cuando el usuario ve una OC con 'Por definir / $0' y quiere
    forzar la sincronizacion."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'OC no existe'}), 404
    # Reusar el helper restringiendo el WHERE a esta OC
    rows = cur.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.valor_total, oc.categoria,
               s.numero, s.influencer_id, COALESCE(s.valor,0), s.solicitante
        FROM ordenes_compra oc
        LEFT JOIN solicitudes_compra s ON s.numero_oc = oc.numero_oc
        WHERE oc.numero_oc=?
    """, (numero_oc,)).fetchone()
    if not rows or not rows[4]:
        return jsonify({'error': 'OC sin solicitud asociada — no hay de donde jalar'}), 409
    # Llamar al helper solo para esta OC
    class _CurFilter:
        def __init__(self, real_cur):
            self.real_cur = real_cur
        def execute(self, sql, params=()):
            # Inyectar filtro por numero_oc al SELECT principal
            if 'oc.numero_oc, oc.proveedor, oc.valor_total' in sql and 'WHERE' in sql and 'numero_oc' not in sql.split('WHERE',1)[1]:
                sql = sql.rstrip().rstrip(';') + " AND oc.numero_oc=?"
                params = list(params) + [numero_oc]
            return self.real_cur.execute(sql, params)
    # Mas simple: llamar normal y verificar si reparo esta OC
    reparadas = _autorreparar_ocs_vacias(cur)
    conn.commit()
    if numero_oc in reparadas:
        return jsonify({'ok': True, 'reparada': True, 'numero_oc': numero_oc})
    # No habia nada que reparar (ya esta completa) o no hay datos en la sol
    actual = cur.execute(
        "SELECT proveedor, valor_total FROM ordenes_compra WHERE numero_oc=?",
        (numero_oc,)
    ).fetchone()
    return jsonify({
        'ok': True, 'reparada': False, 'numero_oc': numero_oc,
        'proveedor': actual[0], 'valor_total': actual[1],
        'mensaje': 'Sin cambios — la OC ya tiene datos o la solicitud tampoco los tiene.'
    })


@bp.route('/api/compras/por-pagar', methods=['GET'])
def get_por_pagar():
    """Vista unificada del contador: TODO lo que está pendiente de pago.

    Incluye:
      - OCs con estado 'Recibida' o 'Parcial' (mercancía física recibida)
      - OCs con estado 'Aprobada'/'Autorizada' Y categoría de servicio
        (Influencer, Cuenta de Cobro, etc.) — NO requieren recepción

    Cada item lleva flag `pago_directo: true` si es servicio sin mercancía.
    El frontend puede mostrarlos en una sección destacada.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    conn = get_db(); cur = conn.cursor()

    # Sebastian (29-abr-2026): "OC-2026-0119 sale Por definir y $0 aunque
    # la solicitud trae 150.000". Auto-reparacion silenciosa al cargar el
    # tab: rellena proveedor/valor de OCs en estado pre-pago tomando los
    # datos de la solicitud asociada. No-op si ya estan completos.
    try:
        _reparadas = _autorreparar_ocs_vacias(cur)
        if _reparadas:
            conn.commit()
    except Exception:
        pass

    # Mercancía física: estado Recibida o Parcial → ya se puede pagar lo recibido.
    # condiciones_pago vive en proveedores, no en ordenes_compra — JOIN.
    cur.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.categoria, oc.valor_total, oc.fecha,
               oc.estado, oc.observaciones, oc.fecha_recepcion,
               COALESCE(p.condiciones_pago, '') as condiciones_pago
        FROM ordenes_compra oc
        LEFT JOIN proveedores p ON oc.proveedor = p.nombre
        WHERE oc.estado IN ('Recibida', 'Parcial') AND
              oc.estado != 'Pagada'
        ORDER BY oc.fecha_recepcion DESC, oc.numero_oc DESC
    """)
    cols = [d[0] for d in cur.description]
    fisicas = [
        {**dict(zip(cols, row)), 'pago_directo': False, 'tipo': 'Mercancía recibida'}
        for row in cur.fetchall()
    ]

    # Servicios sin mercancía: Aprobada/Autorizada + categoría de pago directo
    placeholders = ','.join('?' for _ in CATEGORIAS_PAGO_DIRECTO)
    cur.execute(f"""
        SELECT oc.numero_oc, oc.proveedor, oc.categoria, oc.valor_total, oc.fecha,
               oc.estado, oc.observaciones,
               COALESCE(oc.fecha_recepcion, oc.fecha) as fecha_recepcion,
               COALESCE(p.condiciones_pago, '') as condiciones_pago
        FROM ordenes_compra oc
        LEFT JOIN proveedores p ON oc.proveedor = p.nombre
        WHERE oc.estado IN ('Aprobada', 'Autorizada') AND
              oc.categoria IN ({placeholders})
        ORDER BY oc.fecha DESC
    """, CATEGORIAS_PAGO_DIRECTO)
    cols = [d[0] for d in cur.description]
    servicios = [
        {**dict(zip(cols, row)), 'pago_directo': True,
         'tipo': 'Pago directo (servicio)'}
        for row in cur.fetchall()
    ]

    # NOTA 28-abr-2026 (sesion #2 Sebastian): retiramos la seccion
    # "en_proceso" de Por Pagar. Las OCs en Borrador/Revisada/Pendiente/
    # Aprobada NO son "pendiente de pago" todavia — estan en proceso de
    # creacion/autorizacion y se ven en Dashboard y otras pestañas.
    # Por Pagar ahora muestra SOLO lo que esta listo para pagar:
    #   - Mercancia recibida (Recibida/Parcial)
    #   - Servicios autorizados (Aprobada/Autorizada con categoria de pago directo)
    todos = fisicas + servicios
    todos.sort(key=lambda x: x.get('fecha_recepcion') or x.get('fecha') or '', reverse=True)

    total_valor = sum(item.get('valor_total', 0) or 0 for item in todos)
    total_servicios = sum(item['valor_total'] or 0 for item in servicios)
    total_fisicas = sum(item['valor_total'] or 0 for item in fisicas)

    return jsonify({
        'items': todos,
        'count': len(todos),
        'total_valor': round(total_valor, 2),
        'desglose': {
            'pagos_directos_servicios': {
                'count': len(servicios),
                'valor': round(total_servicios, 2),
            },
            'mercancia_recibida': {
                'count': len(fisicas),
                'valor': round(total_fisicas, 2),
            },
        }
    })

@bp.route('/api/ordenes-compra/<numero_oc>/comprobante', methods=['GET'])
def get_comprobante(numero_oc):
    """Return only the comprobante_imagen for a specific OC (lazy load)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT comprobante_imagen FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row or not row[0]:
        return jsonify({'error': 'Sin comprobante'}), 404
    return jsonify({'imagen': row[0]})

@bp.route('/api/compras/oc/<numero_oc>/rechazar', methods=['POST'])
def rechazar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    d = request.get_json() or {}
    motivo = d.get('motivo', 'Sin motivo especificado')[:300]
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT estado, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'OC no encontrada'}), 404
    # Mark OC as Rechazada
    cur.execute("UPDATE ordenes_compra SET estado='Rechazada', observaciones=COALESCE(observaciones,'')||' | RECHAZADA: '||? WHERE numero_oc=?",
                (motivo, numero_oc))
    try:
        audit_log(cur, usuario=usuario_actual, accion='RECHAZAR_OC',
                  tabla='ordenes_compra', registro_id=numero_oc,
                  antes={'estado': row[0], 'categoria': row[1]},
                  despues={'estado': 'Rechazada', 'motivo': motivo[:300]},
                  detalle=f"Rechazó OC {numero_oc} · motivo: {motivo[:120]}")
    except Exception as e:
        log.warning('audit_log RECHAZAR_OC fallo: %s', e)
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
    conn.commit()

    # Sebastian (30-abr-2026): si el motivo sugiere "ya pagamos", buscar el CE
    # asociado para incluir referencia y cerrar el ciclo informativo.
    _motivo_lower = (motivo or '').lower()
    _ya_pagada = any(k in _motivo_lower for k in ['ya pag', 'pagada', 'duplicada', 'duplicado'])
    _ce_info = ''
    _ce_codigo = None
    if _ya_pagada or 'ya' in _motivo_lower and 'pag' in _motivo_lower:
        try:
            ce_row = cur.execute(
                "SELECT codigo, fecha, monto FROM comprobantes_pago "
                "WHERE numero_oc=? OR observaciones LIKE ? ORDER BY id DESC LIMIT 1",
                (numero_oc, f'%{numero_oc}%')
            ).fetchone()
            if ce_row:
                _ce_codigo, _ce_fecha, _ce_monto = ce_row
                _ce_info = (f'<div style="background:#d1fae5;border-left:4px solid #16a34a;'
                            f'padding:12px 16px;border-radius:0 6px 6px 0;margin-top:12px">'
                            f'<b>\u2713 Esta OC ya estaba pagada:</b> CE {_ce_codigo} '
                            f'del {_ce_fecha} por ${_ce_monto:,.0f}'
                            f'</div>')
        except Exception:
            pass

    # Email destino: primero el email directo de la solicitud, luego el mapa USER_EMAILS
    _dest_email = _sol_email_directo or USER_EMAILS.get(_sol_nombre, '')
    if sol and _dest_email:
        _asunto_r = f'OC rechazada \u2014 {numero_oc}'
        _accion = 'Tu solicitud volvio a estado <em>Pendiente</em>. Puedes corregirla y reenviarla desde el sistema.'
        if _ce_codigo:
            _accion = (f'No necesitas reenviar la solicitud \u2014 el pago ya esta registrado '
                       f'(CE {_ce_codigo}). Si tienes dudas, abre /compras \u2192 Comprobantes.')
        _body_r = (
            '<html><body style="font-family:Arial,sans-serif;max-width:600px;">'
            '<div style="background:#fee2e2;padding:20px;border-radius:8px;border-left:4px solid #dc2626;">'
            '<h2 style="color:#991b1b;">Orden de compra rechazada</h2>'
            f'<p>La OC <strong>{numero_oc}</strong> asociada a tu solicitud fue rechazada.</p>'
            f'<p><strong>Motivo:</strong> {motivo}</p>'
            f'{_ce_info}'
            f'<p style="margin-top:14px">{_accion}</p>'
            '<p style="color:#6b7280;font-size:12px;">Compras HHA \u2014 Espagiria</p>'
            '</div></body></html>'
        )
        _notificar_solicitante_email(_dest_email, _asunto_r, _body_r)

    # Push notif in-app al solicitante tambi\u00e9n
    if sol and _sol_nombre:
        try:
            from blueprints.notif import push_notif
            cuerpo = motivo
            if _ce_codigo:
                cuerpo += f' \u00b7 \u2713 Ya pagada con CE {_ce_codigo}'
            push_notif(_sol_nombre, 'oc_estado',
                       f'OC {numero_oc} rechazada',
                       body=cuerpo[:160], link='/compras#mis-sol',
                       remitente=usuario_actual,
                       importante=not _ya_pagada)
        except Exception:
            pass
    return jsonify({'ok': True, 'estado': 'Rechazada', 'motivo': motivo,
                    'ce_codigo': _ce_codigo, 'ya_pagada': bool(_ce_codigo)})

@bp.route('/api/compras/buscar-remision/<remision_code>')
def buscar_remision(remision_code):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM ordenes_compra WHERE remision_code=?", (remision_code,))
    oc_row = cur.fetchone()
    oc_cols = [d[0] for d in cur.description] if cur.description else []
    if not oc_row:
        return jsonify({'error': 'No encontrado'}), 404
    oc = dict(zip(oc_cols, oc_row))
    cur.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (oc['numero_oc'],))
    items = cur.fetchall()
    return jsonify({'oc': oc, 'items': items})

# ════════════════════════════════════════════
# MEE — Materiales de Envase & Empaque
# ════════════════════════════════════════════

@bp.route('/api/mee', methods=['GET','POST'])
def handle_mee():
    conn = get_db(); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        if not d.get('codigo') or not d.get('descripcion'):
            return jsonify({'error':'codigo y descripcion requeridos'}), 400
        try:
            cur.execute("""INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo'].upper().strip(), d['descripcion'].strip(),
                 d.get('categoria','Otro'), d.get('proveedor',''), d.get('fabricante',''),
                 'Activo', float(d.get('stock_actual',2000)), float(d.get('stock_minimo',1000)),
                 'und', datetime.now().isoformat()))
            conn.commit()
            return jsonify({'message':f"MEE '{d['codigo']}' creado"}), 201
        except Exception as e:
            return jsonify({'error':str(e)}), 400
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
    return jsonify({'items':items})

@bp.route('/api/mee/<codigo>', methods=['GET','PUT'])
def handle_mee_item(codigo):
    conn = get_db(); cur = conn.cursor()
    if request.method == 'PUT':
        d = request.get_json(silent=True) or {}
        fields=[]; vals=[]
        for f in ['descripcion','categoria','proveedor','stock_minimo','estado']:
            if f in d: fields.append(f'{f}=?'); vals.append(d[f])
        if not fields: return jsonify({'error':'nada que actualizar'}), 400
        vals.append(codigo)
        cur.execute(f"UPDATE maestro_mee SET {','.join(fields)} WHERE codigo=?", vals)
        conn.commit()
        return jsonify({'message':'actualizado'})
    cur.execute("SELECT * FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone()
    if not row: return jsonify({'error':'no encontrado'}), 404
    cols=[d[0] for d in cur.description]
    return jsonify(dict(zip(cols,row)))

@bp.route('/api/mee/<codigo>/ajuste', methods=['POST'])
def ajuste_mee(codigo):
    conn = get_db(); cur = conn.cursor()
    d = request.get_json(silent=True) or {}
    nuevo = float(d.get('nuevo_stock',0))
    obs = d.get('observaciones','Ajuste manual')
    oper = d.get('operador','Sistema')
    cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone()
    if not row: return jsonify({'error':'MEE no encontrado'}), 404
    anterior=row[0]
    diff=nuevo-anterior
    cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,codigo))
    cur.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,lote_ref,observaciones,responsable,fecha) VALUES (?,?,?,?,?,?,?)",
                (codigo,'Ajuste',diff,'ajuste_manual',obs,oper,datetime.now().isoformat()))
    conn.commit()
    return jsonify({'ok':True,'nuevo_stock':nuevo})

@bp.route('/api/movimientos-mee', methods=['GET','POST'])
def handle_movimientos_mee():
    conn = get_db(); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        cod  = d.get('codigo_mee') or d.get('mee_codigo', '')
        tipo_raw = d.get('tipo','Entrada'); tipo = tipo_raw[0].upper()+tipo_raw[1:].lower() if tipo_raw else 'Entrada'
        cant = float(d.get('cantidad',0))
        ref  = d.get('referencia','')
        obs  = d.get('observaciones','')
        oper = d.get('operador','')
        if not cod or cant<=0: return jsonify({'error':'datos invalidos'}), 400
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: return jsonify({'error':'MEE no encontrado'}), 404
        delta = cant if tipo in ('Entrada','entrada') else -cant
        nuevo = row[0]+delta
        if nuevo<0: return jsonify({'error':f'Stock insuficiente (actual: {row[0]})'}), 400
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,lote_ref,observaciones,responsable,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,tipo,cant,ref,obs,oper,datetime.now().isoformat()))
        conn.commit()
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
    return jsonify({'movimientos':rows})

@bp.route('/api/movimientos-mee/lote', methods=['POST'])
def movimientos_mee_lote():
    conn = get_db(); cur = conn.cursor()
    d = request.get_json(silent=True) or {}
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
    conn.commit()
    if errores: return jsonify({'ok':True,'advertencias':errores})
    return jsonify({'ok':True})

@bp.route('/api/alertas-mee', methods=['GET'])
def alertas_mee():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""SELECT codigo,descripcion,categoria,proveedor,stock_actual,stock_minimo
                   FROM maestro_mee WHERE estado='Activo' AND stock_actual < stock_minimo
                   ORDER BY (stock_actual - stock_minimo) ASC""")
    cols=['codigo','descripcion','categoria','proveedor','stock_actual','stock_minimo']
    alertas=[dict(zip(cols,r)) for r in cur.fetchall()]
    return jsonify({'alertas':alertas,'total':len(alertas)})

@bp.route('/api/compras/consolidado-proveedor', methods=['GET'])
def consolidado_por_proveedor():
    """
    Consolida OCs activas agrupadas por proveedor.
    Incluye datos del proveedor (NIT, contacto, tel) y observaciones de cada OC
    como fallback cuando no hay items registrados en ordenes_compra_items.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    estados_activos = request.args.getlist('estados') or ['Borrador', 'Revisada', 'Autorizada']
    placeholders = ','.join('?' * len(estados_activos))

    conn = get_db(); c = conn.cursor()
    c.execute(f"""
        SELECT
            o.proveedor,
            o.numero_oc,
            o.estado,
            o.fecha,
            o.valor_total,
            o.categoria,
            o.observaciones,
            i.id,
            i.codigo_mp,
            i.nombre_mp,
            i.cantidad_g,
            i.precio_unitario,
            i.subtotal,
            pv.nit,
            pv.contacto,
            pv.telefono,
            pv.email,
            COALESCE(o.con_iva, 0) AS con_iva,
            COALESCE(o.valor_sin_iva, 0) AS valor_sin_iva
        FROM ordenes_compra o
        LEFT JOIN ordenes_compra_items i ON o.numero_oc = i.numero_oc
        LEFT JOIN proveedores pv ON LOWER(TRIM(o.proveedor)) = LOWER(TRIM(pv.nombre))
        WHERE o.estado IN ({placeholders})
        AND o.categoria NOT IN ('Influencer/Marketing Digital','Cuenta de Cobro','CC')
        ORDER BY o.proveedor, o.numero_oc, i.nombre_mp
    """, estados_activos)

    rows = c.fetchall()
    from collections import OrderedDict
    proveedores = OrderedDict()

    for row in rows:
        (prov, oc, estado, fecha, valor_total_oc, cat, obs,
         item_id, cod_mp, nom_mp, cant, precio_u, subtotal,
         nit, contacto, telefono, email,
         con_iva, valor_sin_iva) = row
        prov = prov or 'Sin proveedor'

        if prov not in proveedores:
            proveedores[prov] = {
                'proveedor': prov,
                'nit': nit or '',
                'contacto': contacto or '',
                'telefono': telefono or '',
                'email': email or '',
                'ocs': {},
                'items': {},
                'valor_total': 0.0,
            }

        p = proveedores[prov]
        # Completar datos proveedor si primera fila no los tenía
        if not p['nit'] and nit: p['nit'] = nit
        if not p['contacto'] and contacto: p['contacto'] = contacto
        if not p['telefono'] and telefono: p['telefono'] = telefono
        if not p['email'] and email: p['email'] = email

        # Registrar OC (incluye observaciones, con_iva, items_raw para edicion)
        if oc and oc not in p['ocs']:
            p['ocs'][oc] = {
                'numero_oc': oc,
                'estado': estado,
                'fecha': (fecha or '')[:10],
                'valor_total': valor_total_oc or 0,
                'categoria': cat or '',
                'observaciones': obs or '',
                'con_iva': int(con_iva or 0),
                'valor_sin_iva': float(valor_sin_iva or 0),
                'items_raw': [],   # items individuales por OC para modo editar
            }
            p['valor_total'] += valor_total_oc or 0

        # Items individuales (para modo editar) por OC
        if oc and item_id is not None:
            p['ocs'][oc]['items_raw'].append({
                'id': item_id,
                'codigo_mp': cod_mp or '',
                'nombre_mp': nom_mp or cod_mp or '',
                'cantidad_g': cant or 0,
                'precio_unitario': precio_u or 0,
                'subtotal': subtotal or 0,
            })

        # Consolidar item por codigo_mp (modo lectura)
        if cod_mp:
            if cod_mp not in p['items']:
                p['items'][cod_mp] = {
                    'codigo_mp': cod_mp,
                    'nombre_mp': nom_mp or cod_mp,
                    'cantidad_total_g': 0.0,
                    'precio_unitario': precio_u or 0,
                    'subtotal_total': 0.0,
                    'ocs_origen': [],
                }
            item = p['items'][cod_mp]
            item['cantidad_total_g'] += cant or 0
            item['subtotal_total'] += subtotal or 0
            if oc and oc not in item['ocs_origen']:
                item['ocs_origen'].append(oc)

    result = []
    for prov, data in proveedores.items():
        result.append({
            'proveedor': prov,
            'nit': data['nit'],
            'contacto': data['contacto'],
            'telefono': data['telefono'],
            'email': data['email'],
            'ocs': sorted(data['ocs'].values(), key=lambda x: x['fecha'], reverse=True),
            'items': sorted(data['items'].values(), key=lambda x: x['nombre_mp']),
            'valor_total': data['valor_total'],
            'n_ocs': len(data['ocs']),
            'n_items': len(data['items']),
        })

    result.sort(key=lambda x: x['valor_total'], reverse=True)
    return jsonify({'proveedores': result, 'total': len(result)})

@bp.route('/api/compras/solicitudes/pdf', methods=['GET'])
def solicitudes_pdf_resumen():
    """Genera PDF ejecutivo con todas las solicitudes filtradas — para que
    Gerencia (Alejandro) revise lo que falta y dé visto bueno antes de
    convertir en OCs.

    Query params:
      - estados: lista (default 'Pendiente,Aprobada')
      - categoria: filtra (default sin filtro, excluye Influencer/CC)

    Cada solicitud incluye su detalle de items (codigo, nombre, cantidad,
    unidad, justificación) agrupado y totalizado.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    estados = (request.args.get('estados') or 'Pendiente,Aprobada').split(',')
    estados = [e.strip() for e in estados if e.strip()]
    if not estados:
        estados = ['Pendiente', 'Aprobada']

    conn = get_db(); c = conn.cursor()
    placeholders = ','.join('?' * len(estados))
    sql = f"""
        SELECT sc.numero, sc.fecha, sc.estado, sc.solicitante, sc.urgencia,
               sc.observaciones, sc.empresa, sc.categoria, sc.area,
               sc.fecha_requerida, sc.numero_oc,
               COALESCE(NULLIF(oc.valor_total,0), sc.valor, 0) as valor_oc,
               COALESCE(oc.proveedor, '') as proveedor
        FROM solicitudes_compra sc
        LEFT JOIN ordenes_compra oc ON oc.numero_oc = sc.numero_oc
        WHERE sc.estado IN ({placeholders})
          AND sc.categoria NOT IN ('Influencer/Marketing Digital', 'Cuenta de Cobro')
        ORDER BY
          CASE sc.urgencia WHEN 'Alta' THEN 0 WHEN 'Normal' THEN 1 ELSE 2 END,
          sc.fecha_requerida ASC, sc.numero ASC
    """
    sols = c.execute(sql, estados).fetchall()

    # Cargar items por solicitud
    items_por_sol = {}
    for sol_row in sols:
        numero = sol_row[0]
        try:
            it = c.execute("""SELECT codigo_mp, nombre_mp, cantidad_g, unidad,
                                     justificacion, COALESCE(valor_estimado, 0)
                              FROM solicitudes_compra_items
                              WHERE numero=?""", (numero,)).fetchall()
            items_por_sol[numero] = it
        except sqlite3.OperationalError:
            items_por_sol[numero] = []

    if not sols:
        return jsonify({
            'error': 'No hay solicitudes con esos estados',
            'estados_solicitados': estados,
        }), 404

    # ── Generar PDF con fpdf2 — diseño ejecutivo nivel OC ──────────────────
    from fpdf import FPDF
    from datetime import datetime as _dt
    from pathlib import Path

    # Paleta HHA — coordinada con OC (compras_html.py) y branding
    HHA_TEAL = (31, 95, 91)
    HHA_TEAL_DARK = (16, 70, 67)
    COLOR_TEXT = (40, 40, 40)
    COLOR_TEXT_SOFT = (110, 110, 110)
    COLOR_LINE = (200, 195, 188)
    CARD_BG = (250, 248, 244)
    CARD_BORDER = (215, 210, 200)
    TABLE_HEADER_BG = (45, 45, 45)
    TABLE_ALT_ROW = (248, 248, 246)
    BADGE_PEND_BG = (255, 213, 79)       # ámbar Pendiente
    BADGE_PEND_FG = (90, 70, 0)
    BADGE_APR_BG = (89, 165, 121)         # verde Aprobada
    BADGE_APR_FG = (255, 255, 255)
    BADGE_URG_ALTA = (220, 70, 70)
    BADGE_URG_NORM = (140, 140, 140)
    BADGE_URG_BAJA = (180, 180, 180)

    def _fmt_cant(g, u='g'):
        """Normalizado: SIEMPRE en gramos con separador de miles (acordado con Alejandro).
        Preserva decimales solo para péptidos (<1g)."""
        n = float(g or 0)
        if u and u != 'g':
            return f'{n:.0f} {u}' if n == int(n) else f'{n:.2f} {u}'
        if n >= 10:
            return f'{int(round(n)):,}'.replace(',', '.') + ' g'
        if n >= 1:
            return f'{n:.1f} g'
        if n > 0:
            return f'{n:.2f} g'
        return '0 g'

    def _safe(t):
        if t is None:
            return ''
        if not isinstance(t, str):
            t = str(t)
        repl = {'—': '-', '–': '-', '…': '...', '"': '"', '"': '"',
                ''': "'", ''': "'", '•': '·', '→': '->', 'á':'a', 'é':'e',
                'í':'i', 'ó':'o', 'ú':'u', 'Á':'A', 'É':'E', 'Í':'I',
                'Ó':'O', 'Ú':'U', 'ñ':'n', 'Ñ':'N'}
        for k, v in repl.items():
            t = t.replace(k, v)
        return t.encode('latin-1', errors='replace').decode('latin-1')

    n_pendientes = sum(1 for s in sols if s[2] == 'Pendiente')
    n_aprobadas = sum(1 for s in sols if s[2] == 'Aprobada')
    generado_str = _dt.now().strftime("%d/%m/%Y %H:%M")
    estados_str = ', '.join(estados)

    # Logo path resuelto una sola vez
    repo_root = Path(__file__).resolve().parents[2]
    logo_path = None
    for cand in [repo_root / 'api' / 'static' / 'logo_hha.png',
                 repo_root / 'logo_hha.png']:
        if cand.exists():
            logo_path = str(cand)
            break

    class SolicitudesPDF(FPDF):
        """Header repetido en cada página + footer con paginación."""

        def header(self_pdf):
            if self_pdf.page_no() == 1:
                # Header completo en la primera página
                if logo_path:
                    try:
                        self_pdf.image(logo_path, x=10, y=10, w=22, h=22)
                    except Exception:
                        pass
                self_pdf.set_xy(36, 10)
                self_pdf.set_font('Helvetica', 'B', 18)
                self_pdf.set_text_color(*HHA_TEAL)
                self_pdf.cell(110, 8, _safe('SOLICITUDES DE COMPRA'), ln=True)
                self_pdf.set_x(36)
                self_pdf.set_font('Helvetica', '', 9)
                self_pdf.set_text_color(*COLOR_TEXT_SOFT)
                self_pdf.cell(110, 4, _safe('HHA Group · Reporte ejecutivo'), ln=True)
                self_pdf.set_x(36)
                self_pdf.set_font('Helvetica', '', 8)
                self_pdf.cell(110, 4, _safe(f'Generado: {generado_str}'), ln=True)
                self_pdf.set_x(36)
                self_pdf.cell(110, 4, _safe(f'Estados: {estados_str}'), ln=True)

                # Caja resumen (top right)
                bx, by, bw, bh = 142, 10, 58, 24
                self_pdf.set_fill_color(*CARD_BG)
                self_pdf.set_draw_color(*HHA_TEAL)
                self_pdf.set_line_width(0.5)
                self_pdf.rect(bx, by, bw, bh, style='DF')
                self_pdf.set_xy(bx + 3, by + 2)
                self_pdf.set_font('Helvetica', 'B', 7)
                self_pdf.set_text_color(*HHA_TEAL_DARK)
                self_pdf.cell(bw - 6, 3, _safe('TOTAL SOLICITUDES'))
                self_pdf.set_xy(bx + 3, by + 6)
                self_pdf.set_font('Helvetica', 'B', 18)
                self_pdf.set_text_color(*COLOR_TEXT)
                self_pdf.cell(bw - 6, 8, str(len(sols)))
                self_pdf.set_xy(bx + 3, by + 16)
                self_pdf.set_font('Helvetica', '', 7.5)
                self_pdf.set_text_color(*COLOR_TEXT_SOFT)
                self_pdf.cell((bw - 6) / 2, 4, _safe(f'Pendientes: {n_pendientes}'))
                self_pdf.cell((bw - 6) / 2, 4, _safe(f'Aprobadas: {n_aprobadas}'))

                # Línea separadora horizontal teal
                self_pdf.set_draw_color(*HHA_TEAL)
                self_pdf.set_line_width(0.6)
                self_pdf.line(10, 36, 200, 36)
                self_pdf.set_y(40)
            else:
                # Mini-header en páginas siguientes
                if logo_path:
                    try:
                        self_pdf.image(logo_path, x=10, y=8, w=10, h=10)
                    except Exception:
                        pass
                self_pdf.set_xy(22, 9)
                self_pdf.set_font('Helvetica', 'B', 10)
                self_pdf.set_text_color(*HHA_TEAL)
                self_pdf.cell(0, 4, _safe('SOLICITUDES DE COMPRA'), ln=True)
                self_pdf.set_x(22)
                self_pdf.set_font('Helvetica', '', 7)
                self_pdf.set_text_color(*COLOR_TEXT_SOFT)
                self_pdf.cell(0, 3, _safe(f'Continuacion · {generado_str}'), ln=True)
                self_pdf.set_draw_color(*CARD_BORDER)
                self_pdf.set_line_width(0.3)
                self_pdf.line(10, 21, 200, 21)
                self_pdf.set_y(25)

        def footer(self_pdf):
            self_pdf.set_y(-13)
            self_pdf.set_font('Helvetica', 'I', 7)
            self_pdf.set_text_color(*COLOR_TEXT_SOFT)
            self_pdf.cell(0, 4, _safe(f'HHA Group · Pagina {self_pdf.page_no()} de {{nb}}'),
                          align='C')

    def _draw_badge(p, x, y, w, h, text, fg, bg):
        p.set_fill_color(*bg)
        p.set_draw_color(*bg)
        p.rect(x, y, w, h, style='DF')
        p.set_xy(x, y)
        p.set_font('Helvetica', 'B', 7)
        p.set_text_color(*fg)
        p.cell(w, h, _safe(text), align='C')

    def _badge_estado(estado):
        if (estado or '').strip() == 'Aprobada':
            return (BADGE_APR_FG, BADGE_APR_BG)
        return (BADGE_PEND_FG, BADGE_PEND_BG)

    def _badge_urgencia(urg):
        u = (urg or '').strip()
        if u == 'Alta':
            return ((255, 255, 255), BADGE_URG_ALTA)
        if u == 'Normal':
            return ((255, 255, 255), BADGE_URG_NORM)
        return ((255, 255, 255), BADGE_URG_BAJA)

    pdf = SolicitudesPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    total_general_g = 0.0
    total_general_valor = 0.0

    # ─── Una "card" por solicitud ───────────────────────────────────
    for s in sols:
        (numero, fecha, estado, solicitante, urgencia, obs, empresa,
         categoria, area, fecha_req, numero_oc, valor_oc, proveedor) = s
        items = items_por_sol.get(numero, [])

        # Page break preventivo: necesitamos al menos espacio para el header
        # de la card + 1 fila de tabla. Si no, salta.
        if pdf.get_y() > 250:
            pdf.add_page()

        card_x = 10
        card_w = 190
        card_top = pdf.get_y()

        # Barra teal con número de solicitud + badges (estado, urgencia)
        bar_h = 9
        pdf.set_fill_color(*HHA_TEAL)
        pdf.rect(card_x, card_top, card_w, bar_h, style='F')
        pdf.set_xy(card_x + 3, card_top + 1.5)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(70, 6, _safe(numero), align='L')

        # Badges en el extremo derecho
        bw = 24
        bh = 5
        gap = 2
        bx_right = card_x + card_w - 3
        # Urgencia (más a la derecha)
        fg_u, bg_u = _badge_urgencia(urgencia)
        _draw_badge(pdf, bx_right - bw, card_top + 2, bw, bh,
                    f'URG: {(urgencia or "-").upper()[:8]}', fg_u, bg_u)
        # Estado
        fg_e, bg_e = _badge_estado(estado)
        _draw_badge(pdf, bx_right - 2 * bw - gap, card_top + 2, bw, bh,
                    (estado or '-').upper()[:10], fg_e, bg_e)

        # Cuerpo de la card
        pdf.set_y(card_top + bar_h)
        pdf.set_x(card_x + 3)
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*COLOR_TEXT)
        meta1 = (f"Fecha: {(fecha or '')[:10]}    "
                 f"Solicitante: {solicitante or '-'}    "
                 f"Area: {area or '-'}    "
                 f"Empresa: {empresa or '-'}")
        pdf.cell(card_w - 6, 5, _safe(meta1), ln=True)

        if proveedor or fecha_req or numero_oc:
            extra = []
            if proveedor: extra.append(f'Proveedor: {proveedor}')
            if fecha_req: extra.append(f'Fecha req.: {fecha_req}')
            if numero_oc: extra.append(f'OC: {numero_oc}')
            pdf.set_x(card_x + 3)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(*COLOR_TEXT_SOFT)
            pdf.cell(card_w - 6, 4, _safe('    '.join(extra)), ln=True)

        if obs:
            pdf.set_x(card_x + 3)
            pdf.set_font('Helvetica', 'I', 7.5)
            pdf.set_text_color(*COLOR_TEXT_SOFT)
            pdf.multi_cell(card_w - 6, 3.6, _safe(f'Obs: {obs[:280]}'))

        # Tabla de items
        if items:
            pdf.ln(0.5)
            cols = [(24, 'CODIGO', 'L'), (72, 'MATERIAL', 'L'),
                    (24, 'CANTIDAD', 'R'), (10, 'UM', 'C'),
                    (40, 'JUSTIFICACION', 'L'), (20, 'VALOR EST', 'R')]
            # Header row (dark gray)
            pdf.set_x(card_x)
            pdf.set_fill_color(*TABLE_HEADER_BG)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 7.5)
            for w, name, _al in cols:
                pdf.cell(w, 5.5, _safe(name), border=0, fill=True, align='C')
            pdf.ln()

            # Data rows con alternating fill
            sol_total_g = 0.0
            sol_total_valor = 0.0
            pdf.set_text_color(*COLOR_TEXT)
            pdf.set_font('Helvetica', '', 8)
            row_h = 4.5
            for idx, it in enumerate(items):
                cod_mp, nom_mp, cant_g, unidad, just, val_est = it
                cant = float(cant_g or 0)
                val = float(val_est or 0)
                sol_total_g += cant
                sol_total_valor += val
                cant_str = _fmt_cant(cant, unidad)
                fill_alt = (idx % 2 == 1)
                if fill_alt:
                    pdf.set_fill_color(*TABLE_ALT_ROW)
                pdf.set_x(card_x)
                pdf.cell(24, row_h, _safe((cod_mp or '')[:14]),
                         border=0, fill=fill_alt)
                pdf.cell(72, row_h, _safe((nom_mp or '')[:46]),
                         border=0, fill=fill_alt)
                pdf.cell(24, row_h, _safe(cant_str),
                         border=0, fill=fill_alt, align='R')
                pdf.cell(10, row_h, _safe(unidad or 'g'),
                         border=0, fill=fill_alt, align='C')
                pdf.cell(40, row_h, _safe((just or '')[:32]),
                         border=0, fill=fill_alt)
                pdf.cell(20, row_h, _safe(f'${val:,.0f}' if val > 0 else '-'),
                         border=0, fill=fill_alt, align='R')
                pdf.ln()

            # Total row (teal-dark)
            pdf.set_x(card_x)
            pdf.set_fill_color(*HHA_TEAL_DARK)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 8)
            cant_total_str = _fmt_cant(sol_total_g, 'g')
            pdf.cell(24 + 72, 5.5, _safe(f'TOTAL  ·  {len(items)} items'),
                     fill=True, border=0, align='R')
            pdf.cell(24, 5.5, _safe(cant_total_str),
                     fill=True, border=0, align='R')
            pdf.cell(10 + 40, 5.5, '', fill=True, border=0)
            pdf.cell(20, 5.5,
                     _safe(f'${sol_total_valor:,.0f}' if sol_total_valor > 0 else '-'),
                     fill=True, border=0, align='R')
            pdf.ln(0)

            total_general_g += sol_total_g
            total_general_valor += sol_total_valor
        else:
            pdf.set_x(card_x + 3)
            pdf.set_font('Helvetica', 'I', 8)
            pdf.set_text_color(*COLOR_TEXT_SOFT)
            pdf.cell(card_w - 6, 5, _safe('(sin items detallados)'), ln=True)

        # Borde fino alrededor de toda la card (post-render para altura exacta)
        card_h = pdf.get_y() - card_top
        pdf.set_draw_color(*CARD_BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(card_x, card_top, card_w, card_h, style='D')

        pdf.ln(5)

    # ─── Resumen final ────────────────────────────────────────────────
    if pdf.get_y() > 235:
        pdf.add_page()

    pdf.ln(2)
    res_y = pdf.get_y()
    res_h = 30 if total_general_valor > 0 else 24
    pdf.set_fill_color(*CARD_BG)
    pdf.set_draw_color(*HHA_TEAL)
    pdf.set_line_width(0.6)
    pdf.rect(10, res_y, 190, res_h, style='DF')

    pdf.set_xy(13, res_y + 2)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*HHA_TEAL_DARK)
    pdf.cell(0, 5, _safe('RESUMEN GENERAL'), ln=True)

    pdf.set_xy(13, res_y + 8)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(60, 5, _safe(f'Total solicitudes:  {len(sols)}'))
    pdf.cell(60, 5, _safe(f'Pendientes:  {n_pendientes}'))
    pdf.cell(60, 5, _safe(f'Aprobadas:  {n_aprobadas}'))
    pdf.ln(5)

    pdf.set_x(13)
    pdf.cell(0, 5, _safe(f'Cantidad total a comprar:  {_fmt_cant(total_general_g)}'),
             ln=True)
    if total_general_valor > 0:
        pdf.set_x(13)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(0, 5, _safe(f'Valor estimado total:  ${total_general_valor:,.0f} COP'),
                 ln=True)

    pdf.set_y(res_y + res_h)

    # ─── Firmas ───────────────────────────────────────────────────────
    pdf.ln(14)
    y_firma = pdf.get_y()
    pdf.set_draw_color(*COLOR_LINE)
    pdf.set_line_width(0.3)
    pdf.line(20, y_firma, 90, y_firma)
    pdf.line(120, y_firma, 190, y_firma)

    pdf.set_xy(20, y_firma + 1)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(70, 4, _safe('REVISADO POR'), align='C', ln=True)
    pdf.set_x(20)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(70, 3.5, _safe('(Compras / Logistica)'), align='C')

    pdf.set_xy(120, y_firma + 1)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(70, 4, _safe('APROBADO POR GERENCIA'), align='C', ln=True)
    pdf.set_x(120)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(70, 3.5, _safe('(Alejandro / Sebastian)'), align='C')

    # Output (mismo contrato que antes: PDF descargable con timestamp)
    pdf_bytes = bytes(pdf.output())
    fname = f'solicitudes_compra_{_dt.now().strftime("%Y%m%d_%H%M")}.pdf'
    return Response(
        pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{fname}"'}
    )


# ─── MÓDULO CLIENTES — Rutas ──────────────────────────────────



@bp.route('/api/solicitudes-compra/<numero>/observaciones', methods=['PUT'])
def update_sol_observaciones(numero):
    """Admin: actualiza observaciones (y opcionalmente solicitante) de una solicitud."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado. Inicia sesion primero.'}), 401
    conn = get_db(); c = conn.cursor()
    d = request.json or {}
    obs = d.get('observaciones')
    solicitante = d.get('solicitante')
    valor = d.get('valor')
    fecha_requerida = d.get('fecha_requerida')
    if not obs and not solicitante and valor is None and not fecha_requerida:
        return jsonify({'error': 'Nada que actualizar'}), 400
    row = c.execute("SELECT numero FROM solicitudes_compra WHERE numero=?", (numero.upper(),)).fetchone()
    if not row:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    updates, params = [], []
    if obs is not None:
        updates.append("observaciones=?"); params.append(obs)
    if solicitante is not None:
        updates.append("solicitante=?"); params.append(solicitante)
    if valor is not None:
        # Cast a float puede fallar si llega string mal formateado.
        # ValueError/TypeError → silencio aceptable (campo opcional).
        try:
            updates.append("valor=?")
            params.append(float(valor))
        except (ValueError, TypeError):
            # Quitar el SET que apenas agregamos para no dejar params desbalanceados.
            if updates and updates[-1] == "valor=?":
                updates.pop()
    if fecha_requerida is not None:
        updates.append("fecha_requerida=?"); params.append(str(fecha_requerida))
    params.append(numero.upper())
    c.execute(f"UPDATE solicitudes_compra SET {','.join(updates)} WHERE numero=?", params)
    conn.commit()
    return jsonify({'ok': True, 'numero': numero.upper()})


# ─── Edicion de items de SOL: cantidad/proveedor/precio (req. Catalina 2026) ──

@bp.route('/api/solicitudes-compra/<numero>/items', methods=['PATCH'])
def update_sol_items(numero):
    """Catalina edita items de una SOL antes de aprobar:
       - cantidad_g  (puede aumentar si conviene pedir mas)
       - proveedor   (si cambia, se normaliza en maestro_mps)
       - precio_unit_g (si cambia, se inserta en precio_historico_mp)

    Body: {items: [{id, cantidad_g, proveedor, precio_unit_g}, ...]}

    Side effects:
      1. solicitudes_compra_items.cantidad_g / valor_estimado actualizados
      2. solicitudes_compra.valor recalculado
      3. maestro_mps.proveedor actualizado si proveedor != actual
      4. precio_historico_mp insertado si precio_unit_g cambio
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado. Inicia sesion primero.'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    items_in = d.get('items') or []
    if not items_in:
        return jsonify({'error': 'No hay items en el body'}), 400

    conn = get_db(); c = conn.cursor()
    sol = c.execute(
        "SELECT numero FROM solicitudes_compra WHERE numero=?",
        (numero.upper(),)
    ).fetchone()
    if not sol:
        return jsonify({'error': 'SOL no encontrada'}), 404

    cambios = {
        'items_actualizados': 0,
        'maestro_mps_actualizados': 0,
        'precios_historicos_insertados': 0,
    }
    now = datetime.now().isoformat()

    for it in items_in:
        item_id = it.get('id')
        if not item_id:
            continue
        # Estado actual del item
        row = c.execute("""
            SELECT id, codigo_mp, nombre_mp, cantidad_g,
                   COALESCE(precio_unit_g, 0) as precio_unit_g,
                   COALESCE(valor_estimado, 0) as valor_estimado,
                   COALESCE(proveedor_sugerido, '') as proveedor_actual
            FROM solicitudes_compra_items
            WHERE id=? AND numero=?
        """, (item_id, numero.upper())).fetchone()
        if not row:
            continue
        (_id, codigo_mp, nombre_mp, cant_actual,
         precio_actual, valor_actual, prov_actual) = row

        # Valores nuevos (si vienen, sino mantenemos los actuales)
        cant_nueva = float(it.get('cantidad_g', cant_actual) or 0)
        precio_nuevo = float(it.get('precio_unit_g', precio_actual) or 0)
        prov_nuevo = (it.get('proveedor', prov_actual) or '').strip()
        valor_nuevo = round(cant_nueva * precio_nuevo, 2) if precio_nuevo > 0 else valor_actual

        # 1) Update item
        c.execute("""
            UPDATE solicitudes_compra_items
               SET cantidad_g=?, precio_unit_g=?, valor_estimado=?,
                   proveedor_sugerido=?, actualizado_at=?, actualizado_por=?
             WHERE id=?
        """, (cant_nueva, precio_nuevo, valor_nuevo, prov_nuevo, now, user, item_id))
        cambios['items_actualizados'] += 1

        # 2) Si proveedor cambio -> normalizar en maestro_mps
        if codigo_mp and prov_nuevo and prov_nuevo != prov_actual:
            try:
                c.execute("""
                    UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?
                """, (prov_nuevo, codigo_mp))
                if c.rowcount > 0:
                    cambios['maestro_mps_actualizados'] += 1
            except Exception:
                pass

        # 3) Si precio cambio (>0) y es distinto del anterior -> historico
        if precio_nuevo > 0 and abs(precio_nuevo - (precio_actual or 0)) > 1e-6:
            try:
                c.execute("""
                    INSERT INTO precio_historico_mp
                        (codigo_mp, nombre_mp, proveedor, precio_unit_g,
                         cantidad_g, valor_total, fuente, sol_numero, usuario)
                    VALUES (?, ?, ?, ?, ?, ?, 'sol_editada', ?, ?)
                """, (codigo_mp or '', nombre_mp or '', prov_nuevo,
                      precio_nuevo, cant_nueva, valor_nuevo,
                      numero.upper(), user))
                cambios['precios_historicos_insertados'] += 1
            except Exception:
                pass

    # 4) Recalcular valor total de la SOL
    total = c.execute("""
        SELECT COALESCE(SUM(valor_estimado), 0)
          FROM solicitudes_compra_items WHERE numero=?
    """, (numero.upper(),)).fetchone()[0] or 0
    c.execute(
        "UPDATE solicitudes_compra SET valor=? WHERE numero=?",
        (float(total), numero.upper())
    )

    conn.commit()
    return jsonify({
        'ok': True,
        'numero': numero.upper(),
        'valor_total': float(total),
        **cambios,
    })


# ─── Historico de precios por MP ─────────────────────────────────────────────

@bp.route('/api/precio-historico/<path:codigo_mp>', methods=['GET'])
def get_precio_historico(codigo_mp):
    """Devuelve serie temporal de precios + agregados para detectar aumentos.

    Returns:
        {
          codigo_mp, nombre_mp,
          serie: [{fecha, proveedor, precio_unit_g, fuente, sol, oc}, ...],
          stats: {
            ultimo_precio, primer_precio, variacion_pct,
            promedio_30d, promedio_90d,
            min_precio, max_precio,
            n_proveedores_distintos,
            alerta: 'sin_datos'|'estable'|'subiendo'|'bajando'|'volatil'
          }
        }
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, fecha, proveedor, precio_unit_g, cantidad_g, fuente,
               sol_numero, oc_numero, usuario
        FROM precio_historico_mp
        WHERE codigo_mp = ?
        ORDER BY fecha DESC
        LIMIT 200
    """, (codigo_mp,)).fetchall()

    serie = [
        {
            'id': r[0], 'fecha': r[1], 'proveedor': r[2],
            'precio_unit_g': r[3], 'cantidad_g': r[4],
            'fuente': r[5], 'sol_numero': r[6], 'oc_numero': r[7],
            'usuario': r[8],
        }
        for r in rows
    ]

    stats = {}
    if serie:
        precios = [s['precio_unit_g'] for s in serie if s['precio_unit_g']]
        if precios:
            stats['ultimo_precio'] = precios[0]
            stats['primer_precio'] = precios[-1]
            stats['min_precio'] = min(precios)
            stats['max_precio'] = max(precios)
            if stats['primer_precio'] > 0:
                stats['variacion_pct'] = round(
                    (stats['ultimo_precio'] - stats['primer_precio'])
                    / stats['primer_precio'] * 100,
                    2
                )
            else:
                stats['variacion_pct'] = 0

            # Promedios temporales
            from datetime import datetime as _dt, timedelta as _td
            now = _dt.now()
            d30 = (now - _td(days=30)).isoformat()
            d90 = (now - _td(days=90)).isoformat()
            p30 = [s['precio_unit_g'] for s in serie if s['fecha'] >= d30 and s['precio_unit_g']]
            p90 = [s['precio_unit_g'] for s in serie if s['fecha'] >= d90 and s['precio_unit_g']]
            stats['promedio_30d'] = round(sum(p30) / len(p30), 4) if p30 else None
            stats['promedio_90d'] = round(sum(p90) / len(p90), 4) if p90 else None

            stats['n_proveedores_distintos'] = len(
                {s['proveedor'] for s in serie if s['proveedor']}
            )

            # Alerta
            v = stats.get('variacion_pct', 0)
            if abs(v) < 5:
                stats['alerta'] = 'estable'
                stats['alerta_msg'] = 'Precio estable (variación <5%)'
            elif v >= 20:
                stats['alerta'] = 'subiendo_fuerte'
                stats['alerta_msg'] = (
                    f'Subió {v:.1f}% — considerar explorar otros proveedores'
                )
            elif v >= 5:
                stats['alerta'] = 'subiendo'
                stats['alerta_msg'] = f'Subió {v:.1f}% — vigilar tendencia'
            elif v <= -5:
                stats['alerta'] = 'bajando'
                stats['alerta_msg'] = f'Bajó {v:.1f}% — buena negociación'

    # Nombre del MP (si existe)
    nombre_mp = ''
    try:
        n = c.execute(
            "SELECT nombre_inci FROM maestro_mps WHERE codigo_mp=?",
            (codigo_mp,)
        ).fetchone()
        if n:
            nombre_mp = n[0] or ''
    except Exception:
        pass

    return jsonify({
        'codigo_mp': codigo_mp,
        'nombre_mp': nombre_mp,
        'serie': serie,
        'stats': stats,
    })


# ─── ALERTAS VIVAS DE COMPRAS (Sprint 3) ─────────────────────────────────────
# Espejo del endpoint de Planta — consume del Centro de Mando para mostrar todo
# lo que requiere atención en compras HOY.

@bp.route('/api/compras/alertas-vivas', methods=['GET'])
def alertas_vivas_compras():
    """Consolida 4 categorías de alertas operacionales de Compras.

    Retorna { ocs_sin_recibir, pagos_por_vencer, solicitudes_pendientes,
              ocs_borrador_estancadas, total, severidad_max }
    """
    u, err, code = _require_compras_session()
    if err:
        return err, code

    from datetime import date, timedelta
    hoy = date.today()
    hace_7 = (hoy - timedelta(days=7)).isoformat()
    hace_15 = (hoy - timedelta(days=15)).isoformat()
    hace_3 = (hoy - timedelta(days=3)).isoformat()

    conn = get_db(); c = conn.cursor()

    # ── 1. OCs Autorizadas hace > 15 días sin recepción ─────────────────
    c.execute("""
        SELECT numero_oc, proveedor, valor_total, fecha,
               COALESCE(fecha_entrega_est, '') as fecha_entrega
        FROM ordenes_compra
        WHERE estado = 'Autorizada' AND fecha < ?
        ORDER BY fecha ASC LIMIT 50
    """, (hace_15,))
    ocs_sin_recibir = []
    for r in c.fetchall():
        try:
            f_oc = date.fromisoformat(r[3][:10])
            dias = (hoy - f_oc).days
        except (ValueError, TypeError, IndexError):
            dias = None
        ocs_sin_recibir.append({
            'numero_oc': r[0], 'proveedor': r[1],
            'valor_total': r[2], 'fecha_oc': r[3],
            'fecha_entrega_est': r[4],
            'dias_sin_recibir': dias,
            'severidad': 'alto' if dias and dias > 30 else 'medio',
        })

    # ── 2. Pagos por vencer: OCs Recibidas con pendiente de pago ────────
    # Heurística: si OC recibida hace > N días según condiciones_pago de
    # proveedor (ej. "30 días"), está en riesgo de mora.
    c.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.valor_total,
               COALESCE(oc.fecha_recepcion, oc.fecha) as fecha_ref,
               COALESCE(p.condiciones_pago, '') as cond,
               COALESCE((SELECT SUM(monto) FROM pagos_oc WHERE numero_oc=oc.numero_oc), 0) as pagado
        FROM ordenes_compra oc
        LEFT JOIN proveedores p ON oc.proveedor = p.nombre
        WHERE oc.estado IN ('Recibida', 'Parcial')
        ORDER BY fecha_ref ASC LIMIT 100
    """)
    pagos_por_vencer = []
    for r in c.fetchall():
        # Extraer días de "30 días" / "30 dias" / "30"
        cond_str = (r[4] or '').lower()
        dias_pago = 30  # default conservador
        for word in cond_str.split():
            if word.isdigit():
                dias_pago = int(word)
                break
        try:
            f_ref = date.fromisoformat(r[3][:10])
            dias_transcurridos = (hoy - f_ref).days
            dias_restantes = dias_pago - dias_transcurridos
        except (ValueError, TypeError, IndexError):
            dias_restantes = None
        pendiente = float(r[2] or 0) - float(r[5] or 0)
        if pendiente > 0.01 and dias_restantes is not None and dias_restantes <= 14:
            pagos_por_vencer.append({
                'numero_oc': r[0], 'proveedor': r[1],
                'valor_total': r[2], 'pendiente': round(pendiente, 2),
                'fecha_ref': r[3], 'condiciones_pago': r[4],
                'dias_restantes': dias_restantes,
                'severidad': ('critico' if dias_restantes < 0 else
                              'alto' if dias_restantes <= 3 else 'medio'),
            })

    # ── 3. Solicitudes Pendientes hace > 3 días ─────────────────────────
    c.execute("""
        SELECT numero, fecha, solicitante, urgencia, area, empresa, categoria
        FROM solicitudes_compra
        WHERE estado = 'Pendiente' AND fecha < ?
        ORDER BY
            CASE urgencia WHEN 'Urgente' THEN 0 WHEN 'Alta' THEN 1 ELSE 2 END,
            fecha ASC
        LIMIT 50
    """, (hace_3,))
    solicitudes_pendientes = []
    for r in c.fetchall():
        try:
            f_sol = date.fromisoformat(r[1][:10])
            dias = (hoy - f_sol).days
        except (ValueError, TypeError, IndexError):
            dias = None
        sev = 'alto' if r[3] == 'Urgente' else ('medio' if dias and dias > 7 else 'bajo')
        solicitudes_pendientes.append({
            'numero': r[0], 'fecha': r[1], 'solicitante': r[2],
            'urgencia': r[3], 'area': r[4], 'empresa': r[5],
            'categoria': r[6], 'dias_pendiente': dias, 'severidad': sev,
        })

    # ── 4. OCs en Borrador hace > 7 días sin avanzar ────────────────────
    c.execute("""
        SELECT numero_oc, proveedor, valor_total, fecha, creado_por
        FROM ordenes_compra
        WHERE estado = 'Borrador' AND fecha < ?
        ORDER BY fecha ASC LIMIT 50
    """, (hace_7,))
    ocs_borrador = [
        {'numero_oc': r[0], 'proveedor': r[1], 'valor_total': r[2],
         'fecha': r[3], 'creado_por': r[4], 'severidad': 'medio'}
        for r in c.fetchall()
    ]

    total = (len(ocs_sin_recibir) + len(pagos_por_vencer) +
             len(solicitudes_pendientes) + len(ocs_borrador))
    sevs = (
        [v['severidad'] for v in ocs_sin_recibir] +
        [v['severidad'] for v in pagos_por_vencer] +
        [v['severidad'] for v in solicitudes_pendientes] +
        [v['severidad'] for v in ocs_borrador]
    )
    sev_orden = {'critico': 4, 'alto': 3, 'medio': 2, 'bajo': 1}
    severidad_max = max(sevs, key=lambda s: sev_orden.get(s, 0)) if sevs else 'ok'

    return jsonify({
        'ocs_sin_recibir': ocs_sin_recibir,
        'pagos_por_vencer': pagos_por_vencer,
        'solicitudes_pendientes': solicitudes_pendientes,
        'ocs_borrador_estancadas': ocs_borrador,
        'total': total,
        'severidad_max': severidad_max,
        'evaluado_en': hoy.isoformat(),
    })


# ─── REPORTE EJECUTIVO COMPRAS (Sprint 4) ────────────────────────────────────

@bp.route('/api/compras/reporte-ejecutivo', methods=['GET'])
def reporte_ejecutivo_compras():
    """Reporte gerencial mensual: top proveedores, gasto por categoría,
    pasivo corriente, variaciones de precio.

    Query: ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD (default últimos 12 meses)
    """
    u, err, code = _require_compras_session()
    if err:
        return err, code

    from datetime import date, timedelta
    desde = (request.args.get('desde') or
             (date.today() - timedelta(days=365)).isoformat())
    hasta = request.args.get('hasta') or date.today().isoformat()

    conn = get_db(); c = conn.cursor()

    # ── Top 10 proveedores por gasto ───────────────────────────────────
    c.execute("""
        SELECT proveedor,
               COUNT(*) as ocs_count,
               COALESCE(SUM(valor_total), 0) as gasto_total,
               COALESCE(SUM(CASE WHEN estado IN ('Recibida','Pagada') THEN 1 ELSE 0 END), 0) as cumplidas,
               MAX(fecha) as ultima_oc
        FROM ordenes_compra
        WHERE fecha >= ? AND fecha <= ?
              AND estado != 'Rechazada' AND estado != 'Borrador'
        GROUP BY proveedor
        ORDER BY gasto_total DESC LIMIT 10
    """, (desde, hasta + 'T23:59:59'))
    top_proveedores = []
    for r in c.fetchall():
        cumplimiento = round(100.0 * (r[3] or 0) / r[1], 1) if r[1] > 0 else 0
        top_proveedores.append({
            'proveedor': r[0], 'ocs_count': r[1],
            'gasto_total': round(r[2] or 0, 2),
            'cumplidas': r[3], 'cumplimiento_pct': cumplimiento,
            'ultima_oc': r[4],
        })

    # ── Gasto por categoría / mes ──────────────────────────────────────
    c.execute("""
        SELECT substr(fecha, 1, 7) as mes,
               COALESCE(categoria, 'Sin categoría') as cat,
               SUM(valor_total) as total
        FROM ordenes_compra
        WHERE fecha >= ? AND fecha <= ? AND estado != 'Rechazada'
        GROUP BY mes, cat
        ORDER BY mes DESC, total DESC
    """, (desde, hasta + 'T23:59:59'))
    gasto_categoria_mes = [
        {'mes': r[0], 'categoria': r[1], 'total': round(r[2] or 0, 2)}
        for r in c.fetchall()
    ]

    # ── Pasivo corriente: OCs Recibidas/Parciales pendientes de pago ──
    c.execute("""
        SELECT oc.numero_oc, oc.proveedor, oc.valor_total, oc.fecha_recepcion,
               COALESCE((SELECT SUM(monto) FROM pagos_oc WHERE numero_oc=oc.numero_oc), 0) as pagado
        FROM ordenes_compra oc
        WHERE oc.estado IN ('Recibida', 'Parcial')
        ORDER BY oc.fecha_recepcion ASC
    """)
    pasivo_items = []
    pasivo_total = 0
    for r in c.fetchall():
        pendiente = float(r[2] or 0) - float(r[4] or 0)
        if pendiente > 0.01:
            pasivo_items.append({
                'numero_oc': r[0], 'proveedor': r[1],
                'valor_total': r[2], 'pagado': r[4],
                'pendiente': round(pendiente, 2),
                'fecha_recepcion': r[3],
            })
            pasivo_total += pendiente

    # ── Variaciones de precio MP > 15% en últimos 6 meses ──────────────
    c.execute("""
        SELECT codigo_mp,
               MIN(precio_kg) as min_precio,
               MAX(precio_kg) as max_precio,
               COUNT(*) as n_compras,
               (SELECT precio_kg FROM precios_mp_historico p2
                WHERE p2.codigo_mp = p1.codigo_mp ORDER BY fecha DESC LIMIT 1) as ultimo
        FROM precios_mp_historico p1
        WHERE fecha >= date('now', '-6 months')
        GROUP BY codigo_mp
        HAVING n_compras >= 2
    """)
    variaciones = []
    for r in c.fetchall():
        cod, mn, mx, n, ult = r
        if mn and mn > 0 and mx > mn:
            var_pct = ((mx - mn) / mn) * 100
            if var_pct > 15:
                variaciones.append({
                    'codigo_mp': cod, 'precio_min': mn, 'precio_max': mx,
                    'precio_actual': ult, 'compras_periodo': n,
                    'variacion_pct': round(var_pct, 1),
                    'severidad': 'critico' if var_pct > 50 else
                                 ('alto' if var_pct > 30 else 'medio'),
                })
    variaciones.sort(key=lambda x: x['variacion_pct'], reverse=True)

    # ── Totales mes actual ─────────────────────────────────────────────
    c.execute("""
        SELECT COUNT(*), COALESCE(SUM(valor_total), 0)
        FROM ordenes_compra
        WHERE fecha >= date('now', 'start of month') AND estado != 'Rechazada'
    """)
    mes_actual = c.fetchone()

    return jsonify({
        'rango': {'desde': desde, 'hasta': hasta},
        'top_proveedores': top_proveedores,
        'gasto_categoria_mes': gasto_categoria_mes,
        'pasivo_corriente': {
            'items': pasivo_items[:50],  # limitar payload
            'total_items': len(pasivo_items),
            'total_pendiente': round(pasivo_total, 2),
        },
        'variaciones_precio': variaciones[:20],
        'mes_actual': {
            'ocs_count': mes_actual[0] if mes_actual else 0,
            'gasto_total': round(mes_actual[1] if mes_actual else 0, 2),
        },
    })


# ─── COTIZACIONES (Sprint 5) ─────────────────────────────────────────────────
# Workflow opcional pre-OC: para items grandes, comparar 3 cotizaciones antes
# de generar la OC. Cada ronda tiene un ronda_id que agrupa N cotizaciones de
# distintos proveedores.

@bp.route('/api/compras/cotizaciones/rondas', methods=['POST'])
def crear_ronda_cotizaciones():
    """Crea una nueva ronda de cotizaciones (3 proveedores).

    Body: {descripcion, proveedores: [{nombre, condiciones, tiempo_entrega_dias?}]}
    """
    u, err, code = _require_compras_write()
    if err:
        return err, code
    d = request.get_json() or {}
    descripcion = (d.get('descripcion') or '').strip()
    proveedores = d.get('proveedores', [])
    if not descripcion or not proveedores:
        return jsonify({'error': 'descripcion y proveedores requeridos'}), 400
    if len(proveedores) < 2:
        return jsonify({'error': 'Mínimo 2 proveedores para comparar'}), 400

    from datetime import datetime as _dt
    ronda_id = f"COT-{_dt.now().strftime('%Y%m%d%H%M%S')}"

    conn = get_db(); c = conn.cursor()
    creadas = []
    for prov in proveedores:
        nombre = (prov.get('nombre') or '').strip()
        if not nombre:
            continue
        c.execute("""INSERT INTO cotizaciones
                     (ronda_id, proveedor, descripcion, condiciones,
                      tiempo_entrega_dias, creado_por, estado)
                     VALUES (?, ?, ?, ?, ?, ?, 'Pendiente')""",
                  (ronda_id, nombre, descripcion,
                   prov.get('condiciones', ''),
                   int(prov.get('tiempo_entrega_dias') or 0),
                   u))
        creadas.append({'id': c.lastrowid, 'proveedor': nombre})
    conn.commit()
    return jsonify({
        'ok': True, 'ronda_id': ronda_id,
        'cotizaciones': creadas, 'count': len(creadas),
    }), 201


@bp.route('/api/compras/cotizaciones/<int:cot_id>', methods=['PATCH'])
def actualizar_cotizacion(cot_id):
    """Actualiza una cotización con la respuesta del proveedor.

    Body: {valor_total, condiciones?, tiempo_entrega_dias?, archivo?}
    """
    u, err, code = _require_compras_write()
    if err:
        return err, code
    d = request.get_json() or {}
    valor = float(d.get('valor_total') or 0)
    if valor <= 0:
        return jsonify({'error': 'valor_total > 0 requerido'}), 400

    conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE cotizaciones SET
                    valor_total=?, fecha_recibida=datetime('now', 'utc'),
                    condiciones=COALESCE(?, condiciones),
                    tiempo_entrega_dias=COALESCE(?, tiempo_entrega_dias),
                    archivo=COALESCE(?, archivo),
                    estado='Recibida'
                 WHERE id=?""",
              (valor, d.get('condiciones'), d.get('tiempo_entrega_dias'),
               d.get('archivo'), cot_id))
    if c.rowcount == 0:
        return jsonify({'error': 'Cotización no encontrada'}), 404
    conn.commit()
    return jsonify({'ok': True, 'id': cot_id, 'estado': 'Recibida'})


@bp.route('/api/compras/cotizaciones/rondas/<ronda_id>', methods=['GET'])
def get_ronda(ronda_id):
    """Lista las cotizaciones de una ronda con comparación lado a lado."""
    u, err, code = _require_compras_session()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, proveedor, fecha_solicitud, fecha_recibida,
                        valor_total, condiciones, descripcion,
                        tiempo_entrega_dias, ganadora, numero_oc, estado
                 FROM cotizaciones WHERE ronda_id=? ORDER BY valor_total ASC""",
              (ronda_id,))
    cols = ['id', 'proveedor', 'fecha_solicitud', 'fecha_recibida',
            'valor_total', 'condiciones', 'descripcion',
            'tiempo_entrega_dias', 'ganadora', 'numero_oc', 'estado']
    cotizaciones = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({
        'ronda_id': ronda_id,
        'cotizaciones': cotizaciones,
        'count': len(cotizaciones),
        'completadas': sum(1 for x in cotizaciones if x['estado'] == 'Recibida'),
    })


@bp.route('/api/compras/cotizaciones/<int:cot_id>/elegir-ganadora', methods=['POST'])
def elegir_ganadora(cot_id):
    """Marca una cotización como ganadora; las demás de la misma ronda quedan
    como 'No seleccionada'. Opcionalmente vincula con número_oc al generar OC.
    """
    u, err, code = _require_compras_write()
    if err:
        return err, code
    d = request.get_json() or {}
    numero_oc = (d.get('numero_oc') or '').strip()

    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT ronda_id, proveedor, valor_total, descripcion
                 FROM cotizaciones WHERE id=?""", (cot_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Cotización no encontrada'}), 404
    ronda_id, prov_ganador, valor_ganador, descripcion = row

    # Marcar ganadora + las demás como no seleccionadas
    c.execute("""UPDATE cotizaciones SET ganadora=1,
                    numero_oc=COALESCE(?, numero_oc), estado='Ganadora'
                 WHERE id=?""", (numero_oc, cot_id))
    c.execute("""UPDATE cotizaciones SET ganadora=0, estado='No seleccionada'
                 WHERE ronda_id=? AND id!=? AND estado != 'No seleccionada'""",
              (ronda_id, cot_id))
    try:
        audit_log(c, usuario=u, accion='ELEGIR_COTIZACION_GANADORA',
                  tabla='cotizaciones', registro_id=cot_id,
                  despues={'ronda_id': ronda_id,
                            'proveedor_ganador': (prov_ganador or '')[:200],
                            'valor_ganador': valor_ganador,
                            'numero_oc_vinculada': numero_oc or None,
                            'descripcion': (descripcion or '')[:200]},
                  detalle=f"Eligió cotización id={cot_id} (ronda {ronda_id}) · "
                          f"ganador {prov_ganador} · {valor_ganador or 0:.0f}")
    except Exception as e:
        log.warning('audit_log ELEGIR_COTIZACION_GANADORA fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'cot_id': cot_id, 'ronda_id': ronda_id,
                    'numero_oc': numero_oc})


@bp.route('/api/compras/cotizaciones/rondas', methods=['GET'])
def listar_rondas():
    """Lista las últimas 50 rondas con resumen de cada una."""
    u, err, code = _require_compras_session()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("""
        SELECT ronda_id, MAX(fecha_solicitud), MAX(descripcion),
               COUNT(*), SUM(CASE WHEN estado='Recibida' THEN 1 ELSE 0 END),
               MAX(CASE WHEN ganadora=1 THEN proveedor ELSE NULL END),
               MIN(CASE WHEN ganadora=1 THEN valor_total ELSE NULL END)
        FROM cotizaciones GROUP BY ronda_id
        ORDER BY MAX(fecha_solicitud) DESC LIMIT 50
    """)
    rondas = [
        {
            'ronda_id': r[0], 'fecha': r[1], 'descripcion': r[2],
            'total_cotizaciones': r[3], 'recibidas': r[4],
            'ganadora_proveedor': r[5], 'valor_ganador': r[6],
        }
        for r in c.fetchall()
    ]
    return jsonify({'rondas': rondas, 'count': len(rondas)})


# ─── CENTRO DE COSTOS (Sprint 5) ─────────────────────────────────────────────

@bp.route('/api/compras/centros-costos', methods=['GET'])
def listar_centros_costos():
    """Devuelve los centros de costos en uso + KPIs por centro."""
    u, err, code = _require_compras_session()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("""
        SELECT COALESCE(centro_costos, 'general') as cc,
               COUNT(*) as ocs, SUM(valor_total) as total
        FROM ordenes_compra
        WHERE estado != 'Rechazada' AND estado != 'Borrador'
        GROUP BY cc ORDER BY total DESC
    """)
    centros = [
        {'centro_costos': r[0], 'ocs': r[1], 'total': round(r[2] or 0, 2)}
        for r in c.fetchall()
    ]
    return jsonify({'centros': centros, 'count': len(centros)})
