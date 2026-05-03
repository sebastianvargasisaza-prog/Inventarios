"""
espagiria.py — Blueprint modulo Espagiria
Panel de control para Luz Adriana (Asistente de Gerencia Espagiria).

Vista consolidada de qué pasa en planta Espagiria: produccion del mes, MPs
bajo minimo, OCs en proceso, solicitudes pendientes, alertas calidad,
compromisos del comite semanal y tareas asignadas a Luz.

Lectura mostly: agrega datos de los modulos operativos (inventario, compras,
calidad, programacion, rrhh, comunicacion). Luz NO escribe en BD operacional
desde aqui — el modulo es para que tenga radar completo.

Acceso: ESPAGIRIA_ACCESS = {luz, alejandro, sebastian}
"""
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, render_template_string

from config import DB_PATH, ESPAGIRIA_ACCESS
from database import get_db

bp = Blueprint("espagiria", __name__)


def _auth():
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in ESPAGIRIA_ACCESS:
        return None, jsonify({"error": "Sin acceso al modulo Espagiria"}), 403
    return u, None, None


def _fmt_many(rows):
    return [dict(r) for r in rows] if rows else []


# ─── HOME (template) ────────────────────────────────────────────────────────

@bp.route("/espagiria")
def espagiria_home():
    u = session.get("compras_user", "")
    if not u or u not in ESPAGIRIA_ACCESS:
        return jsonify({"error": "Sin acceso"}), 403
    from templates_py.espagiria_html import HTML
    return render_template_string(HTML, usuario=u)


# ─── DASHBOARD CONSOLIDADO ──────────────────────────────────────────────────

@bp.route("/api/espagiria/dashboard")
def dashboard():
    u, err, code = _auth()
    if err: return err, code

    conn = get_db()
    c = conn.cursor()
    out = {}

    # 1) Producciones del mes en curso
    try:
        out["producciones_mes"] = c.execute("""
            SELECT COUNT(*) as lotes, COALESCE(SUM(cantidad),0) as total_g
            FROM producciones
            WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
              AND estado != 'Cancelada'
        """).fetchone()
        out["producciones_mes"] = dict(out["producciones_mes"])
    except Exception:
        out["producciones_mes"] = {"lotes": 0, "total_g": 0}

    # 2) MPs bajo minimo (criticas + bajas)
    try:
        out["mps_bajo_minimo"] = c.execute("""
            SELECT m.codigo_mp, m.nombre_inci as nombre, m.stock_minimo,
                   COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                     WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad
                                     ELSE 0 END), 0) as stock_actual
            FROM maestro_mps m
            LEFT JOIN movimientos mov ON mov.material_id = m.codigo_mp
            WHERE m.activo = 1
            GROUP BY m.codigo_mp
            HAVING stock_actual < m.stock_minimo
               AND m.stock_minimo > 0
            ORDER BY (stock_actual / NULLIF(m.stock_minimo, 0)) ASC
            LIMIT 15
        """).fetchall()
        out["mps_bajo_minimo"] = _fmt_many(out["mps_bajo_minimo"])
    except Exception:
        out["mps_bajo_minimo"] = []

    # 3) Lotes que vencen en los proximos 30/60 dias
    try:
        hoy = datetime.now().date().isoformat()
        d30 = (datetime.now() + timedelta(days=30)).date().isoformat()
        d60 = (datetime.now() + timedelta(days=60)).date().isoformat()
        out["vencen_30d"] = c.execute("""
            SELECT COUNT(*) FROM movimientos
            WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL
              AND fecha_vencimiento BETWEEN ? AND ?
        """, (hoy, d30)).fetchone()[0]
        out["vencen_60d"] = c.execute("""
            SELECT COUNT(*) FROM movimientos
            WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL
              AND fecha_vencimiento BETWEEN ? AND ?
        """, (hoy, d60)).fetchone()[0]
    except Exception:
        out["vencen_30d"] = 0
        out["vencen_60d"] = 0

    # 4) OCs activas
    try:
        out["ocs_activas"] = c.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN estado='Aprobada' THEN 1 END) as aprobadas,
                   COUNT(CASE WHEN estado IN ('Autorizada','Revisada') THEN 1 END) as en_proceso,
                   COUNT(CASE WHEN estado='Pagada' THEN 1 END) as pagadas_mes
            FROM ordenes_compra
            WHERE fecha >= date('now','-30 day')
        """).fetchone()
        out["ocs_activas"] = dict(out["ocs_activas"])
    except Exception:
        out["ocs_activas"] = {"total": 0, "aprobadas": 0, "en_proceso": 0, "pagadas_mes": 0}

    # 5) Solicitudes pendientes
    try:
        out["solicitudes_pendientes"] = c.execute("""
            SELECT COUNT(*) FROM solicitudes_compra
            WHERE estado IN ('Pendiente','En revision')
        """).fetchone()[0]
    except Exception:
        out["solicitudes_pendientes"] = 0

    # 6) Calidad: NCs abiertas + cuarentena + calibraciones vencidas
    try:
        out["calidad_ncs"] = c.execute(
            "SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'"
        ).fetchone()[0]
    except Exception:
        out["calidad_ncs"] = 0

    try:
        out["lotes_cuarentena"] = c.execute("""
            SELECT COUNT(DISTINCT lote)
            FROM movimientos
            WHERE estado_calidad='Cuarentena' AND tipo='Entrada'
        """).fetchone()[0]
    except Exception:
        out["lotes_cuarentena"] = 0

    try:
        out["calibraciones_vencidas"] = c.execute("""
            SELECT COUNT(*) FROM calibraciones
            WHERE fecha_proxima < date('now') AND estado != 'OK'
        """).fetchone()[0]
    except Exception:
        out["calibraciones_vencidas"] = 0

    # 7) Tareas asignadas a Luz (de comunicacion, si la tabla existe)
    try:
        out["mis_tareas_pendientes"] = c.execute("""
            SELECT t.id, t.titulo, t.fecha_compromiso, t.prioridad, t.estado, t.area
            FROM tareas_internas t
            JOIN tareas_raci r ON r.tarea_id = t.id
            WHERE r.usuario = ?
              AND r.rol IN ('R','A')
              AND t.estado NOT IN ('Hecha','Cancelada')
            ORDER BY
              CASE t.prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END,
              COALESCE(t.fecha_compromiso, '9999-12-31')
            LIMIT 20
        """, (u,)).fetchall()
        out["mis_tareas_pendientes"] = _fmt_many(out["mis_tareas_pendientes"])
    except Exception:
        out["mis_tareas_pendientes"] = []

    # 8) Compromisos del ultimo comite (si la tabla existe)
    try:
        ultima_acta = c.execute("""
            SELECT id, fecha FROM comites_actas
            ORDER BY fecha DESC LIMIT 1
        """).fetchone()
        if ultima_acta:
            out["ultimo_comite_fecha"] = ultima_acta["fecha"]
            out["compromisos_ultimo_comite"] = c.execute("""
                SELECT t.id, t.titulo, t.estado, t.fecha_compromiso,
                       (SELECT GROUP_CONCAT(usuario, ',') FROM tareas_raci
                        WHERE tarea_id=t.id AND rol='R') as responsables
                FROM tareas_internas t
                WHERE t.origen = 'comite' AND t.origen_ref = ?
                ORDER BY t.estado, t.titulo
                LIMIT 30
            """, (str(ultima_acta["id"]),)).fetchall()
            out["compromisos_ultimo_comite"] = _fmt_many(out["compromisos_ultimo_comite"])
        else:
            out["ultimo_comite_fecha"] = None
            out["compromisos_ultimo_comite"] = []
    except Exception:
        out["ultimo_comite_fecha"] = None
        out["compromisos_ultimo_comite"] = []

    # 9) Pedidos cliente activos (Fernando Mesa principal)
    try:
        out["pedidos_activos"] = c.execute("""
            SELECT COUNT(*) FROM pedidos
            WHERE estado IN ('Pendiente','En produccion','Listo','En despacho')
        """).fetchone()[0]
    except Exception:
        out["pedidos_activos"] = 0

    return jsonify(out)


# ─── ALERTAS CONSOLIDADAS ───────────────────────────────────────────────────

@bp.route("/api/espagiria/alertas")
def alertas():
    """Lista de alertas operativas para que Luz priorice el dia."""
    u, err, code = _auth()
    if err: return err, code

    conn = get_db()
    c = conn.cursor()
    alertas_lista = []

    # MPs en cero stock (criticas)
    try:
        for r in c.execute("""
            SELECT m.codigo_mp, m.nombre_inci as nombre,
                   COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                     WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad
                                     ELSE 0 END), 0) as stock_actual
            FROM maestro_mps m
            LEFT JOIN movimientos mov ON mov.material_id = m.codigo_mp
            WHERE m.activo = 1 AND m.stock_minimo > 0
            GROUP BY m.codigo_mp
            HAVING stock_actual <= 0
            LIMIT 10
        """).fetchall():
            alertas_lista.append({
                "tipo": "stock_cero",
                "severidad": "alta",
                "titulo": f"MP en cero: {r['nombre']}",
                "detalle": f"Codigo {r['codigo_mp']}",
                "accion_sugerida": "Crear solicitud de compra urgente",
            })
    except Exception:
        pass

    # Lotes vencen en 7 dias
    try:
        hoy = datetime.now().date().isoformat()
        d7 = (datetime.now() + timedelta(days=7)).date().isoformat()
        for r in c.execute("""
            SELECT material_nombre, lote, fecha_vencimiento, cantidad
            FROM movimientos
            WHERE tipo='Entrada' AND fecha_vencimiento BETWEEN ? AND ?
            LIMIT 10
        """, (hoy, d7)).fetchall():
            alertas_lista.append({
                "tipo": "vencimiento_proximo",
                "severidad": "alta",
                "titulo": f"Lote {r['lote']} vence en <7 dias",
                "detalle": f"{r['material_nombre']} ({r['cantidad']} g) - {r['fecha_vencimiento']}",
                "accion_sugerida": "Usar primero o transferir",
            })
    except Exception:
        pass

    # NCs abiertas hace mas de 30 dias
    try:
        for r in c.execute("""
            SELECT id, descripcion, fecha, responsable
            FROM no_conformidades
            WHERE estado='Abierta' AND fecha < date('now','-30 day')
            ORDER BY fecha ASC
            LIMIT 10
        """).fetchall():
            alertas_lista.append({
                "tipo": "nc_estancada",
                "severidad": "media",
                "titulo": f"NC abierta hace >30 dias",
                "detalle": (r["descripcion"] or "")[:100],
                "accion_sugerida": f"Cerrar o escalar — responsable: {r['responsable']}",
            })
    except Exception:
        pass

    # Tareas vencidas asignadas a Luz
    try:
        for r in c.execute("""
            SELECT t.id, t.titulo, t.fecha_compromiso, t.area
            FROM tareas_internas t
            JOIN tareas_raci r ON r.tarea_id = t.id
            WHERE r.usuario = ?
              AND r.rol IN ('R','A')
              AND t.estado NOT IN ('Hecha','Cancelada')
              AND t.fecha_compromiso IS NOT NULL
              AND t.fecha_compromiso < date('now')
            LIMIT 15
        """, (u,)).fetchall():
            alertas_lista.append({
                "tipo": "tarea_vencida",
                "severidad": "alta",
                "titulo": f"Tarea vencida: {r['titulo']}",
                "detalle": f"Comprometida {r['fecha_compromiso']} - area: {r['area']}",
                "accion_sugerida": "Completar o renegociar plazo",
            })
    except Exception:
        pass

    return jsonify({"alertas": alertas_lista, "total": len(alertas_lista)})


# ─── RESUMEN DIARIO PRE-COMITE ──────────────────────────────────────────────

@bp.route("/api/espagiria/resumen-pre-comite")
def resumen_pre_comite():
    """Resumen para que Luz prepare el comite del viernes:
    - Pendientes que se llevan arrastrando >2 semanas (reincidentes)
    - Compromisos completados en la semana
    - Nuevos problemas detectados
    """
    u, err, code = _auth()
    if err: return err, code

    conn = get_db()
    c = conn.cursor()
    out = {}

    try:
        out["reincidentes"] = _fmt_many(c.execute("""
            SELECT t.id, t.titulo, t.area,
                   (SELECT GROUP_CONCAT(usuario,',') FROM tareas_raci WHERE tarea_id=t.id AND rol='R') as responsables,
                   (julianday('now') - julianday(t.fecha_creacion)) as dias_abierta
            FROM tareas_internas t
            WHERE t.estado NOT IN ('Hecha','Cancelada')
              AND t.origen = 'comite'
              AND t.fecha_creacion < date('now','-14 day')
            ORDER BY t.fecha_creacion ASC
            LIMIT 20
        """).fetchall())
    except Exception:
        out["reincidentes"] = []

    try:
        out["completadas_semana"] = _fmt_many(c.execute("""
            SELECT id, titulo, area, fecha_completada
            FROM tareas_internas
            WHERE estado = 'Hecha'
              AND fecha_completada >= date('now','-7 day')
            ORDER BY fecha_completada DESC
            LIMIT 30
        """).fetchall())
    except Exception:
        out["completadas_semana"] = []

    try:
        out["nuevas_semana"] = _fmt_many(c.execute("""
            SELECT id, titulo, area, fecha_creacion, prioridad
            FROM tareas_internas
            WHERE fecha_creacion >= date('now','-7 day')
            ORDER BY fecha_creacion DESC
            LIMIT 30
        """).fetchall())
    except Exception:
        out["nuevas_semana"] = []

    return jsonify(out)


# ════════════════════════════════════════════════════════════════════════
# QUICK ACTIONS · "Lo urgente del dia" para Luz (Sebastian 3-may-2026)
# ════════════════════════════════════════════════════════════════════════

@bp.route("/api/espagiria/quick-actions", methods=["GET"])
def quick_actions():
    """Agrupa lo que requiere accion HOY de Luz: pedidos por confirmar,
    OOS sin asignar, lotes en cuarentena >7d, equipos vencidos, tareas
    vencidas/hoy."""
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    out = {"timestamp": datetime.now().isoformat(), "secciones": []}
    total = 0

    # 1) Pedidos maquila SIN produccion_id (necesitan planificacion)
    try:
        rows = c.execute("""
            SELECT id, numero, cliente_nombre, producto_nombre, unidades,
                   fecha_entrega_objetivo, estado
              FROM maquila_pedidos
             WHERE estado IN ('recibido','planificado')
               AND (produccion_id IS NULL OR produccion_id = 0)
             ORDER BY fecha_entrega_objetivo ASC NULLS LAST
             LIMIT 10
        """).fetchall()
    except Exception:
        try:
            rows = c.execute("""
                SELECT id, numero, cliente_nombre, producto_nombre, unidades,
                       fecha_entrega_objetivo, estado
                  FROM maquila_pedidos
                 WHERE estado IN ('recibido','planificado')
                   AND (produccion_id IS NULL OR produccion_id = 0)
                 ORDER BY fecha_entrega_objetivo ASC
                 LIMIT 10
            """).fetchall()
        except Exception:
            rows = []
    items = _fmt_many(rows)
    if items:
        out["secciones"].append({
            "id": "pedidos_sin_produccion",
            "titulo": f"📦 {len(items)} pedidos sin producción asignada",
            "severidad": "alta",
            "accion": "Asignar producción · planta los necesita",
            "link": "/maquila",
            "items": items,
        })
        total += len(items)

    # 2) OOS abiertos sin investigador
    try:
        rows = c.execute("""
            SELECT id, codigo, lote, producto, parametro, fecha_deteccion, estado
              FROM oos
             WHERE estado IN ('abierto','en_investigacion')
             ORDER BY fecha_deteccion DESC LIMIT 10
        """).fetchall()
        items = _fmt_many(rows)
        if items:
            out["secciones"].append({
                "id": "oos_abiertos",
                "titulo": f"⚠️ {len(items)} OOS abiertos",
                "severidad": "alta",
                "accion": "Revisar y escalar a calidad · CTRL.PRO-006",
                "link": "/calidad",
                "items": items,
            })
            total += len(items)
    except Exception:
        pass

    # 3) Lotes en cuarentena >7d (urgente liberar)
    try:
        rows = c.execute("""
            SELECT material_id, material_nombre, lote, cantidad, fecha,
                   julianday('now') - julianday(fecha) as dias
              FROM movimientos
             WHERE estado_calidad = 'Cuarentena' AND tipo = 'Entrada'
               AND date(fecha) <= date('now', '-7 day')
             ORDER BY fecha ASC LIMIT 10
        """).fetchall()
        items = _fmt_many(rows)
        if items:
            out["secciones"].append({
                "id": "cuarentena_vieja",
                "titulo": f"🟡 {len(items)} lotes en cuarentena hace >7 días",
                "severidad": "media",
                "accion": "Pedir liberación a calidad",
                "link": "/calidad",
                "items": items,
            })
            total += len(items)
    except Exception:
        pass

    # 4) Equipos calibracion vencida
    try:
        rows = c.execute("""
            SELECT ep.codigo, ep.nombre, ep.area_codigo,
                   MAX(ee.fecha_proxima) as fecha_proxima,
                   julianday('now') - julianday(MAX(ee.fecha_proxima)) as dias_vencido
              FROM equipos_planta ep
              LEFT JOIN equipos_eventos ee
                ON ee.equipo_codigo = ep.codigo
                AND ee.tipo_evento IN ('calibracion','verificacion_semestral')
                AND ee.fecha_proxima IS NOT NULL
             WHERE COALESCE(ep.activo,1) = 1
             GROUP BY ep.codigo
             HAVING fecha_proxima IS NOT NULL
                AND date(fecha_proxima) < date('now')
             ORDER BY fecha_proxima ASC
             LIMIT 10
        """).fetchall()
        items = _fmt_many(rows)
        if items:
            out["secciones"].append({
                "id": "equipos_vencidos",
                "titulo": f"🔧 {len(items)} equipos con calibración VENCIDA",
                "severidad": "alta",
                "accion": "Coordinar calibración o NO usar el equipo",
                "link": "/calidad",
                "items": items,
            })
            total += len(items)
    except Exception:
        pass

    # 5) Tareas de Luz vencidas o de hoy
    try:
        rows = c.execute("""
            SELECT t.id, t.titulo, t.fecha_compromiso, t.prioridad, t.area
              FROM tareas_internas t
              JOIN tareas_raci r ON r.tarea_id = t.id
             WHERE r.usuario = ?
               AND r.rol IN ('R','A')
               AND t.estado NOT IN ('Hecha','Cancelada')
               AND (t.fecha_compromiso <= date('now') OR
                    t.prioridad = 'Alta')
             ORDER BY t.fecha_compromiso ASC LIMIT 10
        """, (u,)).fetchall()
        items = _fmt_many(rows)
        if items:
            out["secciones"].append({
                "id": "mis_tareas_urgentes",
                "titulo": f"📋 {len(items)} tareas tuyas vencidas/urgentes",
                "severidad": "alta",
                "accion": "Resolver o reasignar",
                "link": "/comunicacion",
                "items": items,
            })
            total += len(items)
    except Exception:
        pass

    # 6) Pedidos entregados sin pago registrado (cobros vencidos)
    try:
        rows = c.execute("""
            SELECT mp.id, mp.numero, mp.cliente_nombre, mp.valor_total,
                   mp.fecha_pedido,
                   julianday('now') - julianday(mp.fecha_pedido) as dias
              FROM maquila_pedidos mp
             WHERE mp.estado = 'entregado'
               AND COALESCE(mp.valor_total, 0) > 0
               AND NOT EXISTS (
                 SELECT 1 FROM flujo_ingresos fi
                  WHERE fi.referencia = mp.numero
               )
               AND julianday('now') - julianday(mp.fecha_pedido) > 7
             ORDER BY dias DESC LIMIT 10
        """).fetchall()
        items = _fmt_many(rows)
        if items:
            out["secciones"].append({
                "id": "cobros_vencidos",
                "titulo": f"💰 {len(items)} pedidos entregados sin pago confirmado",
                "severidad": "media",
                "accion": "Confirmar pago o llamar al cliente",
                "link": "/espagiria#tab-cartera",
                "items": items,
            })
            total += len(items)
    except Exception:
        pass

    out["total_urgentes"] = total
    return jsonify(out)


# ════════════════════════════════════════════════════════════════════════
# CREAR PEDIDO MAQUILA RAPIDO (Sebastian 3-may-2026)
# ════════════════════════════════════════════════════════════════════════

@bp.route("/api/espagiria/pedido-rapido", methods=["POST"])
def pedido_rapido():
    """Crea un pedido maquila rapido desde el panel de Luz.

    Body: {cliente_id, producto_nombre, unidades, fecha_entrega_objetivo,
           presentacion_id?, precio_unidad?, observaciones?}

    Genera numero MQ-NNNN automatico, valida, audita, notifica.
    """
    u, err, code = _auth()
    if err: return err, code
    from audit_helpers import audit_log
    d = request.get_json() or {}
    try:
        cliente_id = int(d.get("cliente_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "cliente_id requerido"}), 400
    producto = (d.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    try:
        unidades = int(d.get("unidades") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "unidades debe ser entero"}), 400
    if unidades <= 0:
        return jsonify({"error": "unidades debe ser > 0"}), 400

    conn = get_db(); c = conn.cursor()
    cli = c.execute(
        "SELECT nombre FROM clientes_maquila WHERE id=? AND activo=1",
        (cliente_id,)).fetchone()
    if not cli:
        return jsonify({"error": "Cliente no existe o esta inactivo"}), 400

    # Numero secuencial MQ-NNNN
    n = c.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(numero,4) AS INTEGER)),0)+1 FROM maquila_pedidos WHERE numero LIKE 'MQ-%'"
    ).fetchone()[0] or 1
    numero = f'MQ-{n:04d}'

    # Calcular kg si tenemos presentacion
    kg_est = None
    if d.get("presentacion_id"):
        pr = c.execute(
            "SELECT factor_g_por_unidad FROM producto_presentaciones WHERE id=?",
            (d.get("presentacion_id"),)).fetchone()
        if pr and pr[0]:
            kg_est = (unidades * pr[0]) / 1000.0

    precio_unidad = None
    if d.get("precio_unidad") not in (None, ""):
        try:
            precio_unidad = float(d.get("precio_unidad"))
            if precio_unidad < 0:
                return jsonify({"error": "precio_unidad no puede ser negativo"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "precio_unidad invalido"}), 400
    valor_total = (precio_unidad * unidades) if precio_unidad else None

    try:
        c.execute("""
            INSERT INTO maquila_pedidos
              (numero, cliente_id, cliente_nombre, producto_nombre,
               presentacion_id, unidades, kg_estimados,
               fecha_entrega_objetivo, precio_unidad, valor_total,
               observaciones, creado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            numero, cliente_id, cli[0], producto,
            d.get("presentacion_id"),
            unidades, kg_est,
            (d.get("fecha_entrega_objetivo") or "").strip() or None,
            precio_unidad, valor_total,
            d.get("observaciones") or "",
            u,
        ))
        new_id = c.lastrowid
        audit_log(c, usuario=u, accion='CREAR_PEDIDO_MAQUILA_RAPIDO',
                  tabla='maquila_pedidos', registro_id=new_id,
                  despues={'numero': numero, 'cliente': cli[0], 'producto': producto[:80],
                           'unidades': unidades, 'valor_total': valor_total},
                  detalle=f"Pedido {numero} · {cli[0]} · {producto[:60]} · {unidades} uds" +
                           (f" · ${valor_total:,.0f}" if valor_total else ""))
        conn.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)[:200]}), 400

    # Notif al equipo de produccion
    try:
        from blueprints.notif import push_notif_multi
        push_notif_multi(
            ['sebastian','alejandro','luis','luz'],
            'maquila',
            f'📦 Nuevo pedido maquila · {numero}',
            body=f"{cli[0]} pidió {unidades} uds de {producto}" +
                 (f"\nEntrega: {d.get('fecha_entrega_objetivo')}" if d.get('fecha_entrega_objetivo') else "") +
                 f"\nRegistrado por {u}",
            link=f'/maquila',
            remitente=u,
        )
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "id": new_id,
        "numero": numero,
        "cliente": cli[0],
        "valor_total": valor_total,
    }), 201


# ════════════════════════════════════════════════════════════════════════
# CARTERA MAQUILA · cobros vencidos (Sebastian 3-may-2026)
# ════════════════════════════════════════════════════════════════════════

@bp.route("/api/espagiria/cartera-maquila", methods=["GET"])
def cartera_maquila():
    """Pedidos entregados con/sin pago confirmado · cartera por cliente.

    Cruza maquila_pedidos.estado='entregado' contra flujo_ingresos
    (referencia=numero_pedido) para detectar cobros pendientes.
    """
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    # Pedidos entregados con valor
    rows = c.execute("""
        SELECT mp.id, mp.numero, mp.cliente_id, mp.cliente_nombre,
               mp.producto_nombre, mp.unidades, mp.valor_total,
               mp.fecha_pedido, mp.fecha_entrega_objetivo,
               (SELECT MAX(actualizado_en) FROM maquila_pedidos
                 WHERE id = mp.id) as fecha_estado_actual,
               (SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos
                 WHERE referencia = mp.numero) as pagado,
               julianday('now') - julianday(mp.fecha_pedido) as dias_desde_pedido
          FROM maquila_pedidos mp
         WHERE mp.estado = 'entregado'
           AND COALESCE(mp.valor_total,0) > 0
         ORDER BY mp.fecha_pedido DESC
         LIMIT 200
    """).fetchall()
    items = []
    total_facturado = 0
    total_pagado = 0
    total_vencido = 0
    for r in rows:
        d = dict(r)
        valor = d.get('valor_total') or 0
        pagado = d.get('pagado') or 0
        saldo = valor - pagado
        dias = int(d.get('dias_desde_pedido') or 0)
        # Estado pago
        if saldo <= 0.01:
            estado_pago = 'pagado'
        elif pagado > 0:
            estado_pago = 'parcial'
        elif dias > 30:
            estado_pago = 'vencido_mayor_30d'
        elif dias > 15:
            estado_pago = 'vencido_15d'
        elif dias > 7:
            estado_pago = 'pendiente_>7d'
        else:
            estado_pago = 'pendiente_reciente'
        d['saldo'] = saldo
        d['estado_pago'] = estado_pago
        d['dias_desde_pedido'] = dias
        items.append(d)
        total_facturado += valor
        total_pagado += pagado
        if saldo > 0.01 and dias > 30:
            total_vencido += saldo

    # KPIs por cliente
    por_cliente = {}
    for it in items:
        cn = it.get('cliente_nombre') or '—'
        if cn not in por_cliente:
            por_cliente[cn] = {
                'cliente': cn, 'pedidos': 0, 'facturado': 0,
                'pagado': 0, 'saldo': 0, 'vencido_30d': 0,
            }
        por_cliente[cn]['pedidos'] += 1
        por_cliente[cn]['facturado'] += it['valor_total'] or 0
        por_cliente[cn]['pagado'] += it.get('pagado', 0) or 0
        por_cliente[cn]['saldo'] += it.get('saldo', 0) or 0
        if it['estado_pago'] == 'vencido_mayor_30d':
            por_cliente[cn]['vencido_30d'] += it.get('saldo', 0) or 0
    por_cliente_list = sorted(por_cliente.values(),
                                key=lambda x: x['saldo'], reverse=True)

    return jsonify({
        "kpis": {
            "total_facturado": total_facturado,
            "total_pagado": total_pagado,
            "total_saldo": total_facturado - total_pagado,
            "total_vencido_30d": total_vencido,
            "total_pedidos": len(items),
        },
        "por_cliente": por_cliente_list,
        "pedidos": items,
    })


# ════════════════════════════════════════════════════════════════════════
# CLIENTES MAQUILA 360 (Sebastian 3-may-2026 · pedido por Luz)
# ════════════════════════════════════════════════════════════════════════
# Luz necesita ver de cada cliente maquila el panorama completo:
# datos basicos + KPIs financieros + pedidos historicos + pipeline activo +
# top productos. Espejo de /api/clientes/<id>/ficha360 pero adaptado a
# clientes_maquila + maquila_pedidos.

@bp.route("/api/espagiria/clientes-maquila", methods=["GET"])
def clientes_maquila_lista():
    """Lista clientes_maquila con stats agregadas (count + valor + ult ped)."""
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT cm.id, cm.nombre, cm.nit_cedula, cm.email, cm.telefono,
                   cm.es_marca_propia, cm.empresa_grupo, cm.comparte_formula_con,
                   cm.activo, cm.creado_en,
                   COALESCE(s.total_pedidos, 0) as total_pedidos,
                   COALESCE(s.valor_total, 0) as valor_total,
                   COALESCE(s.activos, 0) as pedidos_activos,
                   s.ultimo_ped, s.primer_ped
              FROM clientes_maquila cm
              LEFT JOIN (
                SELECT cliente_id,
                       COUNT(*) as total_pedidos,
                       COALESCE(SUM(valor_total),0) as valor_total,
                       COUNT(CASE WHEN estado NOT IN ('entregado','cancelado') THEN 1 END) as activos,
                       MAX(fecha_pedido) as ultimo_ped,
                       MIN(fecha_pedido) as primer_ped
                  FROM maquila_pedidos
                 GROUP BY cliente_id
              ) s ON s.cliente_id = cm.id
             WHERE cm.activo = 1
             ORDER BY s.ultimo_ped DESC NULLS LAST, cm.nombre
        """).fetchall()
        return jsonify({"clientes": _fmt_many(rows)})
    except sqlite3.OperationalError as e:
        # NULLS LAST puede no estar en sqlite viejo · fallback
        rows = c.execute("""
            SELECT cm.id, cm.nombre, cm.nit_cedula, cm.email, cm.telefono,
                   cm.es_marca_propia, cm.empresa_grupo, cm.comparte_formula_con,
                   cm.activo, cm.creado_en,
                   COALESCE(s.total_pedidos, 0) as total_pedidos,
                   COALESCE(s.valor_total, 0) as valor_total,
                   COALESCE(s.activos, 0) as pedidos_activos,
                   s.ultimo_ped, s.primer_ped
              FROM clientes_maquila cm
              LEFT JOIN (
                SELECT cliente_id,
                       COUNT(*) as total_pedidos,
                       COALESCE(SUM(valor_total),0) as valor_total,
                       COUNT(CASE WHEN estado NOT IN ('entregado','cancelado') THEN 1 END) as activos,
                       MAX(fecha_pedido) as ultimo_ped,
                       MIN(fecha_pedido) as primer_ped
                  FROM maquila_pedidos
                 GROUP BY cliente_id
              ) s ON s.cliente_id = cm.id
             WHERE cm.activo = 1
             ORDER BY cm.nombre
        """).fetchall()
        return jsonify({"clientes": _fmt_many(rows)})


@bp.route("/api/espagiria/clientes-maquila/<int:cid>/360", methods=["GET"])
def cliente_maquila_360(cid):
    """Ficha 360 de un cliente maquila: datos + stats + pedidos + top productos
    + pipeline activo + produccion vinculada."""
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    # Datos cliente + stats agregadas
    row = c.execute("""
        SELECT cm.id, cm.nombre, cm.nit_cedula, cm.email, cm.telefono,
               cm.es_marca_propia, cm.empresa_grupo, cm.comparte_formula_con,
               cm.margen_seguridad_pct, cm.notas, cm.creado_en,
               COALESCE(s.total_pedidos, 0) as total_pedidos,
               COALESCE(s.valor_total, 0) as valor_total,
               s.ultimo_ped, s.primer_ped
          FROM clientes_maquila cm
          LEFT JOIN (
            SELECT cliente_id, COUNT(*) as total_pedidos,
                   COALESCE(SUM(valor_total),0) as valor_total,
                   MAX(fecha_pedido) as ultimo_ped,
                   MIN(fecha_pedido) as primer_ped
              FROM maquila_pedidos GROUP BY cliente_id
          ) s ON s.cliente_id = cm.id
         WHERE cm.id = ? AND cm.activo = 1
    """, (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Cliente no encontrado"}), 404
    cliente = dict(row)
    total_ped = cliente.pop('total_pedidos', 0) or 0
    valor_total = cliente.pop('valor_total', 0) or 0
    ultimo_ped = cliente.pop('ultimo_ped', None)
    primer_ped = cliente.pop('primer_ped', None)
    # Stats derivados
    dias_sin_pedido = None
    if ultimo_ped:
        try:
            dias_sin_pedido = (datetime.now() - datetime.fromisoformat(ultimo_ped[:19])).days
        except Exception:
            pass
    ticket_prom = round(valor_total / total_ped, 0) if total_ped > 0 else 0
    # Pedidos recientes (10 últimos)
    pedidos_recientes = _fmt_many(c.execute("""
        SELECT id, numero, producto_nombre, unidades, kg_estimados,
               fecha_pedido, fecha_entrega_objetivo, estado, valor_total,
               produccion_id
          FROM maquila_pedidos
         WHERE cliente_id = ?
         ORDER BY fecha_pedido DESC LIMIT 10
    """, (cid,)).fetchall())
    # Pipeline activo (no entregado/cancelado)
    pipeline_activo = _fmt_many(c.execute("""
        SELECT id, numero, producto_nombre, unidades, fecha_pedido,
               fecha_entrega_objetivo, estado, produccion_id
          FROM maquila_pedidos
         WHERE cliente_id = ? AND estado NOT IN ('entregado','cancelado')
         ORDER BY
           CASE estado WHEN 'recibido' THEN 1 WHEN 'planificado' THEN 2
                       WHEN 'en_produccion' THEN 3 WHEN 'listo_entrega' THEN 4
                       ELSE 5 END,
           fecha_entrega_objetivo
    """, (cid,)).fetchall())
    # Top productos (mas pedidos)
    top_productos = _fmt_many(c.execute("""
        SELECT producto_nombre,
               COUNT(*) as veces_pedido,
               COALESCE(SUM(unidades),0) as total_uds,
               COALESCE(SUM(kg_estimados),0) as total_kg,
               MAX(fecha_pedido) as ultimo
          FROM maquila_pedidos
         WHERE cliente_id = ?
         GROUP BY producto_nombre
         ORDER BY veces_pedido DESC, total_uds DESC
         LIMIT 10
    """, (cid,)).fetchall())
    return jsonify({
        "cliente": cliente,
        "stats": {
            "total_pedidos": total_ped,
            "valor_total": valor_total,
            "ticket_promedio": ticket_prom,
            "ultimo_pedido": (ultimo_ped or '')[:10],
            "primer_pedido": (primer_ped or '')[:10],
            "dias_sin_pedido": dias_sin_pedido,
            "pipeline_activos": len(pipeline_activo),
        },
        "pedidos_recientes": pedidos_recientes,
        "pipeline_activo": pipeline_activo,
        "top_productos": top_productos,
    })


# ════════════════════════════════════════════════════════════════════════
# LAB EN VIVO (Sebastian 3-may-2026 · pedido por Luz)
# ════════════════════════════════════════════════════════════════════════
# Reportes en tiempo real de qué pasa en planta espagiria AHORA mismo.

@bp.route("/api/espagiria/lab/en-vivo", methods=["GET"])
def lab_en_vivo():
    """Snapshot del laboratorio AHORA: producciones en curso, equipos vencidos,
    lotes en cuarentena, OOS abiertos, sistema de agua, capacitaciones."""
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    out = {"timestamp": datetime.now().isoformat()}

    # 1) Producciones en curso (con sala + operario si tienen)
    try:
        out["producciones_en_curso"] = _fmt_many(c.execute("""
            SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
                   pp.cantidad_kg, pp.estado, pp.inicio_real_at,
                   ap.codigo as area_codigo, ap.nombre as area_nombre,
                   op_e.nombre as operario_elaboracion,
                   op_d.nombre as operario_dispensacion
              FROM produccion_programada pp
              LEFT JOIN areas_planta ap ON ap.id = pp.area_id
              LEFT JOIN operarios_planta op_e ON op_e.id = pp.operario_elaboracion_id
              LEFT JOIN operarios_planta op_d ON op_d.id = pp.operario_dispensacion_id
             WHERE LOWER(COALESCE(pp.estado,'')) IN
                   ('en_produccion','en proceso','iniciada','dispensando','elaborando','envasando')
                OR pp.inicio_real_at IS NOT NULL AND pp.fin_real_at IS NULL
             ORDER BY COALESCE(pp.inicio_real_at, pp.fecha_programada) DESC
             LIMIT 20
        """).fetchall())
    except Exception:
        out["producciones_en_curso"] = []

    # 2) Producciones HOY programadas
    try:
        out["producciones_hoy"] = _fmt_many(c.execute("""
            SELECT pp.id, pp.producto, pp.lotes, pp.cantidad_kg,
                   pp.estado, ap.codigo as area_codigo
              FROM produccion_programada pp
              LEFT JOIN areas_planta ap ON ap.id = pp.area_id
             WHERE pp.fecha_programada = date('now')
               AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
             ORDER BY ap.codigo, pp.producto
        """).fetchall())
    except Exception:
        out["producciones_hoy"] = []

    # 3) Equipos con calibracion vencida o proximos
    try:
        out["equipos_estado"] = _fmt_many(c.execute("""
            SELECT ep.codigo, ep.nombre, ep.area_codigo,
                   MAX(ee.fecha_proxima) as fecha_proxima,
                   julianday(MAX(ee.fecha_proxima)) - julianday('now') as dias
              FROM equipos_planta ep
              LEFT JOIN equipos_eventos ee
                ON ee.equipo_codigo = ep.codigo
                AND ee.tipo_evento IN ('calibracion','verificacion_semestral')
                AND ee.fecha_proxima IS NOT NULL
             WHERE COALESCE(ep.activo,1) = 1
             GROUP BY ep.codigo
             HAVING fecha_proxima IS NOT NULL
                AND date(fecha_proxima) <= date('now', '+15 days')
             ORDER BY fecha_proxima ASC
             LIMIT 20
        """).fetchall())
    except Exception:
        out["equipos_estado"] = []

    # 4) Lotes en cuarentena (con dias allí)
    try:
        out["lotes_cuarentena"] = _fmt_many(c.execute("""
            SELECT material_id, material_nombre, lote, cantidad,
                   fecha as fecha_entrada,
                   julianday('now') - julianday(fecha) as dias_cuarentena
              FROM movimientos
             WHERE estado_calidad = 'Cuarentena' AND tipo = 'Entrada'
             ORDER BY fecha ASC
             LIMIT 20
        """).fetchall())
    except Exception:
        out["lotes_cuarentena"] = []

    # 5) OOS abiertos (calidad)
    try:
        out["oos_abiertos"] = _fmt_many(c.execute("""
            SELECT id, codigo, origen, lote, producto, parametro,
                   valor_obtenido, valor_obtenido_texto, estado, fecha_deteccion
              FROM oos
             WHERE estado IN ('abierto', 'en_investigacion', 'en_aprobacion')
             ORDER BY fecha_deteccion DESC
             LIMIT 15
        """).fetchall())
    except Exception:
        out["oos_abiertos"] = []

    # 6) Sistema de agua hoy (registro o no)
    try:
        agua_hoy = c.execute("""
            SELECT COUNT(*) as registros, MAX(fecha) as ultima
              FROM calidad_agua_registros
             WHERE date(fecha) = date('now')
        """).fetchone()
        out["agua_hoy"] = dict(agua_hoy) if agua_hoy else {'registros': 0, 'ultima': None}
    except Exception:
        out["agua_hoy"] = {'registros': 0, 'ultima': None}

    # 7) Capacitaciones pendientes activas
    try:
        out["capacitaciones_pendientes"] = c.execute("""
            SELECT COUNT(*) FROM sgd_capacitaciones
             WHERE estado IN ('asignada','leida')
        """).fetchone()[0]
    except Exception:
        out["capacitaciones_pendientes"] = 0

    # 8) Desviaciones abiertas + dias
    try:
        out["desviaciones_abiertas"] = _fmt_many(c.execute("""
            SELECT codigo, tipo, severidad, estado, fecha_deteccion,
                   julianday('now') - julianday(fecha_deteccion) as dias_abierta
              FROM desviaciones
             WHERE estado NOT IN ('cerrada','rechazada')
             ORDER BY fecha_deteccion DESC
             LIMIT 10
        """).fetchall())
    except Exception:
        out["desviaciones_abiertas"] = []

    return jsonify(out)
