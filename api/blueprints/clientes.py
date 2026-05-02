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
from database import get_db
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
from http_helpers import validate_money
from audit_helpers import audit_log
from templates_py.clientes_html import CLIENTES_HTML

bp = Blueprint('clientes', __name__)


def _require_clientes_access():
    """Helper de auth · audit zero-error 2-may-2026.

    Antes 14 endpoints `/api/clientes*`, `/api/pedidos`, `/api/despachos`,
    `/api/stock-pt`, `/api/aliados/*` no validaban sesión. Cualquier
    visitante con cookie de OTRO módulo válida (ej. RRHH) leía PII
    completa: NIT, teléfono, email, historial 360°, cartera.

    Retorna (None, None) si OK, o (Response, code) si rechaza.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    u = session.get('compras_user', '')
    if u not in CLIENTES_ACCESS:
        return jsonify({'error': 'Sin acceso al módulo Clientes'}), 403
    return None, None


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
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('nombre'):
            return jsonify({'error': 'Nombre requerido'}), 400
        c.execute("SELECT COUNT(*) FROM clientes"); n = (c.fetchone()[0] or 0) + 1
        codigo = d.get('codigo') or f"CLI-{n:03d}"
        # Validar descuento_pct razonable (0-100)
        try:
            descuento = float(d.get('descuento_pct', 0))
        except (TypeError, ValueError):
            return jsonify({'error': 'descuento_pct inválido'}), 400
        if descuento < 0 or descuento > 100:
            return jsonify({'error': 'descuento_pct debe estar entre 0 y 100'}), 400
        try:
            c.execute("""INSERT INTO clientes
                         (codigo,nombre,empresa,tipo,contacto,email,telefono,nit,
                          condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones,ciudad,
                          categoria_profesional,canal_captacion,redes_sociales,notas_seguimiento)
                         VALUES (?,?,?,?,?,?,?,?,?,?,1,datetime('now'),?,?,?,?,?,?)""",
                      (codigo, d['nombre'], d.get('empresa','ANIMUS'), d.get('tipo','Distribuidor'),
                       d.get('contacto',''), d.get('email',''), d.get('telefono',''),
                       d.get('nit',''), d.get('condiciones_pago','Pago anticipado'),
                       descuento, d.get('observaciones',''), d.get('ciudad',''),
                       d.get('categoria_profesional',''), d.get('canal_captacion',''),
                       json.dumps(d.get('redes_sociales',{})), d.get('notas_seguimiento','')))
            cid_new = c.lastrowid
            try:
                audit_log(c, usuario=session.get('compras_user','sistema'),
                          accion='CREAR_CLIENTE', tabla='clientes', registro_id=cid_new,
                          despues={'codigo': codigo, 'nombre': d['nombre'][:200],
                                    'empresa': d.get('empresa','ANIMUS'),
                                    'tipo': d.get('tipo','Distribuidor'),
                                    'descuento_pct': descuento},
                          detalle=f"Creó cliente {codigo} · {d['nombre'][:100]}")
            except Exception:
                pass
            conn.commit()
            return jsonify({'message': f"Cliente creado", 'codigo': codigo, 'id': cid_new}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
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
                        COALESCE(cl.redes_sociales,'{{}}') as redes_sociales,
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
    return jsonify({'clientes': clientes})

@bp.route('/api/clientes/<int:cid>', methods=['GET','PUT'])
def handle_cliente_detalle(cid):
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    if request.method == 'PUT':
        d = request.json or {}
        # Capturar antes para audit
        antes_row = c.execute("""SELECT codigo, nombre, empresa, descuento_pct, activo
                                  FROM clientes WHERE id=?""", (cid,)).fetchone()
        if not antes_row:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        antes = dict(antes_row)
        # Validar descuento_pct si viene
        if 'descuento_pct' in d:
            try:
                desc = float(d['descuento_pct'])
            except (TypeError, ValueError):
                return jsonify({'error': 'descuento_pct inválido'}), 400
            if desc < 0 or desc > 100:
                return jsonify({'error': 'descuento_pct debe estar entre 0 y 100'}), 400
        campos = ['nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','observaciones','activo']
        sets = []; vals = []
        for campo in campos:
            if campo in d: sets.append(f"{campo}=?"); vals.append(d[campo])
        if sets:
            vals.append(cid)
            c.execute(f"UPDATE clientes SET {','.join(sets)} WHERE id=?", vals)
            try:
                audit_log(c, usuario=session.get('compras_user','sistema'),
                          accion='ACTUALIZAR_CLIENTE', tabla='clientes', registro_id=cid,
                          antes=antes,
                          despues={k: d.get(k) for k in d if k in campos},
                          detalle=f"Actualizó cliente id={cid} ({antes.get('codigo','')})")
            except Exception:
                pass
            conn.commit()
        return jsonify({'message': 'Cliente actualizado'})
    c.execute("SELECT id,codigo,nombre,empresa,tipo,contacto,email,telefono,nit,condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones FROM clientes WHERE id=?", (cid,))
    row = c.fetchone()
    if not row: return jsonify({'error': 'No encontrado'}), 404
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','activo','fecha_creacion','observaciones']
    return jsonify({'cliente': dict(zip(cols, row))})

@bp.route('/api/clientes/<int:cid>/historial')
def handle_cliente_historial(cid):
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,valor_total,fecha_despacho FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 50", (cid,))
    cols = ['numero','fecha','estado','valor_total','fecha_despacho']
    pedidos = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'pedidos': pedidos})

@bp.route('/api/clientes/<int:cid>/stats')
def handle_cliente_stats(cid):
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    row = c.fetchone()
    return jsonify({'total_pedidos': row[0], 'valor_total': row[1], 'ultimo_pedido': row[2]})

@bp.route('/api/clientes/alertas-recompra')
def clientes_alertas_recompra():
    """Clientes con >N dias sin pedido — churn detection."""
    err, code = _require_clientes_access()
    if err: return err, code
    umbral = int(request.args.get('dias', 75))
    conn = get_db(); c = conn.cursor()
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
    return jsonify({'alertas': resultado, 'umbral_dias': umbral})

@bp.route('/api/clientes/<int:cid>/ficha360')
def cliente_ficha_360(cid):
    """Cliente 360: datos + stats + historial pedidos recientes + items."""
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    # Audit zero-error 2-may-2026: combinado cliente + stats en una sola query
    # con LEFT JOIN agregado · ahorra 1 roundtrip por GET.
    c.execute("""
        SELECT cl.id, cl.codigo, cl.nombre, cl.empresa, cl.tipo, cl.contacto,
               cl.email, cl.telefono, cl.nit, cl.condiciones_pago,
               cl.descuento_pct, cl.observaciones, cl.fecha_creacion,
               COALESCE(s.total_pedidos, 0) as total_pedidos,
               COALESCE(s.valor_total, 0) as valor_total,
               s.ultimo_ped, s.primer_ped
        FROM clientes cl
        LEFT JOIN (
            SELECT cliente_id, COUNT(*) as total_pedidos,
                   SUM(valor_total) as valor_total,
                   MAX(fecha) as ultimo_ped, MIN(fecha) as primer_ped
            FROM pedidos GROUP BY cliente_id
        ) s ON s.cliente_id = cl.id
        WHERE cl.id=? AND cl.activo=1
    """, (cid,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    cols_cli = ['id','codigo','nombre','empresa','tipo','contacto','email',
                'telefono','nit','condiciones_pago','descuento_pct','observaciones','fecha_creacion']
    cliente = dict(zip(cols_cli, row[:len(cols_cli)]))
    total_ped = row[13] or 0
    valor_total = row[14] or 0
    ultimo_ped = row[15]
    primer_ped = row[16]
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

@bp.route('/api/aliados/canal-salud')
def aliados_canal_salud():
    """Capa 1 — Salud del canal aliados: revenue MoM, retención, concentración, activos vs dormidos."""
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    try:
        hoy       = datetime.now()
        mes_ini   = hoy.replace(day=1).strftime("%Y-%m-%d")
        # Primer día del mes anterior
        primer_mes_ant = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        anio_ini  = hoy.replace(month=1, day=1).strftime("%Y-%m-%d")
        hace60    = (hoy - timedelta(days=60)).strftime("%Y-%m-%d")
        hace90    = (hoy - timedelta(days=90)).strftime("%Y-%m-%d")
        hoy_s     = hoy.strftime("%Y-%m-%d")

        BASE = "cl.empresa='ANIMUS' AND cl.activo=1 AND p.estado NOT IN ('Cancelado','Borrador')"

        # Revenue mes actual
        rev_mes = c.execute(f"""
            SELECT COALESCE(SUM(p.valor_total),0) FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE {BASE} AND p.fecha >= ?
        """, (mes_ini,)).fetchone()[0] or 0

        # Revenue mes anterior
        rev_ant = c.execute(f"""
            SELECT COALESCE(SUM(p.valor_total),0) FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE {BASE} AND p.fecha >= ? AND p.fecha < ?
        """, (primer_mes_ant, mes_ini)).fetchone()[0] or 0

        pct_mom = round((rev_mes - rev_ant) / rev_ant * 100, 1) if rev_ant > 0 else (100.0 if rev_mes > 0 else 0.0)

        # Revenue acumulado año
        rev_anio = c.execute(f"""
            SELECT COALESCE(SUM(p.valor_total),0) FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE {BASE} AND p.fecha >= ?
        """, (anio_ini,)).fetchone()[0] or 0

        # Total aliados activos en sistema
        total_aliados = c.execute(
            "SELECT COUNT(*) FROM clientes WHERE empresa='ANIMUS' AND activo=1"
        ).fetchone()[0] or 0

        # Aliados que compraron en últimos 60 días
        activos_ids = [r[0] for r in c.execute(f"""
            SELECT DISTINCT cl.id FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE {BASE} AND p.fecha >= ?
        """, (hace60,)).fetchall()]
        n_activos = len(activos_ids)
        n_dormidos = max(total_aliados - n_activos, 0)

        # Revenue de aliados dormidos (valor en riesgo)
        valor_en_riesgo = 0
        if n_dormidos > 0:
            ph = ','.join('?' * len(activos_ids)) if activos_ids else "''"
            excl = f"AND cl.id NOT IN ({ph})" if activos_ids else ""
            valor_en_riesgo = c.execute(f"""
                SELECT COALESCE(SUM(p.valor_total),0) FROM clientes cl
                JOIN pedidos p ON p.cliente_id=cl.id
                WHERE {BASE} AND p.fecha >= ? {excl}
            """, [anio_ini] + activos_ids).fetchone()[0] or 0

        # Tasa de retención: aliados que compraron en últimos 90d Y tenían historial previo
        ret_count = c.execute(f"""
            SELECT COUNT(DISTINCT p.cliente_id) FROM pedidos p
            JOIN clientes cl ON p.cliente_id=cl.id
            WHERE cl.empresa='ANIMUS' AND cl.activo=1
              AND p.estado NOT IN ('Cancelado','Borrador')
              AND p.fecha >= ?
              AND EXISTS (
                  SELECT 1 FROM pedidos p2
                  WHERE p2.cliente_id=p.cliente_id
                    AND p2.estado NOT IN ('Cancelado','Borrador')
                    AND p2.fecha < ?
              )
        """, (hace90, hace90)).fetchone()[0] or 0

        aliados_con_historial = c.execute(f"""
            SELECT COUNT(DISTINCT cliente_id) FROM pedidos p
            JOIN clientes cl ON p.cliente_id=cl.id
            WHERE cl.empresa='ANIMUS' AND cl.activo=1
              AND p.estado NOT IN ('Cancelado','Borrador')
              AND p.fecha < ?
        """, (hace90,)).fetchone()[0] or 0

        tasa_ret = round(ret_count / aliados_con_historial * 100, 1) if aliados_con_historial > 0 else 0

        # Concentración por aliado (revenue histórico total)
        rev_ranking = c.execute(f"""
            SELECT cl.nombre, COALESCE(SUM(p.valor_total),0) as rev
            FROM clientes cl JOIN pedidos p ON p.cliente_id=cl.id
            WHERE {BASE}
            GROUP BY cl.id ORDER BY rev DESC
        """).fetchall()

        total_hist = sum(r[1] for r in rev_ranking) or 1
        top_aliados = [{'nombre': r[0], 'revenue': round(r[1], 0),
                        'pct': round(r[1] / total_hist * 100, 1)} for r in rev_ranking[:5]]
        conc_top1 = top_aliados[0]['pct'] if top_aliados else 0
        conc_top3 = round(sum(r['pct'] for r in top_aliados[:3]), 1)

        return jsonify({
            'revenue_mes_actual':  round(rev_mes, 0),
            'revenue_mes_anterior': round(rev_ant, 0),
            'pct_mom':             pct_mom,
            'revenue_anio':        round(rev_anio, 0),
            'total_aliados':       total_aliados,
            'aliados_activos':     n_activos,
            'aliados_dormidos':    n_dormidos,
            'valor_en_riesgo':     round(valor_en_riesgo, 0),
            'tasa_retencion':      tasa_ret,
            'concentracion_top1':  conc_top1,
            'concentracion_top3':  conc_top3,
            'top_aliados':         top_aliados,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/aliados/skus-segmento')
def aliados_skus_segmento():
    """Capa 3 — Top SKUs comprados por categoria_profesional de aliados ANIMUS.
    Retorna: { segmentos: [{categoria, total_revenue, total_pedidos, top_skus:[{sku,descripcion,uds,pedidos,revenue}]}] }
    """
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    try:
        # SKUs por categoría: join clientes -> pedidos -> pedidos_items
        rows = c.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(cl.categoria_profesional),''), 'Sin categoría') as cat,
                pi.sku,
                COALESCE(pi.descripcion, pi.sku) as descripcion,
                SUM(pi.cantidad) as uds,
                COUNT(DISTINCT p.numero) as pedidos,
                SUM(pi.subtotal) as revenue
            FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            JOIN pedidos_items pi ON pi.numero_pedido=p.numero
            WHERE cl.empresa='ANIMUS' AND cl.activo=1
              AND p.estado NOT IN ('Cancelado','Borrador')
            GROUP BY cat, pi.sku
            ORDER BY cat, revenue DESC
        """).fetchall()

        # Agrupar por categoría
        from collections import defaultdict
        cats = defaultdict(lambda: {'total_revenue':0,'total_pedidos':set(),'skus':[]})
        for (cat, sku, desc, uds, peds, rev) in rows:
            cats[cat]['total_revenue'] += rev or 0
            cats[cat]['skus'].append({
                'sku': sku,
                'descripcion': desc,
                'uds': int(uds or 0),
                'pedidos': int(peds or 0),
                'revenue': round(rev or 0, 0),
            })

        # Revenue total de pedidos por categoría (sin repetir pedido)
        rev_cat = c.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(cl.categoria_profesional),''), 'Sin categoría') as cat,
                COUNT(DISTINCT p.numero) as total_pedidos,
                SUM(p.valor_total) as rev_total
            FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE cl.empresa='ANIMUS' AND cl.activo=1
              AND p.estado NOT IN ('Cancelado','Borrador')
            GROUP BY cat
        """).fetchall()

        rev_cat_map = {r[0]: {'total_pedidos': int(r[1]), 'total_revenue': round(r[2] or 0, 0)} for r in rev_cat}

        segmentos = []
        for cat, data in sorted(cats.items(), key=lambda x: -x[1]['total_revenue']):
            meta = rev_cat_map.get(cat, {})
            segmentos.append({
                'categoria':      cat,
                'total_revenue':  meta.get('total_revenue', round(data['total_revenue'],0)),
                'total_pedidos':  meta.get('total_pedidos', 0),
                'top_skus':       data['skus'][:6],  # top 6 por revenue
            })

        return jsonify({'segmentos': segmentos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/aliados/scores')
def aliados_scores():
    """Capa 2 — Score individual por aliado: recencia, frecuencia, MoM, LTV relativo.
    Score 0-100:
      Recencia  (30 pts) — días desde última compra
      Frecuencia (25 pts) — intervalo medio entre pedidos
      MoM       (25 pts) — crecimiento revenue mes actual vs anterior
      LTV rel   (20 pts) — posición en ranking de revenue total
    """
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    try:
        hoy       = datetime.now()
        mes_ini   = hoy.replace(day=1).strftime("%Y-%m-%d")
        primer_mes_ant = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")

        # ── Traer todos los aliados activos ──────────────────────────────────
        aliados = c.execute("""
            SELECT id, nombre FROM clientes
            WHERE empresa='ANIMUS' AND activo=1
        """).fetchall()

        if not aliados:
            return jsonify({'scores': []})

        scores = []
        ltvs = []  # para calcular percentil LTV después

        for (aid, nombre) in aliados:
            BASE = "p.estado NOT IN ('Cancelado','Borrador') AND p.cliente_id=?"

            # Todas las fechas de pedido ordenadas
            fechas_rows = c.execute(
                f"SELECT fecha FROM pedidos WHERE {BASE} ORDER BY fecha ASC", (aid,)
            ).fetchall()
            fechas = [r[0][:10] for r in fechas_rows if r[0]]

            # Recencia: días desde última compra
            if fechas:
                from datetime import date as date_cls
                ultima = datetime.strptime(fechas[-1], "%Y-%m-%d")
                recencia_dias = (hoy - ultima).days
            else:
                recencia_dias = 9999

            # Frecuencia: intervalo medio entre pedidos consecutivos
            if len(fechas) >= 2:
                deltas = []
                for i in range(1, len(fechas)):
                    d1 = datetime.strptime(fechas[i-1], "%Y-%m-%d")
                    d2 = datetime.strptime(fechas[i],   "%Y-%m-%d")
                    deltas.append((d2 - d1).days)
                frecuencia_dias = round(sum(deltas) / len(deltas))
            elif len(fechas) == 1:
                frecuencia_dias = None
            else:
                frecuencia_dias = None

            # Predicción próxima compra
            if fechas and frecuencia_dias:
                ultima_dt = datetime.strptime(fechas[-1], "%Y-%m-%d")
                proxima_est = ultima_dt + timedelta(days=frecuencia_dias)
                dias_para_proxima = (proxima_est - hoy).days
                proxima_str = proxima_est.strftime("%Y-%m-%d")
            else:
                dias_para_proxima = None
                proxima_str = None

            # Revenue mes actual
            rev_mes = c.execute(
                f"SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE {BASE} AND fecha >= ?",
                (aid, mes_ini)
            ).fetchone()[0] or 0

            # Revenue mes anterior
            rev_ant = c.execute(
                f"SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE {BASE} AND fecha >= ? AND fecha < ?",
                (aid, primer_mes_ant, mes_ini)
            ).fetchone()[0] or 0

            mom_pct = round((rev_mes - rev_ant) / rev_ant * 100, 1) if rev_ant > 0 else (100.0 if rev_mes > 0 else 0.0)

            # LTV total histórico
            ltv = c.execute(
                f"SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE {BASE}",
                (aid,)
            ).fetchone()[0] or 0

            ltvs.append(ltv)

            scores.append({
                'id':              aid,
                'nombre':          nombre,
                'recencia_dias':   recencia_dias,
                'frecuencia_dias': frecuencia_dias,
                'rev_mes':         round(rev_mes, 0),
                'rev_mes_ant':     round(rev_ant, 0),
                'mom_pct':         mom_pct,
                'ltv':             round(ltv, 0),
                'proxima_est':     proxima_str,
                'dias_proxima':    dias_para_proxima,
            })

        # ── Score compuesto 0-100 ─────────────────────────────────────────────
        max_ltv = max(ltvs) if ltvs else 1
        # Percentiles LTV (top 20%, 40%, 60%)
        sorted_ltvs = sorted(ltvs, reverse=True)
        n = len(sorted_ltvs)
        ltv_p20 = sorted_ltvs[max(0, int(n*0.2)-1)]
        ltv_p40 = sorted_ltvs[max(0, int(n*0.4)-1)]
        ltv_p60 = sorted_ltvs[max(0, int(n*0.6)-1)]

        for s in scores:
            # Recencia (30 pts)
            r = s['recencia_dias']
            if r <= 30:
                pts_rec = 30
            elif r <= 60:
                pts_rec = 18
            elif r <= 90:
                pts_rec = 8
            else:
                pts_rec = 0

            # Frecuencia (25 pts)
            f = s['frecuencia_dias']
            if f is None:
                pts_frec = 8  # solo 1 compra → crédito parcial
            elif f <= 30:
                pts_frec = 25
            elif f <= 60:
                pts_frec = 17
            elif f <= 90:
                pts_frec = 10
            else:
                pts_frec = 3

            # MoM (25 pts)
            m = s['mom_pct']
            if m >= 20:
                pts_mom = 25
            elif m > 0:
                pts_mom = 15
            elif m == 0:
                pts_mom = 8
            else:
                pts_mom = 0

            # LTV relativo (20 pts)
            ltv = s['ltv']
            if ltv >= ltv_p20:
                pts_ltv = 20
            elif ltv >= ltv_p40:
                pts_ltv = 13
            elif ltv >= ltv_p60:
                pts_ltv = 7
            else:
                pts_ltv = 2

            s['score'] = pts_rec + pts_frec + pts_mom + pts_ltv
            s['score_detalle'] = {
                'recencia': pts_rec,
                'frecuencia': pts_frec,
                'mom': pts_mom,
                'ltv_rel': pts_ltv,
            }

        # Ordenar por score desc
        scores.sort(key=lambda x: x['score'], reverse=True)

        return jsonify({'scores': scores})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/aliados/analytics')
def aliados_analytics():
    """Ventas mensuales por aliado, frecuencia de compra y top SKUs."""
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
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

        return jsonify({
            'resumen': resumen,
            'ventas_mes': ventas_mes,
            'frecuencia': frecuencia
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/pedidos', methods=['GET','POST'])
def handle_pedidos():
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('cliente_id'):
            return jsonify({'error': 'cliente_id requerido'}), 400
        # Money sanity validation por item · audit zero-error 2-may-2026
        items_raw = d.get('items') or []
        items_clean = []
        for it in items_raw:
            cantidad, err = validate_money(it.get('cantidad', 0), allow_zero=False,
                                              max_value=100_000, field_name='cantidad')
            if err: return jsonify(err), 400
            precio, err = validate_money(it.get('precio_unitario', 0), allow_zero=True,
                                            field_name='precio_unitario')
            if err: return jsonify(err), 400
            subtotal_raw = it.get('subtotal', cantidad * precio)
            subtotal, err = validate_money(subtotal_raw, allow_zero=True,
                                              field_name='subtotal')
            if err: return jsonify(err), 400
            items_clean.append({
                'sku': (it.get('sku') or '')[:80],
                'descripcion': (it.get('descripcion') or '')[:200],
                'cantidad': int(cantidad),
                'precio_unitario': precio,
                'subtotal': subtotal,
            })
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM pedidos WHERE numero LIKE ?", (f"PED-{datetime.now().strftime('%Y')}-%",)); n = (c.fetchone()[0] or 0) + 1
        numero = f"PED-{datetime.now().strftime('%Y')}-{n:04d}"
        valor_total = sum(it['subtotal'] for it in items_clean)
        # Validar que cliente_id existe
        cli_row = c.execute("SELECT id, nombre FROM clientes WHERE id=? AND activo=1",
                            (d['cliente_id'],)).fetchone()
        if not cli_row:
            return jsonify({'error': 'cliente_id no existe o está inactivo'}), 400
        c.execute("""INSERT INTO pedidos (numero,cliente_id,fecha,fecha_entrega_est,estado,empresa,valor_total,observaciones,creado_por)
                     VALUES (?,?,datetime('now'),?,?,?,?,?,?)""",
                  (numero, d['cliente_id'], d.get('fecha_entrega_est',''), d.get('estado','Confirmado'),
                   d.get('empresa','ANIMUS'), valor_total, d.get('observaciones',''), session.get('compras_user','sistema')))
        for it in items_clean:
            c.execute("INSERT INTO pedidos_items (numero_pedido,sku,descripcion,cantidad,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero, it['sku'], it['descripcion'], it['cantidad'], it['precio_unitario'], it['subtotal']))
        try:
            audit_log(c, usuario=session.get('compras_user','sistema'),
                      accion='CREAR_PEDIDO', tabla='pedidos', registro_id=numero,
                      despues={'cliente_id': d['cliente_id'],
                                'cliente_nombre': cli_row[1][:100] if cli_row else '',
                                'empresa': d.get('empresa','ANIMUS'),
                                'estado': d.get('estado','Confirmado'),
                                'valor_total': valor_total,
                                'items_count': len(items_clean)},
                      detalle=f"Creó pedido {numero} · {cli_row[1] if cli_row else ''} · "
                              f"${valor_total/1_000_000:.1f}M · {len(items_clean)} items")
        except Exception:
            pass
        conn.commit()
        return jsonify({'message': f'Pedido {numero} creado', 'numero': numero}), 201
    estado = request.args.get('estado')
    q = "SELECT p.numero,c.nombre,p.fecha,p.estado,p.valor_total,p.empresa,p.fecha_entrega_est,c.codigo as cliente_codigo,COALESCE(p.monto_pagado,0) as monto_pagado,COALESCE(p.estado_pago,'Pendiente') as estado_pago,c.id as cliente_id FROM pedidos p LEFT JOIN clientes c ON p.cliente_id=c.id"
    params = []
    if estado: q += " WHERE p.estado=?"; params.append(estado)
    q += " ORDER BY p.fecha DESC LIMIT 100"
    c.execute(q, params)
    cols = ['numero','cliente','fecha','estado','valor_total','empresa','fecha_entrega_est','cliente_codigo','monto_pagado','estado_pago','cliente_id']
    rows = c.fetchall()
    return jsonify({'pedidos': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/pedidos/<numero>', methods=['GET','PATCH','DELETE'])
def handle_pedido_detalle(numero):
    err, code = _require_clientes_access()
    if err: return err, code
    if request.method == 'DELETE':
        usuario_act = session.get('compras_user', '')
        if usuario_act not in ADMIN_USERS:
            return jsonify({'error':'Solo admins'}), 403
        conn = get_db(); c = conn.cursor()
        # Audit zero-error: guard contra eliminar pedido despachado
        # (perdería trazabilidad despacho→cliente para recall).
        antes_row = c.execute(
            "SELECT numero, cliente_id, estado, valor_total FROM pedidos WHERE numero=?",
            (numero,)).fetchone()
        if not antes_row:
            return jsonify({'error':'No encontrado'}), 404
        antes = dict(antes_row)
        if (antes.get('estado') or '') in ('Despachado', 'Entregado', 'Pagada', 'Pagado'):
            return jsonify({
                'error': f"Pedido en estado '{antes.get('estado')}' no se puede eliminar (trazabilidad). "
                          f"Cambia el estado a 'Cancelado' en su lugar.",
                'codigo': 'PEDIDO_DESPACHADO_NO_ELIMINABLE'
            }), 409
        # Verificar que no tiene despachos
        despachos = c.execute(
            "SELECT COUNT(*) FROM despachos WHERE numero_pedido=?", (numero,)
        ).fetchone()[0]
        if despachos > 0:
            return jsonify({
                'error': f'Pedido tiene {despachos} despacho(s) asociado(s) · no se puede eliminar',
                'codigo': 'PEDIDO_CON_DESPACHOS'
            }), 409
        c.execute('DELETE FROM pedidos_items WHERE numero_pedido=?', (numero,))
        c.execute('DELETE FROM pedidos WHERE numero=?', (numero,))
        try:
            audit_log(c, usuario=usuario_act, accion='ELIMINAR_PEDIDO',
                      tabla='pedidos', registro_id=numero, antes=antes,
                      detalle=f"Eliminó pedido {numero} (estado={antes.get('estado','')})")
        except Exception:
            pass
        conn.commit()
        return jsonify({'ok':True, 'eliminado':numero})
    conn = get_db(); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}
        # Capturar antes para audit (cambios financieros · monto_pagado/estado/factura)
        antes_row = c.execute(
            "SELECT estado, COALESCE(monto_pagado,0), COALESCE(estado_pago,''), COALESCE(numero_factura,'') "
            "FROM pedidos WHERE numero=?", (numero,)).fetchone()
        if not antes_row:
            return jsonify({'error': 'Pedido no encontrado'}), 404
        antes = {'estado': antes_row[0], 'monto_pagado': antes_row[1],
                 'estado_pago': antes_row[2], 'numero_factura': antes_row[3]}
        # Validar money en monto_pagado si viene
        if 'monto_pagado' in d:
            mp_v, err = validate_money(d['monto_pagado'], allow_zero=True,
                                          field_name='monto_pagado')
            if err:
                return jsonify(err), 400
        sets = []; vals = []
        if d.get('estado'): sets.append('estado=?'); vals.append(d['estado'])
        if 'monto_pagado' in d:
            sets.append('monto_pagado=?'); vals.append(float(d['monto_pagado']))
        if d.get('estado_pago'): sets.append('estado_pago=?'); vals.append(d['estado_pago'])
        if d.get('numero_factura'): sets.append('numero_factura=?'); vals.append(d['numero_factura'])
        if sets:
            vals.append(numero)
            c.execute(f"UPDATE pedidos SET {','.join(sets)} WHERE numero=?", vals)
            try:
                audit_log(c, usuario=session.get('compras_user',''),
                          accion='ACTUALIZAR_PEDIDO', tabla='pedidos',
                          registro_id=numero, antes=antes,
                          despues={k: d.get(k) for k in d
                                    if k in ('estado','monto_pagado','estado_pago','numero_factura')},
                          detalle=f"Actualizó pedido {numero}")
            except Exception:
                pass
            conn.commit()
        return jsonify({'message': f'Pedido {numero} actualizado'})
    c.execute("SELECT p.*,cl.nombre as cliente_nombre FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id WHERE p.numero=?", (numero,))
    row = c.fetchone()
    if not row: return jsonify({'error': 'No encontrado'}), 404
    cols = [d[0] for d in c.description]
    pedido = dict(zip(cols, row))
    c.execute("SELECT sku,descripcion,cantidad,precio_unitario,subtotal,lote_pt FROM pedidos_items WHERE numero_pedido=?", (numero,))
    items = [dict(zip(['sku','descripcion','cantidad','precio_unitario','subtotal','lote_pt'], r)) for r in c.fetchall()]
    return jsonify({'pedido': pedido, 'items': items})

@bp.route('/api/stock-pt', methods=['GET','POST'])
def handle_stock_pt():
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('sku'):
            return jsonify({'error': 'SKU requerido'}), 400
        # Validar unidades (entero positivo) y precio_base (money)
        try:
            unidades = int(d.get('unidades_inicial', d.get('unidades_disponible', 0)))
        except (TypeError, ValueError):
            return jsonify({'error': 'unidades inválidas'}), 400
        if unidades <= 0:
            return jsonify({'error': 'unidades debe ser > 0'}), 400
        precio_base, err = validate_money(d.get('precio_base', 0), allow_zero=True,
                                            field_name='precio_base')
        if err:
            return jsonify(err), 400
        # Idempotency: si ya existe stock_pt con mismo sku+lote_produccion, no duplicar
        lote_prod = (d.get('lote_produccion') or '').strip()
        if lote_prod:
            existing = c.execute(
                "SELECT id FROM stock_pt WHERE sku=? AND lote_produccion=? AND estado='Disponible'",
                (d['sku'], lote_prod)).fetchone()
            if existing:
                return jsonify({
                    'error': f"Ya existe stock PT con SKU={d['sku']} lote={lote_prod}",
                    'codigo': 'STOCK_PT_DUPLICADO'
                }), 409
        c.execute("""INSERT INTO stock_pt (sku,descripcion,lote_produccion,fecha_produccion,unidades_inicial,unidades_disponible,precio_base,empresa,estado,observaciones)
                     VALUES (?,?,?,datetime('now'),?,?,?,?,?,?)""",
                  (d['sku'], d.get('descripcion',''), lote_prod, unidades, unidades,
                   precio_base, d.get('empresa','ANIMUS'), 'Disponible', d.get('observaciones','')))
        spt_id = c.lastrowid
        try:
            audit_log(c, usuario=session.get('compras_user', 'sistema'),
                      accion='CREAR_STOCK_PT', tabla='stock_pt', registro_id=spt_id,
                      despues={'sku': d['sku'], 'lote_produccion': lote_prod,
                                'unidades': unidades, 'precio_base': precio_base,
                                'empresa': d.get('empresa', 'ANIMUS')},
                      detalle=f"Registró stock PT {d['sku']} lote={lote_prod} · {unidades} uds")
        except Exception:
            pass
        conn.commit()
        return jsonify({'message': f"Stock PT registrado: {d['sku']} — {unidades} uds",
                        'id': spt_id}), 201
    c.execute("SELECT sku,descripcion,SUM(unidades_disponible) as disponible,SUM(unidades_inicial) as inicial,MAX(fecha_produccion) as ultima_prod,empresa,precio_base,COUNT(*) as lotes FROM stock_pt WHERE estado='Disponible' GROUP BY sku,empresa ORDER BY sku")
    cols = ['sku','descripcion','disponible','inicial','ultima_prod','empresa','precio_base','lotes']
    rows = c.fetchall()
    return jsonify({'stock_pt': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/despachos', methods=['GET','POST'])
def handle_despachos():
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        # Validar cliente_id existe (despacho no debe quedar fantasma)
        if not d.get('cliente_id'):
            return jsonify({'error': 'cliente_id requerido'}), 400
        cli_row = c.execute(
            "SELECT id, nombre FROM clientes WHERE id=?", (d['cliente_id'],)
        ).fetchone()
        if not cli_row:
            return jsonify({'error': 'cliente_id no existe'}), 400
        # Validar pedido si se especifica
        numero_ped = d.get('numero_pedido', '')
        if numero_ped:
            ped_row = c.execute(
                "SELECT estado FROM pedidos WHERE numero=?", (numero_ped,)).fetchone()
            if not ped_row:
                return jsonify({'error': f'Pedido {numero_ped} no existe'}), 400
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM despachos WHERE numero LIKE ?", (f"DSP-{datetime.now().strftime('%Y')}-%",)); n = (c.fetchone()[0] or 0) + 1
        numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
        c.execute("INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado) VALUES (?,?,?,datetime('now'),?,?,?)",
                  (numero, numero_ped, d['cliente_id'], session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
        # Audit zero-error 2-may-2026: trazabilidad lote→cliente recall-ready.
        # Antes el lote_pt persistido en despachos_items era el que mandó el
        # frontend (string libre). Ahora se persiste el lote REAL que descontó
        # FEFO de stock_pt, garantizando que un recall pueda listar todos los
        # clientes que recibieron el lote afectado.
        for it in (d.get('items') or []):
            # Money sanity validation · audit zero-error
            cantidad_v, err = validate_money(it.get('cantidad', 0), allow_zero=False,
                                                max_value=100_000, field_name='cantidad')
            if err:
                return jsonify(err), 400
            cantidad = int(cantidad_v)
            precio_v, err = validate_money(it.get('precio_unitario', 0), allow_zero=True,
                                              field_name='precio_unitario')
            if err:
                return jsonify(err), 400
            sku = it.get('sku', '')
            # 1. Identificar el lote FEFO que se va a descontar
            lote_real = None
            row_lote = c.execute("""
                SELECT id, lote_produccion FROM stock_pt
                WHERE sku=? AND unidades_disponible>0
                ORDER BY fecha_produccion ASC LIMIT 1
            """, (sku,)).fetchone()
            if row_lote:
                lote_real = row_lote[1] or it.get('lote_pt', '')
                # 2. Descontar del lote identificado (atómico por id)
                c.execute("""UPDATE stock_pt
                              SET unidades_disponible=MAX(0, unidades_disponible-?)
                              WHERE id=?""",
                          (cantidad, row_lote[0]))
            else:
                # No hay stock disponible · usar lote del frontend como fallback
                lote_real = it.get('lote_pt', '')
            # 3. Persistir el lote REAL en despachos_items (recall-ready)
            c.execute("""INSERT INTO despachos_items
                          (numero_despacho, sku, descripcion, lote_pt, cantidad, precio_unitario)
                          VALUES (?,?,?,?,?,?)""",
                      (numero, sku, it.get('descripcion',''),
                       lote_real, cantidad, precio_v))
        if numero_ped:
            c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (numero_ped,))
        try:
            items_count = len(d.get('items') or [])
            audit_log(c, usuario=session.get('compras_user', 'sistema'),
                      accion='CREAR_DESPACHO', tabla='despachos', registro_id=numero,
                      despues={'cliente_id': d['cliente_id'],
                                'cliente_nombre': cli_row[1][:100],
                                'numero_pedido': numero_ped or None,
                                'items_count': items_count},
                      detalle=f"Despacho {numero} a {cli_row[1][:60]}"
                              + (f" · pedido {numero_ped}" if numero_ped else "")
                              + f" · {items_count} items")
        except Exception:
            pass
        conn.commit()
        return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201
    c.execute("SELECT d.numero,cl.nombre as cliente,d.fecha,d.numero_pedido,d.estado,d.operador FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id ORDER BY d.fecha DESC LIMIT 100")
    cols = ['numero','cliente','fecha','numero_pedido','estado','operador']
    rows = c.fetchall()
    return jsonify({'despachos': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/aliados/<int:cid>', methods=['PATCH'])
def patch_aliado(cid):
    """Actualiza semaforo y/o nivel_aliado de un aliado ANIMUS."""
    err, code = _require_clientes_access()
    if err: return err, code
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
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
        # Capturar antes para audit
        antes_row = c.execute(
            "SELECT codigo, nombre, semaforo, nivel_aliado FROM clientes WHERE id=?",
            (cid,)).fetchone()
        if not antes_row:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        antes = dict(antes_row)
        vals.append(cid)
        c.execute(f"UPDATE clientes SET {','.join(campos)} WHERE id=?", vals)
        try:
            audit_log(c, usuario=session.get('compras_user', 'sistema'),
                      accion='ACTUALIZAR_ALIADO', tabla='clientes', registro_id=cid,
                      antes=antes,
                      despues={k: d.get(k) for k in d
                                if k in ('semaforo', 'nivel_aliado',
                                         'fecha_vinculacion', 'ciudad',
                                         'categoria_profesional', 'canal_captacion',
                                         'notas_seguimiento')},
                      detalle=f"Actualizó aliado id={cid} ({antes.get('codigo','')})")
        except Exception:
            pass
        conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/clientes/cartera')
def get_cartera():
    """Resumen de cartera por aliado: facturado, pagado, saldo."""
    err, code = _require_clientes_access()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
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
    total_cartera = sum(r['saldo'] for r in rows if r['saldo'] > 0)
    return jsonify({'aliados': rows, 'total_cartera': total_cartera})

@bp.route('/api/aliados/<int:cid>', methods=['DELETE'])
def delete_aliado(cid):
    """Soft-delete: marca activo=0. No borra datos historicos.

    Audit zero-error 2-may-2026: requiere ADMIN (era cualquier sesión).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin puede desactivar aliados'}), 403
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE clientes SET activo=0 WHERE id=? AND empresa='ANIMUS'", (cid,))
    conn.commit()
    try:
        c.execute("""
            INSERT INTO audit_log (usuario, accion, tabla, registro_id, fecha)
            VALUES (?, 'DESACTIVAR_ALIADO', 'clientes', ?, datetime('now'))
        """, (user, str(cid)))
        conn.commit()
    except Exception as e:
        # Log fail (audit_log puede no tener todos los campos en DB pre-migración)
        pass
    return jsonify({'ok': True, 'message': 'Aliado desactivado'})

# ─── MÓDULO GERENCIA — Rutas ──────────────────────────────────
