"""
marketing.py — Blueprint módulo Marketing
Campañas, Influencers, Contenido, Analytics, 5 Agentes IA internos
"""
import sqlite3
import traceback
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session

from config import DB_PATH, ADMIN_USERS

bp = Blueprint("marketing", __name__)

MARKETING_USERS = {"jefferson", "valentina", "sebastian", "alejandro"}


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _auth():
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    return u, None, None


def _fmt(row):
    return dict(row) if row else None


def _fmt_many(rows):
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/dashboard")
def mkt_dashboard():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        # KPIs principales
        total_campanas = c.execute("SELECT COUNT(*) FROM marketing_campanas").fetchone()[0]
        activas = c.execute("SELECT COUNT(*) FROM marketing_campanas WHERE estado='Activa'").fetchone()[0]
        presupuesto_total = c.execute("SELECT COALESCE(SUM(presupuesto),0) FROM marketing_campanas").fetchone()[0]
        presupuesto_gastado = c.execute("SELECT COALESCE(SUM(presupuesto_gastado),0) FROM marketing_campanas").fetchone()[0]
        total_influencers = c.execute("SELECT COUNT(*) FROM marketing_influencers WHERE estado='Activo'").fetchone()[0]
        contenido_publicado = c.execute("SELECT COUNT(*) FROM marketing_contenido WHERE estado='Publicado'").fetchone()[0]
        total_conversiones = c.execute("SELECT COALESCE(SUM(conversiones),0) FROM marketing_contenido").fetchone()[0]
        total_alcance = c.execute("SELECT COALESCE(SUM(alcance),0) FROM marketing_contenido").fetchone()[0]
        ventas_total = c.execute("SELECT COALESCE(SUM(resultado_ventas),0) FROM marketing_campanas").fetchone()[0]

        # ROI global
        roi = 0
        if presupuesto_gastado > 0:
            roi = round(((ventas_total - presupuesto_gastado) / presupuesto_gastado) * 100, 1)

        # Top influencer por conversiones
        top_inf = c.execute("""
            SELECT i.nombre, i.red_social, COALESCE(SUM(ci.conversiones),0) as conv
            FROM marketing_influencers i
            LEFT JOIN marketing_campana_influencer ci ON ci.influencer_id=i.id
            GROUP BY i.id ORDER BY conv DESC LIMIT 1
        """).fetchone()

        # Campañas activas
        campanas_activas = _fmt_many(c.execute("""
            SELECT id, nombre, tipo, estado, presupuesto, presupuesto_gastado,
                   fecha_inicio, fecha_fin, resultado_ventas
            FROM marketing_campanas
            WHERE estado IN ('Activa','Planificada')
            ORDER BY fecha_inicio DESC LIMIT 6
        """).fetchall())

        # Contenido reciente
        contenido_reciente = _fmt_many(c.execute("""
            SELECT mc.id, mc.tipo, mc.plataforma, mc.estado, mc.fecha_publicacion,
                   mc.likes, mc.alcance, mc.conversiones,
                   mc2.nombre as campana,
                   mi.nombre as influencer
            FROM marketing_contenido mc
            LEFT JOIN marketing_campanas mc2 ON mc2.id=mc.campana_id
            LEFT JOIN marketing_influencers mi ON mi.id=mc.influencer_id
            ORDER BY mc.fecha_creacion DESC LIMIT 8
        """).fetchall())

        # Tendencias mensuales: liberaciones PT últimos 6 meses por SKU
        seis_meses = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        tendencias = _fmt_many(c.execute("""
            SELECT sku, COALESCE(SUM(unidades),0) as total_liberado,
                   strftime('%Y-%m', creado_en) as mes
            FROM liberaciones
            WHERE creado_en >= ? AND sku IS NOT NULL AND sku != ''
            GROUP BY sku, mes ORDER BY mes DESC, total_liberado DESC
            LIMIT 30
        """, (seis_meses,)).fetchall())

        # Presupuesto por canal
        por_canal = _fmt_many(c.execute("""
            SELECT canal, COUNT(*) as campanas,
                   COALESCE(SUM(presupuesto),0) as presupuesto_total,
                   COALESCE(SUM(resultado_ventas),0) as ventas_total
            FROM marketing_campanas
            WHERE canal IS NOT NULL AND canal != ''
            GROUP BY canal ORDER BY presupuesto_total DESC
        """).fetchall())

        return jsonify({
            "kpis": {
                "total_campanas": total_campanas,
                "activas": activas,
                "presupuesto_total": round(presupuesto_total, 0),
                "presupuesto_gastado": round(presupuesto_gastado, 0),
                "pct_ejecutado": round((presupuesto_gastado / presupuesto_total * 100) if presupuesto_total > 0 else 0, 1),
                "total_influencers": total_influencers,
                "contenido_publicado": contenido_publicado,
                "total_conversiones": total_conversiones,
                "total_alcance": total_alcance,
                "ventas_total": round(ventas_total, 0),
                "roi_global": roi,
            },
            "top_influencer": _fmt(top_inf),
            "campanas_activas": campanas_activas,
            "contenido_reciente": contenido_reciente,
            "tendencias": tendencias,
            "por_canal": por_canal,
        })
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# CAMPAÑAS
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/campanas", methods=["GET", "POST"])
def mkt_campanas():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            estado = request.args.get("estado", "")
            if estado:
                rows = c.execute("""
                    SELECT * FROM marketing_campanas WHERE estado=?
                    ORDER BY fecha_creacion DESC
                """, (estado,)).fetchall()
            else:
                rows = c.execute("""
                    SELECT * FROM marketing_campanas ORDER BY fecha_creacion DESC
                """).fetchall()
            result = []
            for row in rows:
                r = dict(row)
                # Contar influencers asignados
                r["num_influencers"] = c.execute(
                    "SELECT COUNT(*) FROM marketing_campana_influencer WHERE campana_id=?",
                    (r["id"],)
                ).fetchone()[0]
                r["num_contenido"] = c.execute(
                    "SELECT COUNT(*) FROM marketing_contenido WHERE campana_id=?",
                    (r["id"],)
                ).fetchone()[0]
                result.append(r)
            return jsonify(result)

        # POST — crear campaña
        d = request.get_json() or {}
        if not d.get("nombre"):
            return jsonify({"error": "nombre requerido"}), 400
        c.execute("""
            INSERT INTO marketing_campanas
            (nombre, tipo, estado, presupuesto, presupuesto_gastado,
             fecha_inicio, fecha_fin, sku_objetivo, objetivo_unidades,
             canal, notas, creada_por)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d["nombre"], d.get("tipo", "Digital"), d.get("estado", "Planificada"),
            d.get("presupuesto", 0), d.get("presupuesto_gastado", 0),
            d.get("fecha_inicio"), d.get("fecha_fin"),
            d.get("sku_objetivo", ""), d.get("objetivo_unidades", 0),
            d.get("canal", ""), d.get("notas", ""), u
        ))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201
    finally:
        conn.close()


@bp.route("/api/marketing/campanas/<int:cid>", methods=["GET", "PUT", "DELETE"])
def mkt_campana_detail(cid):
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            row = c.execute("SELECT * FROM marketing_campanas WHERE id=?", (cid,)).fetchone()
            if not row:
                return jsonify({"error": "No encontrada"}), 404
            r = dict(row)
            # Influencers asignados
            r["influencers"] = _fmt_many(c.execute("""
                SELECT ci.*, i.nombre, i.red_social, i.usuario_red, i.seguidores, i.engagement_rate
                FROM marketing_campana_influencer ci
                JOIN marketing_influencers i ON i.id=ci.influencer_id
                WHERE ci.campana_id=?
            """, (cid,)).fetchall())
            # Contenido
            r["contenido"] = _fmt_many(c.execute("""
                SELECT mc.*, i.nombre as influencer_nombre
                FROM marketing_contenido mc
                LEFT JOIN marketing_influencers i ON i.id=mc.influencer_id
                WHERE mc.campana_id=?
                ORDER BY mc.fecha_publicacion DESC
            """, (cid,)).fetchall())
            return jsonify(r)

        if request.method == "PUT":
            d = request.get_json() or {}
            campos = ["nombre", "tipo", "estado", "presupuesto", "presupuesto_gastado",
                      "fecha_inicio", "fecha_fin", "sku_objetivo", "objetivo_unidades",
                      "resultado_unidades", "resultado_ventas", "canal", "notas"]
            updates = {k: d[k] for k in campos if k in d}
            if not updates:
                return jsonify({"error": "Nada que actualizar"}), 400
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE marketing_campanas SET {set_clause} WHERE id=?",
                      list(updates.values()) + [cid])
            conn.commit()
            return jsonify({"ok": True})

        if request.method == "DELETE":
            if u not in ADMIN_USERS:
                return jsonify({"error": "Sin permiso"}), 403
            c.execute("DELETE FROM marketing_campana_influencer WHERE campana_id=?", (cid,))
            c.execute("DELETE FROM marketing_contenido WHERE campana_id=?", (cid,))
            c.execute("DELETE FROM marketing_campanas WHERE id=?", (cid,))
            conn.commit()
            return jsonify({"ok": True})
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# INFLUENCERS
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/influencers", methods=["GET", "POST"])
def mkt_influencers():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            q = request.args.get("q", "")
            estado = request.args.get("estado", "")
            base = "SELECT * FROM marketing_influencers"
            conds, params = [], []
            if q:
                conds.append("(nombre LIKE ? OR usuario_red LIKE ? OR nicho LIKE ?)")
                params += [f"%{q}%", f"%{q}%", f"%{q}%"]
            if estado:
                conds.append("estado=?")
                params.append(estado)
            sql = base + (" WHERE " + " AND ".join(conds) if conds else "") + " ORDER BY nombre"
            rows = c.execute(sql, params).fetchall()
            result = []
            for row in rows:
                r = dict(row)
                # Estadísticas agregadas
                stats = c.execute("""
                    SELECT COUNT(DISTINCT campana_id) as campanas,
                           COALESCE(SUM(conversiones),0) as conversiones,
                           COALESCE(SUM(alcance_real),0) as alcance_total,
                           COALESCE(SUM(monto_pagado),0) as total_pagado
                    FROM marketing_campana_influencer WHERE influencer_id=?
                """, (r["id"],)).fetchone()
                r["stats"] = _fmt(stats)
                result.append(r)
            return jsonify(result)

        d = request.get_json() or {}
        if not d.get("nombre"):
            return jsonify({"error": "nombre requerido"}), 400
        c.execute("""
            INSERT INTO marketing_influencers
            (nombre, red_social, usuario_red, seguidores, engagement_rate,
             nicho, tarifa, estado, email, telefono, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d["nombre"], d.get("red_social", "Instagram"), d.get("usuario_red", ""),
            d.get("seguidores", 0), d.get("engagement_rate", 0),
            d.get("nicho", ""), d.get("tarifa", 0), d.get("estado", "Activo"),
            d.get("email", ""), d.get("telefono", ""), d.get("notas", "")
        ))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201
    finally:
        conn.close()


@bp.route("/api/marketing/influencers/<int:iid>", methods=["GET", "PUT", "DELETE"])
def mkt_influencer_detail(iid):
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            row = c.execute("SELECT * FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
            if not row:
                return jsonify({"error": "No encontrado"}), 404
            r = dict(row)
            r["campanas"] = _fmt_many(c.execute("""
                SELECT ci.*, mc.nombre as campana_nombre, mc.estado as campana_estado,
                       mc.fecha_inicio, mc.fecha_fin
                FROM marketing_campana_influencer ci
                JOIN marketing_campanas mc ON mc.id=ci.campana_id
                WHERE ci.influencer_id=?
                ORDER BY mc.fecha_inicio DESC
            """, (iid,)).fetchall())
            return jsonify(r)

        if request.method == "PUT":
            d = request.get_json() or {}
            campos = ["nombre", "red_social", "usuario_red", "seguidores", "engagement_rate",
                      "nicho", "tarifa", "estado", "email", "telefono", "notas"]
            updates = {k: d[k] for k in campos if k in d}
            if not updates:
                return jsonify({"error": "Nada que actualizar"}), 400
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE marketing_influencers SET {set_clause} WHERE id=?",
                      list(updates.values()) + [iid])
            conn.commit()
            return jsonify({"ok": True})

        if request.method == "DELETE":
            if u not in ADMIN_USERS:
                return jsonify({"error": "Sin permiso"}), 403
            c.execute("DELETE FROM marketing_campana_influencer WHERE influencer_id=?", (iid,))
            c.execute("DELETE FROM marketing_influencers WHERE id=?", (iid,))
            conn.commit()
            return jsonify({"ok": True})
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# ASIGNACIÓN CAMPAÑA ↔ INFLUENCER
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/campana-influencer", methods=["POST"])
def mkt_asignar_influencer():
    u, err, code = _auth()
    if err:
        return err, code
    d = request.get_json() or {}
    if not d.get("campana_id") or not d.get("influencer_id"):
        return jsonify({"error": "campana_id e influencer_id requeridos"}), 400
    conn = _db()
    c = conn.cursor()
    try:
        # Verificar si ya existe
        exists = c.execute(
            "SELECT id FROM marketing_campana_influencer WHERE campana_id=? AND influencer_id=?",
            (d["campana_id"], d["influencer_id"])
        ).fetchone()
        if exists:
            return jsonify({"error": "Ya asignado"}), 409
        c.execute("""
            INSERT INTO marketing_campana_influencer
            (campana_id, influencer_id, monto_pactado, estado, notas)
            VALUES (?,?,?,?,?)
        """, (d["campana_id"], d["influencer_id"],
              d.get("monto_pactado", 0), d.get("estado", "Pendiente"), d.get("notas", "")))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201
    finally:
        conn.close()


@bp.route("/api/marketing/campana-influencer/<int:rid>", methods=["PUT"])
def mkt_update_asignacion(rid):
    u, err, code = _auth()
    if err:
        return err, code
    d = request.get_json() or {}
    campos = ["monto_pactado", "monto_pagado", "fecha_pago",
              "alcance_real", "impresiones", "clicks", "conversiones", "estado", "notas"]
    updates = {k: d[k] for k in campos if k in d}
    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400
    conn = _db()
    c = conn.cursor()
    try:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        c.execute(f"UPDATE marketing_campana_influencer SET {set_clause} WHERE id=?",
                  list(updates.values()) + [rid])
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# CONTENIDO
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/contenido", methods=["GET", "POST"])
def mkt_contenido():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            campana_id = request.args.get("campana_id", "")
            estado = request.args.get("estado", "")
            base = """
                SELECT mc.*, c.nombre as campana_nombre, i.nombre as influencer_nombre
                FROM marketing_contenido mc
                LEFT JOIN marketing_campanas c ON c.id=mc.campana_id
                LEFT JOIN marketing_influencers i ON i.id=mc.influencer_id
            """
            conds, params = [], []
            if campana_id:
                conds.append("mc.campana_id=?")
                params.append(campana_id)
            if estado:
                conds.append("mc.estado=?")
                params.append(estado)
            sql = base + (" WHERE " + " AND ".join(conds) if conds else "") + \
                  " ORDER BY mc.fecha_publicacion DESC, mc.fecha_creacion DESC LIMIT 100"
            return jsonify(_fmt_many(c.execute(sql, params).fetchall()))

        d = request.get_json() or {}
        c.execute("""
            INSERT INTO marketing_contenido
            (campana_id, influencer_id, tipo, plataforma, fecha_publicacion,
             estado, caption, url_publicacion, likes, comentarios, shares,
             guardados, alcance, impresiones, clicks, conversiones, notas, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d.get("campana_id"), d.get("influencer_id"),
            d.get("tipo", "Post"), d.get("plataforma", "Instagram"),
            d.get("fecha_publicacion"), d.get("estado", "Borrador"),
            d.get("caption", ""), d.get("url_publicacion", ""),
            d.get("likes", 0), d.get("comentarios", 0), d.get("shares", 0),
            d.get("guardados", 0), d.get("alcance", 0), d.get("impresiones", 0),
            d.get("clicks", 0), d.get("conversiones", 0),
            d.get("notas", ""), u
        ))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201
    finally:
        conn.close()


@bp.route("/api/marketing/contenido/<int:cid>", methods=["PUT", "DELETE"])
def mkt_contenido_detail(cid):
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "DELETE":
            c.execute("DELETE FROM marketing_contenido WHERE id=?", (cid,))
            conn.commit()
            return jsonify({"ok": True})
        d = request.get_json() or {}
        campos = ["tipo", "plataforma", "fecha_publicacion", "estado", "caption",
                  "url_publicacion", "likes", "comentarios", "shares", "guardados",
                  "alcance", "impresiones", "clicks", "conversiones", "notas"]
        updates = {k: d[k] for k in campos if k in d}
        if not updates:
            return jsonify({"error": "Nada que actualizar"}), 400
        set_clause = ", ".join(f"{k}=?" for k in updates)
        c.execute(f"UPDATE marketing_contenido SET {set_clause} WHERE id=?",
                  list(updates.values()) + [cid])
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/analytics/roi")
def mkt_analytics_roi():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        # ROI por campaña
        campanas = _fmt_many(c.execute("""
            SELECT id, nombre, tipo, canal, presupuesto, presupuesto_gastado,
                   resultado_ventas, objetivo_unidades, resultado_unidades,
                   fecha_inicio, fecha_fin,
                   CASE WHEN presupuesto_gastado > 0
                        THEN ROUND((resultado_ventas - presupuesto_gastado) / presupuesto_gastado * 100, 1)
                        ELSE 0 END as roi_pct,
                   CASE WHEN objetivo_unidades > 0
                        THEN ROUND(resultado_unidades * 100.0 / objetivo_unidades, 1)
                        ELSE 0 END as pct_objetivo
            FROM marketing_campanas
            ORDER BY roi_pct DESC
        """).fetchall())

        # ROI por influencer
        influencers = _fmt_many(c.execute("""
            SELECT i.id, i.nombre, i.red_social, i.seguidores, i.engagement_rate,
                   COUNT(DISTINCT ci.campana_id) as campanas,
                   COALESCE(SUM(ci.monto_pagado),0) as total_invertido,
                   COALESCE(SUM(ci.conversiones),0) as conversiones,
                   COALESCE(SUM(ci.alcance_real),0) as alcance_total,
                   COALESCE(SUM(ci.clicks),0) as clicks_total,
                   CASE WHEN SUM(ci.monto_pagado) > 0 AND SUM(ci.conversiones) > 0
                        THEN ROUND(SUM(ci.monto_pagado) / SUM(ci.conversiones), 0)
                        ELSE 0 END as costo_por_conversion
            FROM marketing_influencers i
            LEFT JOIN marketing_campana_influencer ci ON ci.influencer_id=i.id
            GROUP BY i.id ORDER BY campanas DESC, conversiones DESC
        """).fetchall())

        # ROI por canal
        por_canal = _fmt_many(c.execute("""
            SELECT canal,
                   COUNT(*) as campanas,
                   COALESCE(SUM(presupuesto_gastado),0) as total_invertido,
                   COALESCE(SUM(resultado_ventas),0) as total_ventas,
                   CASE WHEN SUM(presupuesto_gastado) > 0
                        THEN ROUND((SUM(resultado_ventas) - SUM(presupuesto_gastado))
                             / SUM(presupuesto_gastado) * 100, 1)
                        ELSE 0 END as roi_pct
            FROM marketing_campanas
            WHERE canal IS NOT NULL AND canal != ''
            GROUP BY canal ORDER BY roi_pct DESC
        """).fetchall())

        return jsonify({"campanas": campanas, "influencers": influencers, "por_canal": por_canal})
    finally:
        conn.close()


@bp.route("/api/marketing/analytics/tendencias")
def mkt_analytics_tendencias():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        meses = int(request.args.get("meses", 6))
        desde = (datetime.now() - timedelta(days=meses * 30)).strftime("%Y-%m-%d")

        # Liberaciones por SKU y mes
        por_sku_mes = _fmt_many(c.execute("""
            SELECT sku, strftime('%Y-%m', creado_en) as mes,
                   SUM(unidades) as unidades,
                   COUNT(*) as liberaciones
            FROM liberaciones
            WHERE creado_en >= ? AND sku IS NOT NULL AND sku != ''
            GROUP BY sku, mes ORDER BY mes DESC, unidades DESC
        """, (desde,)).fetchall())

        # Top SKUs últimos 90 días vs anteriores 90 (crecimiento)
        hoy = datetime.now().strftime("%Y-%m-%d")
        hace90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        hace180 = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        reciente = {}
        for row in c.execute("""
            SELECT sku, SUM(unidades) as total FROM liberaciones
            WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL
            GROUP BY sku
        """, (hace90, hoy)).fetchall():
            reciente[row["sku"]] = row["total"]

        anterior = {}
        for row in c.execute("""
            SELECT sku, SUM(unidades) as total FROM liberaciones
            WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL
            GROUP BY sku
        """, (hace180, hace90)).fetchall():
            anterior[row["sku"]] = row["total"]

        crecimiento = []
        todos_sku = set(list(reciente.keys()) + list(anterior.keys()))
        for sku in todos_sku:
            rec = reciente.get(sku, 0)
            ant = anterior.get(sku, 0)
            if ant > 0:
                pct = round((rec - ant) / ant * 100, 1)
            elif rec > 0:
                pct = 100.0
            else:
                pct = 0.0
            crecimiento.append({"sku": sku, "reciente_90d": rec, "anterior_90d": ant, "crecimiento_pct": pct})
        crecimiento.sort(key=lambda x: x["crecimiento_pct"], reverse=True)

        return jsonify({
            "por_sku_mes": por_sku_mes,
            "crecimiento": crecimiento[:20],
            "periodo_meses": meses
        })
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# AGENTES IA (internos — sin API externa)
# ──────────────────────────────────────────────────────────────────────────────
def _log_agente(c, agente, accion, resultado, user):
    c.execute("""
        INSERT INTO marketing_agentes_log (agente, accion, resultado, ejecutado_por)
        VALUES (?,?,?,?)
    """, (agente, accion, json.dumps(resultado, ensure_ascii=False), user))


@bp.route("/api/marketing/agentes/log")
def mkt_agentes_log():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        agente = request.args.get("agente", "")
        if agente:
            rows = c.execute("""
                SELECT id, agente, accion, fecha, ejecutado_por,
                       SUBSTR(resultado, 1, 200) as resultado_preview
                FROM marketing_agentes_log WHERE agente=?
                ORDER BY fecha DESC LIMIT 30
            """, (agente,)).fetchall()
        else:
            rows = c.execute("""
                SELECT id, agente, accion, fecha, ejecutado_por,
                       SUBSTR(resultado, 1, 200) as resultado_preview
                FROM marketing_agentes_log ORDER BY fecha DESC LIMIT 50
            """).fetchall()
        return jsonify(_fmt_many(rows))
    finally:
        conn.close()


@bp.route("/api/marketing/agentes/<agente>", methods=["POST"])
def mkt_ejecutar_agente(agente):
    u, err, code = _auth()
    if err:
        return err, code

    agentes_validos = {"oportunidad", "roi", "tendencias", "brief", "presupuesto"}
    if agente not in agentes_validos:
        return jsonify({"error": f"Agente desconocido. Válidos: {agentes_validos}"}), 400

    conn = _db()
    c = conn.cursor()
    try:
        resultado = {}

        # ── Agente 1: Oportunidad ────────────────────────────────────────────
        if agente == "oportunidad":
            # SKUs con alto stock y baja liberación reciente → candidatos a impulsar
            hace90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            stock_rows = c.execute("""
                SELECT sku, SUM(unidades_disponible) as stock_total, MAX(precio_base) as precio_base
                FROM stock_pt WHERE estado='Disponible' GROUP BY sku ORDER BY stock_total DESC LIMIT 20
            """).fetchall()

            recomendaciones = []
            for row in stock_rows:
                sku = row["sku"]
                stock = row["stock_total"]
                precio = row["precio_base"] or 0

                lib_90 = c.execute("""
                    SELECT COALESCE(SUM(unidades),0) FROM liberaciones
                    WHERE sku=? AND creado_en >= ?
                """, (sku, hace90)).fetchone()[0]

                lib_30 = c.execute("""
                    SELECT COALESCE(SUM(unidades),0) FROM liberaciones
                    WHERE sku=? AND creado_en >= ?
                """, (sku, hace30)).fetchone()[0]

                # Ratio de rotación (unidades/mes en últimos 90d)
                rotacion_mensual = round(lib_90 / 3, 1)
                meses_inventario = round(stock / rotacion_mensual, 1) if rotacion_mensual > 0 else 99

                # Score oportunidad: alto stock + baja rotación reciente
                score = 0
                razones = []
                if stock > 500:
                    score += 2
                    razones.append(f"Stock alto ({int(stock)} uds)")
                if meses_inventario > 3:
                    score += 3
                    razones.append(f"{meses_inventario} meses de inventario")
                if lib_30 < lib_90 / 3 * 0.7:
                    score += 2
                    razones.append("Ventas cayendo vs promedio 90d")
                if precio > 0 and stock * precio > 5000000:
                    score += 2
                    razones.append(f"Capital inmovilizado ${int(stock * precio):,}")

                if score >= 3:
                    recomendaciones.append({
                        "sku": sku,
                        "stock": int(stock),
                        "precio": precio,
                        "lib_30d": int(lib_30),
                        "lib_90d": int(lib_90),
                        "rotacion_mensual": rotacion_mensual,
                        "meses_inventario": meses_inventario,
                        "score": score,
                        "razones": razones,
                        "accion_sugerida": f"Campaña urgente para {sku}: {meses_inventario}m de stock. Canal recomendado: Influencer + Promo Digital."
                    })

            recomendaciones.sort(key=lambda x: x["score"], reverse=True)
            resultado = {
                "agente": "Oportunidad",
                "titulo": "SKUs con oportunidad de impulso",
                "fecha": datetime.now().isoformat(),
                "recomendaciones": recomendaciones[:10],
                "resumen": f"{len(recomendaciones)} SKUs identificados con oportunidad de campaña. "
                           f"Prioridad máxima: {recomendaciones[0]['sku'] if recomendaciones else 'N/A'}"
            }
            _log_agente(c, "oportunidad", "scan_stock_liberaciones", resultado, u)

        # ── Agente 2: ROI ────────────────────────────────────────────────────
        elif agente == "roi":
            campanas = c.execute("""
                SELECT id, nombre, tipo, canal, presupuesto_gastado, resultado_ventas,
                       resultado_unidades, objetivo_unidades,
                       CASE WHEN presupuesto_gastado > 0
                            THEN ROUND((resultado_ventas - presupuesto_gastado) / presupuesto_gastado * 100, 1)
                            ELSE NULL END as roi_pct
                FROM marketing_campanas
                WHERE presupuesto_gastado > 0
                ORDER BY roi_pct DESC NULLS LAST
            """).fetchall()

            campanas_data = []
            for row in campanas:
                r = dict(row)
                inf_count = c.execute(
                    "SELECT COUNT(*) FROM marketing_campana_influencer WHERE campana_id=?",
                    (r["id"],)
                ).fetchone()[0]
                r["influencers"] = inf_count
                campanas_data.append(r)

            mejor = campanas_data[0] if campanas_data else None
            peor = campanas_data[-1] if len(campanas_data) > 1 else None

            total_invertido = sum(r["presupuesto_gastado"] for r in campanas_data)
            total_ventas = sum(r["resultado_ventas"] or 0 for r in campanas_data)
            roi_global = round((total_ventas - total_invertido) / total_invertido * 100, 1) if total_invertido > 0 else 0

            recomendaciones = []
            for r in campanas_data:
                if r["roi_pct"] and r["roi_pct"] < 0:
                    recomendaciones.append(f"Revisar campaña '{r['nombre']}': ROI negativo ({r['roi_pct']}%)")
                elif r["roi_pct"] and r["roi_pct"] > 200:
                    recomendaciones.append(f"Escalar campaña '{r['nombre']}': ROI excelente ({r['roi_pct']}%)")

            resultado = {
                "agente": "ROI",
                "titulo": "Análisis de retorno por campaña",
                "fecha": datetime.now().isoformat(),
                "roi_global_pct": roi_global,
                "total_invertido": total_invertido,
                "total_ventas_atribuidas": total_ventas,
                "campanas": campanas_data,
                "mejor_campana": mejor["nombre"] if mejor and mejor.get("roi_pct") else "Sin datos",
                "peor_campana": peor["nombre"] if peor and peor.get("roi_pct") else "Sin datos",
                "recomendaciones": recomendaciones
            }
            _log_agente(c, "roi", "calcular_roi_campanas", resultado, u)

        # ── Agente 3: Tendencias ─────────────────────────────────────────────
        elif agente == "tendencias":
            hace90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            hace180 = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
            hoy = datetime.now().strftime("%Y-%m-%d")

            reciente = {r["sku"]: r["total"] for r in c.execute("""
                SELECT sku, SUM(unidades) as total FROM liberaciones
                WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL GROUP BY sku
            """, (hace90, hoy)).fetchall()}

            anterior = {r["sku"]: r["total"] for r in c.execute("""
                SELECT sku, SUM(unidades) as total FROM liberaciones
                WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL GROUP BY sku
            """, (hace180, hace90)).fetchall()}

            tendencias = []
            for sku in set(list(reciente.keys()) + list(anterior.keys())):
                rec = reciente.get(sku, 0)
                ant = anterior.get(sku, 0)
                pct = round((rec - ant) / ant * 100, 1) if ant > 0 else (100.0 if rec > 0 else 0.0)
                tendencias.append({"sku": sku, "reciente_90d": rec, "anterior_90d": ant, "variacion_pct": pct})
            tendencias.sort(key=lambda x: x["variacion_pct"], reverse=True)

            en_alza = [t for t in tendencias if t["variacion_pct"] > 20][:5]
            en_caida = [t for t in tendencias if t["variacion_pct"] < -20][:5]
            estables = [t for t in tendencias if abs(t["variacion_pct"]) <= 20][:5]

            alertas = []
            for t in en_alza:
                alertas.append(f"SKU {t['sku']} subiendo {t['variacion_pct']}% — reforzar stock y marketing")
            for t in en_caida:
                alertas.append(f"SKU {t['sku']} bajando {t['variacion_pct']}% — campaña de reactivación recomendada")

            resultado = {
                "agente": "Tendencias",
                "titulo": "Análisis de tendencias por SKU",
                "fecha": datetime.now().isoformat(),
                "en_alza": en_alza,
                "en_caida": en_caida,
                "estables": estables,
                "alertas": alertas,
                "total_skus_analizados": len(tendencias)
            }
            _log_agente(c, "tendencias", "analizar_liberaciones", resultado, u)

        # ── Agente 4: Brief ──────────────────────────────────────────────────
        elif agente == "brief":
            params = request.get_json() or {}
            campana_id = params.get("campana_id")
            campana = None
            if campana_id:
                row = c.execute("SELECT * FROM marketing_campanas WHERE id=?", (campana_id,)).fetchone()
                if row:
                    campana = dict(row)

            # Top SKUs recientes para sugerir en brief
            hace60 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            top_skus = c.execute("""
                SELECT sku, SUM(unidades) as total FROM liberaciones
                WHERE creado_en >= ? AND sku IS NOT NULL
                GROUP BY sku ORDER BY total DESC LIMIT 5
            """, (hace60,)).fetchall()
            top_skus_list = [r["sku"] for r in top_skus]

            nombre_campana = campana["nombre"] if campana else "Nueva Campaña"
            sku_objetivo = campana["sku_objetivo"] if campana else ", ".join(top_skus_list[:3])
            presupuesto = campana["presupuesto"] if campana else 0
            fecha_inicio = campana["fecha_inicio"] if campana else datetime.now().strftime("%Y-%m-%d")

            brief = {
                "titulo": f"Brief Campaña: {nombre_campana}",
                "marca": "ÁNIMUS Lab",
                "concepto": "Skincare científico para piel latina — belleza auténtica, respaldada por ciencia",
                "productos_objetivo": sku_objetivo,
                "objetivo_principal": "Generar conversiones directas y aumentar reconocimiento de marca",
                "kpis": ["Tasa de conversión > 2%", "Alcance mínimo 50,000", "Engagement rate > 3.5%", "CPM < $15,000 COP"],
                "mensajes_clave": [
                    "Formulación dermatológicamente probada",
                    "Ingredientes activos de alta concentración",
                    "Desarrollado para el clima y la piel latinoamericana",
                    "Sin parabenos, sin colorantes artificiales"
                ],
                "entregables": ["1 Reel (30-60s)", "3 Stories (product demo)", "1 Post carrusel", "1 Foto lifestyle"],
                "lineamientos_creativos": [
                    "Mostrar textura y aplicación del producto",
                    "Resultados antes/después (reales, no editados)",
                    "Tono: profesional pero cercano",
                    "Colores: paleta nude/blanco/dorado de ÁNIMUS"
                ],
                "restricciones": [
                    "No comparar con competencia por nombre",
                    "No hacer claims médicos",
                    "Incluir #AnimalFree #Dermatologicamente si aplica"
                ],
                "hashtags_sugeridos": ["#ANIMUSLab", "#SkincareColombiano", "#PielLatina", "#SkincareCientifico"],
                "presupuesto_indicativo": f"${int(presupuesto):,} COP" if presupuesto > 0 else "Por definir",
                "fecha_inicio": fecha_inicio,
                "aprobacion_contenido": "Todo contenido debe ser aprobado 48h antes de publicar",
                "contacto": "marketing@animuslab.com"
            }

            resultado = {
                "agente": "Brief",
                "titulo": "Brief para influencer generado",
                "fecha": datetime.now().isoformat(),
                "brief": brief,
                "campana_id": campana_id
            }
            _log_agente(c, "brief", f"generar_brief_campana_{campana_id}", resultado, u)

        # ── Agente 5: Presupuesto ────────────────────────────────────────────
        elif agente == "presupuesto":
            params = request.get_json() or {}
            presupuesto_total = params.get("presupuesto_total", 5000000)

            # Calcular ROI histórico por canal para distribuir
            canales = c.execute("""
                SELECT canal,
                       COUNT(*) as campanas,
                       AVG(CASE WHEN presupuesto_gastado > 0
                                THEN (resultado_ventas - presupuesto_gastado) / presupuesto_gastado * 100
                                ELSE NULL END) as roi_promedio,
                       SUM(presupuesto_gastado) as total_invertido,
                       SUM(resultado_ventas) as total_ventas
                FROM marketing_campanas
                WHERE canal IS NOT NULL AND canal != '' AND presupuesto_gastado > 0
                GROUP BY canal
            """).fetchall()

            canales_data = [dict(r) for r in canales]
            # Si no hay datos históricos, usar distribución por defecto
            if not canales_data:
                canales_data = [
                    {"canal": "Influencer Instagram", "roi_promedio": 180, "recomendacion_pct": 40},
                    {"canal": "Influencer TikTok",    "roi_promedio": 220, "recomendacion_pct": 30},
                    {"canal": "Email Marketing",      "roi_promedio": 350, "recomendacion_pct": 15},
                    {"canal": "Pauta Digital",        "roi_promedio": 120, "recomendacion_pct": 15},
                ]
                distribucion = canales_data
            else:
                # Distribuir proporcionalmente al ROI promedio
                roi_total = sum(max(r.get("roi_promedio") or 0, 0) for r in canales_data)
                for r in canales_data:
                    roi = max(r.get("roi_promedio") or 0, 0)
                    r["recomendacion_pct"] = round(roi / roi_total * 100) if roi_total > 0 else 0
                distribucion = canales_data

            # Asignar montos
            for r in distribucion:
                r["monto_sugerido"] = round(presupuesto_total * r["recomendacion_pct"] / 100, 0)

            # Proyección de ventas esperadas
            roi_promedio_global = sum(
                (r.get("roi_promedio") or 0) * r["recomendacion_pct"] / 100
                for r in distribucion
            )
            ventas_proyectadas = round(presupuesto_total * (1 + roi_promedio_global / 100), 0)

            resultado = {
                "agente": "Presupuesto",
                "titulo": "Recomendación de distribución de presupuesto",
                "fecha": datetime.now().isoformat(),
                "presupuesto_total": presupuesto_total,
                "distribucion": distribucion,
                "ventas_proyectadas": ventas_proyectadas,
                "roi_proyectado_pct": round(roi_promedio_global, 1),
                "notas": [
                    "Distribución basada en ROI histórico de campañas anteriores",
                    "Email marketing ofrece mejor ROI si la base de datos está activa",
                    "Influencers TikTok muestran mejor engagement en target 18-28",
                    "Reservar 10% como fondo de contingencia para oportunidades emergentes"
                ]
            }
            _log_agente(c, "presupuesto", f"calcular_distribucion_{presupuesto_total}", resultado, u)

        conn.commit()
        return jsonify(resultado)
    finally:
        conn.close()


@bp.route("/api/marketing/agentes/log/<int:log_id>")
def mkt_agente_log_detalle(log_id):
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        row = c.execute("SELECT * FROM marketing_agentes_log WHERE id=?", (log_id,)).fetchone()
        if not row:
            return jsonify({"error": "No encontrado"}), 404
        r = dict(row)
        try:
            r["resultado"] = json.loads(r["resultado"])
        except Exception:
            pass
        return jsonify(r)
    finally:
        conn.close()
