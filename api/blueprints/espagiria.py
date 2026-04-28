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
