"""
marketing.py — Blueprint módulo Marketing
Campañas, Influencers, Contenido, Analytics, 5 Agentes IA internos
"""
import sqlite3, urllib.request
import traceback
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session

from config import DB_PATH, ADMIN_USERS, MARKETING_USERS
from database import get_db

bp = Blueprint("marketing", __name__)
CALENDARIO_COSMETICO = [
    {"evento": "Día de la Mujer",       "fecha": "2026-03-08", "color": "#e91e8c", "multiplicador": 1.8},
    {"evento": "Día de la Madre",        "fecha": "2026-05-10", "color": "#d4af37", "multiplicador": 3.0},
    {"evento": "Mitad de Año",           "fecha": "2026-06-30", "color": "#4fc3f7", "multiplicador": 1.5},
    {"evento": "Día del Padre",          "fecha": "2026-06-21", "color": "#81c784", "multiplicador": 1.4},
    {"evento": "Amor y Amistad",         "fecha": "2026-09-19", "color": "#ff8a65", "multiplicador": 2.2},
    {"evento": "Halloween",              "fecha": "2026-10-31", "color": "#ff6f00", "multiplicador": 1.3},
    {"evento": "Black Friday",           "fecha": "2026-11-27", "color": "#212121", "multiplicador": 3.5},
    {"evento": "Cyber Monday",           "fecha": "2026-11-30", "color": "#1565c0", "multiplicador": 2.5},
    {"evento": "Navidad",                "fecha": "2026-12-25", "color": "#c62828", "multiplicador": 2.8},
    {"evento": "Fin de Año / Rituales",  "fecha": "2026-12-31", "color": "#6a1b9a", "multiplicador": 2.0},
]

# MARKETING_USERS importado desde config (fuente única de verdad para accesos)

def _db():
    conn = get_db()

    return conn

def _ig_resolve_token(conn):
    """Resuelve el Page Access Token y el IG user ID correcto.

    El token guardado puede ser:
    - User Access Token (UAT): /me devuelve el usuario.
      → Se llama /me/accounts para obtener páginas y sus Page Tokens.
      → Por cada página se verifica si tiene instagram_business_account.
    - Page Access Token (PAT): /me devuelve la página.
      → Se prueba directamente el instagram_business_account de esa página.

    Retorna (token_resuelto, ig_user_id) o (None, None) si falla todo.
    """
    token = _cfg(conn, "instagram_token")
    stored_uid = _cfg(conn, "instagram_user_id")
    if not token:
        return None, None

    def _fetch(url):
        import urllib.request, json
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return json.loads(r.read()), None
        except Exception as e:
            return None, str(e)

    # Paso 1: ¿qué devuelve /me con este token?
    me_data, me_err = _fetch(f"https://graph.facebook.com/v19.0/me?access_token={token}")
    if me_err or not me_data:
        return token, stored_uid   # fallback

    me_id = me_data.get("id", "")

    # Paso 2a: probar como si token ya es page token
    # → GET /{me_id}?fields=instagram_business_account
    ig_data, _ = _fetch(
        f"https://graph.facebook.com/v19.0/{me_id}"
        f"?fields=instagram_business_account&access_token={token}"
    )
    if ig_data:
        linked = (ig_data.get("instagram_business_account") or {}).get("id")
        if linked:
            # Token ya es un page token y tiene IG conectado
            return token, linked

    # Paso 2b: token es UAT → obtener pages con /me/accounts
    accounts_data, _ = _fetch(
        f"https://graph.facebook.com/v19.0/me/accounts?access_token={token}&limit=20"
    )
    if accounts_data:
        for page in accounts_data.get("data", []):
            pt = page.get("access_token")
            pid = page.get("id")
            if not pt or not pid:
                continue
            ig2, _ = _fetch(
                f"https://graph.facebook.com/v19.0/{pid}"
                f"?fields=instagram_business_account&access_token={pt}"
            )
            if ig2:
                linked2 = (ig2.get("instagram_business_account") or {}).get("id")
                if linked2:
                    # Guardar el page token permanente
                    try:
                        conn.execute(
                            "INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                            ("instagram_token", pt)
                        )
                        conn.execute(
                            "INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                            ("instagram_user_id", linked2)
                        )
                        conn.commit()
                    except Exception:
                        pass
                    return pt, linked2

    # Fallback: usar lo que hay almacenado
    return token, stored_uid

def _auth():
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in MARKETING_USERS:
        return None, jsonify({"error": "Sin acceso al módulo Marketing"}), 403
    return u, None, None

def _fmt(row):
    return dict(row) if row else None

def _fmt_many(rows):
    return [dict(r) for r in rows]

def _cfg(conn, clave, default=None):
    """Lee configuración de animus_config (tabla compartida con Centro de Mando)."""
    try:
        row = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else default
    except Exception:
        return default

def _call_claude(conn, agente, datos):
    """Enriquece el resultado del agente con análisis IA usando Claude API."""
    api_key = _cfg(conn, "anthropic_api_key")
    if not api_key:
        return None
    PROMPTS = {
        "estacionalidad": "Eres el director comercial de ÁNIMUS Lab (skincare premium colombiano). Analiza el stock vs demanda proyectada para los próximos eventos del calendario cosmético. Identifica los SKUs en riesgo, calcula fechas límite de producción y da instrucciones concretas. Máximo 200 palabras, en español.",
        "oportunidad":    "Eres el director comercial de ÁNIMUS Lab. Analiza los SKUs con alto stock y baja rotación. Propón acciones de marketing específicas (descuentos, bundles, campañas) con fechas y porcentajes concretos. Máximo 200 palabras, en español.",
        "roi":            "Eres el CFO de ÁNIMUS Lab. Analiza el ROI de las campañas activas. Señala cuáles escalar, pausar o ajustar y por qué. Incluye recomendaciones de presupuesto. Máximo 200 palabras, en español.",
        "tendencias":     "Eres el analista de datos de ÁNIMUS Lab. Analiza las tendencias de ventas por SKU (ERP vs Shopify). Identifica los productos con mayor momentum y los que están cayendo. Da recomendaciones de producción y marketing. Máximo 200 palabras, en español.",
        "brief":          "Eres el director creativo de ÁNIMUS Lab. Basado en los SKUs top, genera briefs de contenido detallados: canal recomendado, formato, claim principal, tono y ángulo de diferenciación científica. Máximo 200 palabras, en español.",
        "pricing":        "Eres el director de pricing de ÁNIMUS Lab. Analiza qué SKUs tienen margen para descuento sin comprometer rentabilidad. Da recomendaciones de precios promocionales concretos con porcentajes. Máximo 200 palabras, en español.",
        "reorden":        "Eres el jefe de supply chain de ÁNIMUS Lab. Analiza los patrones de compra B2B y predice cuándo hará su próximo pedido cada cliente. Da fechas concretas y recomendaciones de seguimiento proactivo. Máximo 200 palabras, en español.",
        "canibal":        "Eres el director de marketing de ÁNIMUS Lab. Detecta conflictos entre campañas activas (mismo SKU, canal, fechas). Propón un calendario de campañas optimizado para maximizar el impacto sin canibalización. Máximo 200 palabras, en español.",
        "contenido_auto": "Eres el community manager de ÁNIMUS Lab (skincare científico premium para piel latina). Revisa los captions generados y da feedback sobre tono, claims científicos y potencial de conversión. Sugiere mejoras concretas. Máximo 200 palabras, en español.",
        "alerta_stock":   "Eres el director de operaciones de ÁNIMUS Lab. Analiza los SKUs con cobertura crítica cruzando ERP y Shopify. Da instrucciones específicas de producción urgente con cantidades y fechas. Máximo 200 palabras, en español.",
    }
    prompt = PROMPTS.get(agente, "Analiza estos datos de ÁNIMUS Lab y da recomendaciones accionables en español. Máximo 200 palabras.")
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt + "\n\nDatos del sistema:\n" + json.dumps(datos, ensure_ascii=False, default=str)[:3000]}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except Exception:
        return None

def _ig_check_refresh(conn):
    """Auto-renueva el token de IG si vence en < 10 dias.
    Funciona con long-lived User Tokens (60 dias) y Page Access Tokens que
    heredan la duracion del User Token. Llama a fb_exchange_token para
    extender automaticamente antes de que expire.
    Retorna dict con estado del token para incluir en la respuesta del dashboard.
    """
    from datetime import date as _date, timedelta as _td

    raw_token  = _cfg(conn, "instagram_token")
    app_id     = _cfg(conn, "meta_app_id")
    app_secret = _cfg(conn, "meta_app_secret")
    expiry_str = _cfg(conn, "instagram_token_expiry")  # e.g. "2026-06-20"

    today = _date.today()

    # Calcular dias restantes segun expiry guardado
    if expiry_str:
        try:
            expiry_date = _date.fromisoformat(expiry_str)
            days_left = (expiry_date - today).days
        except Exception:
            days_left = 0
    else:
        # Sin expiry registrado: asumir que hay que renovar (token inicial sin fecha)
        days_left = 0

    near_expiry = days_left < 10
    refreshed   = False

    # Intentar refresh si esta cerca de expirar y tenemos las credenciales de la app
    if near_expiry and raw_token and app_id and app_secret:
        try:
            exch_url = (
                f"https://graph.facebook.com/v19.0/oauth/access_token"
                f"?grant_type=fb_exchange_token"
                f"&client_id={app_id}&client_secret={app_secret}"
                f"&fb_exchange_token={raw_token}"
            )
            with urllib.request.urlopen(urllib.request.Request(exch_url), timeout=10) as r:
                data = json.loads(r.read())
            new_token  = data.get("access_token")
            expires_in = data.get("expires_in", 5184000)  # 60 dias default
            if new_token:
                new_expiry = (_date.today() + _td(seconds=int(expires_in))).isoformat()
                conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                             ("instagram_token", new_token))
                conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                             ("instagram_token_expiry", new_expiry))
                conn.commit()
                days_left  = int(expires_in) // 86400
                expiry_str = new_expiry
                refreshed  = True
        except Exception:
            pass  # Token expirado del todo — usuario debe ingresar nuevo token manual

    return {
        "expiry_date": expiry_str,
        "days_left":   days_left,
        "near_expiry": near_expiry and not refreshed,
        "refreshed":   refreshed,
        "expired":     days_left <= 0 and not refreshed and bool(expiry_str),
    }

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

        # ── Shopify: datos reales ────────────────────────────────────────────
        hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        hace7  = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        sh_30 = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos,
                   COUNT(DISTINCT email) as clientes
            FROM animus_shopify_orders WHERE creado_en >= ?
        """, (hace30,)).fetchone()

        sh_7 = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos
            FROM animus_shopify_orders WHERE creado_en >= ?
        """, (hace7,)).fetchone()

        sh_total = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos,
                   COUNT(DISTINCT email) as clientes
            FROM animus_shopify_orders
        """).fetchone()

        sh_ticket = round(sh_30["rev"] / sh_30["pedidos"], 0) if sh_30["pedidos"] > 0 else 0

        # Clientes nuevos vs recurrentes (30d)
        sh_nuevos = c.execute("""
            SELECT COUNT(DISTINCT o.email) as n FROM animus_shopify_orders o
            WHERE o.creado_en >= ?
            AND (SELECT COUNT(*) FROM animus_shopify_orders o2
                 WHERE o2.email=o.email AND o2.creado_en < ?) = 0
        """, (hace30, hace30)).fetchone()["n"]

        # Top SKUs por revenue Shopify (30d)
        sh_top_skus_raw = _fmt_many(c.execute("""
            SELECT sku_items, SUM(total) as rev, SUM(unidades_total) as uds
            FROM animus_shopify_orders WHERE creado_en >= ?
            GROUP BY sku_items ORDER BY rev DESC LIMIT 20
        """, (hace30,)).fetchall())

        # Agregar revenue ERP (liberaciones)
        erp_rev = {}
        for row in c.execute("""
            SELECT sku, SUM(unidades) as uds FROM liberaciones
            WHERE creado_en >= ? AND sku IS NOT NULL GROUP BY sku
        """, (hace30,)).fetchall():
            precio = c.execute("SELECT MAX(precio_base) as p FROM stock_pt WHERE sku=?", (row["sku"],)).fetchone()
            p = precio["p"] if precio and precio["p"] else 0
            erp_rev[row["sku"]] = {"uds": row["uds"], "rev": round(row["uds"] * p, 0)}

        top_skus_combined = sorted(erp_rev.items(), key=lambda x: -x[1]["rev"])[:6]
        sh_top_skus = [{"sku": k, "total": v["rev"], "uds": v["uds"]} for k, v in top_skus_combined]

        # Ventas mensuales Shopify (últimos 6 meses)
        sh_mensual = _fmt_many(c.execute("""
            SELECT strftime('%Y-%m', creado_en) as mes,
                   COALESCE(SUM(total),0) as total,
                   COUNT(*) as pedidos
            FROM animus_shopify_orders
            GROUP BY mes ORDER BY mes DESC LIMIT 6
        """).fetchall())
        sh_mensual.reverse()

        # Liberaciones mensuales ERP (últimos 6 meses)
        erp_mensual = _fmt_many(c.execute("""
            SELECT strftime('%Y-%m', creado_en) as mes,
                   COALESCE(SUM(unidades),0) as uds
            FROM liberaciones WHERE sku IS NOT NULL
            GROUP BY mes ORDER BY mes DESC LIMIT 6
        """).fetchall())
        erp_mensual.reverse()

        # Top ciudades
        sh_ciudades = _fmt_many(c.execute("""
            SELECT ciudad, COUNT(*) as pedidos, COALESCE(SUM(total),0) as total
            FROM animus_shopify_orders WHERE ciudad != ''
            GROUP BY ciudad ORDER BY total DESC LIMIT 5
        """).fetchall())

        # GHL: contactos y pipeline
        ghl_total = c.execute("SELECT COUNT(*) as n FROM animus_ghl_contacts").fetchone()["n"]
        ghl_nuevos = c.execute("""
            SELECT COUNT(*) as n FROM animus_ghl_contacts WHERE creado_en >= ?
        """, (hace30,)).fetchone()["n"]

        # Instagram: metricas desde posts sincronizados
        ig_total_posts  = c.execute("SELECT COUNT(*) as n FROM animus_instagram_posts").fetchone()["n"]
        ig_posts_30d    = c.execute("SELECT COUNT(*) as n FROM animus_instagram_posts WHERE publicado_en >= ?", (hace30,)).fetchone()["n"]
        ig_likes_30d    = c.execute("SELECT COALESCE(SUM(likes),0) as s FROM animus_instagram_posts WHERE publicado_en >= ?", (hace30,)).fetchone()["s"]
        ig_comments_30d = c.execute("SELECT COALESCE(SUM(comentarios),0) as s FROM animus_instagram_posts WHERE publicado_en >= ?", (hace30,)).fetchone()["s"]
        ig_avg_likes    = round(ig_likes_30d / ig_posts_30d, 1) if ig_posts_30d > 0 else 0
        ig_top_posts    = _fmt_many(c.execute("""
            SELECT instagram_id, tipo, descripcion, likes, comentarios, url_permalink, publicado_en
            FROM animus_instagram_posts
            ORDER BY (likes + comentarios*3) DESC LIMIT 5
        """).fetchall())
        ig_configured   = bool(_cfg(conn, "instagram_token") and _cfg(conn, "instagram_user_id"))
        # Auto-refresh token si vence en < 10 dias (silencioso)
        ig_token_status = _ig_check_refresh(conn) if ig_configured else {"expiry_date": None, "days_left": 0, "near_expiry": False, "refreshed": False, "expired": False}

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
            "shopify": {
                "revenue_30d": round(sh_30["rev"], 0),
                "revenue_7d":  round(sh_7["rev"], 0),
                "revenue_total": round(sh_total["rev"], 0),
                "pedidos_30d": sh_30["pedidos"],
                "pedidos_7d": sh_7["pedidos"],
                "pedidos_total": sh_total["pedidos"],
                "clientes_30d": sh_30["clientes"],
                "clientes_total": sh_total["clientes"],
                "clientes_nuevos_30d": sh_nuevos,
                "clientes_recurrentes_30d": sh_30["clientes"] - sh_nuevos,
                "ticket_promedio": sh_ticket,
                "mensual": sh_mensual,
                "top_skus": sh_top_skus,
                "ciudades": sh_ciudades,
            },
            "ghl": {
                "contactos_total": ghl_total,
                "contactos_nuevos_30d": ghl_nuevos,
            },
            "instagram": {
                "configurado": ig_configured,
                "total_posts": ig_total_posts,
                "posts_30d": ig_posts_30d,
                "likes_30d": ig_likes_30d,
                "comentarios_30d": ig_comments_30d,
                "avg_likes": ig_avg_likes,
                "top_posts": ig_top_posts,
                "token_expiry_date":  ig_token_status["expiry_date"],
                "token_days_left":    ig_token_status["days_left"],
                "token_near_expiry":  ig_token_status["near_expiry"],
                "token_refreshed":    ig_token_status["refreshed"],
                "token_expired":      ig_token_status["expired"],
            },
            "top_influencer": _fmt(top_inf),
            "campanas_activas": campanas_activas,
            "contenido_reciente": contenido_reciente,
            "tendencias": tendencias,
            "por_canal": por_canal,
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

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

        # ── Shopify baseline KPIs (shown when campaigns are empty) ────────────
        hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        hace60 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        hoy    = datetime.now().strftime("%Y-%m-%d")
        mes_ini_sh = datetime.now().replace(day=1).strftime("%Y-%m-%d")

        # Cobertura real de datos
        cobertura = c.execute(
            "SELECT MIN(creado_en) as desde, MAX(creado_en) as hasta, COUNT(*) as total FROM animus_shopify_orders"
        ).fetchone()
        datos_desde = cobertura["desde"] if cobertura["desde"] else None
        datos_hasta = cobertura["hasta"] if cobertura["hasta"] else None

        # Días reales de cobertura
        if datos_desde:
            try:
                d_desde = datetime.strptime(datos_desde, "%Y-%m-%d")
                cobertura_dias = max((datetime.now() - d_desde).days + 1, 1)
            except Exception:
                cobertura_dias = 30
        else:
            cobertura_dias = 0

        # Revenue usando ventana real de datos (no asumir 30d si hay menos)
        sh_30 = c.execute(
            "SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos FROM animus_shopify_orders WHERE creado_en >= ?",
            (hace30,)
        ).fetchone()
        sh_60 = c.execute(
            "SELECT COALESCE(SUM(total),0) as rev FROM animus_shopify_orders WHERE creado_en BETWEEN ? AND ?",
            (hace60, hace30)
        ).fetchone()
        # Revenue mes calendario actual
        sh_mes = c.execute(
            "SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos FROM animus_shopify_orders WHERE creado_en >= ?",
            (mes_ini_sh,)
        ).fetchone()

        sh_rev_30 = round(sh_30["rev"], 0)
        sh_rev_prev = round(sh_60["rev"], 0)
        sh_growth = round((sh_rev_30 - sh_rev_prev) / sh_rev_prev * 100, 1) if sh_rev_prev > 0 else (100.0 if sh_rev_30 > 0 else 0.0)

        return jsonify({
            "campanas": campanas,
            "influencers": influencers,
            "por_canal": por_canal,
            "shopify_kpis": {
                "revenue_30d":      sh_rev_30,
                "revenue_prev_30d": sh_rev_prev,
                "crecimiento_pct":  sh_growth,
                "pedidos_30d":      sh_30["pedidos"],
                "revenue_mes":      round(sh_mes["rev"], 0),
                "pedidos_mes":      sh_mes["pedidos"],
                "datos_desde":      datos_desde,
                "datos_hasta":      datos_hasta,
                "cobertura_dias":   cobertura_dias,
                "cobertura_parcial": cobertura_dias < 25,  # aviso si menos de 25 días
            }
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

@bp.route("/api/marketing/analytics/tendencias")
def mkt_analytics_tendencias():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        meses = int(request.args.get("meses", 6))
        hoy   = datetime.now().strftime("%Y-%m-%d")
        hace90  = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        hace180 = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        desde   = (datetime.now() - timedelta(days=meses * 30)).strftime("%Y-%m-%d")

        # ── Parse sku_items JSON from Shopify orders ─────────────────────────
        def _parse_orders_skus(rows):
            """Return {sku: {rev, qty}} from animus_shopify_orders rows."""
            result = {}
            for row in rows:
                try:
                    items = json.loads(row["sku_items"] or "[]")
                    if not items:
                        continue
                    rev_per = row["total"] / len(items)
                    for item in items:
                        sku = (item.get("sku") or "").strip()
                        if not sku or sku in ("", "null", "None"):
                            continue
                        if sku not in result:
                            result[sku] = {"rev": 0.0, "qty": 0}
                        result[sku]["rev"] += rev_per
                        result[sku]["qty"] += int(item.get("qty") or 0)
                except Exception:
                    pass
            return result

        rows_rec = c.execute(
            "SELECT sku_items, total, unidades_total FROM animus_shopify_orders WHERE creado_en BETWEEN ? AND ?",
            (hace90, hoy)
        ).fetchall()
        rows_ant = c.execute(
            "SELECT sku_items, total, unidades_total FROM animus_shopify_orders WHERE creado_en BETWEEN ? AND ?",
            (hace180, hace90)
        ).fetchall()

        reciente_sh = _parse_orders_skus(rows_rec)
        anterior_sh = _parse_orders_skus(rows_ant)

        # ── Also include ERP liberaciones (if any) ───────────────────────────
        reciente_erp, anterior_erp = {}, {}
        try:
            for row in c.execute(
                "SELECT sku, SUM(unidades) as total FROM liberaciones WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL GROUP BY sku",
                (hace90, hoy)
            ).fetchall():
                reciente_erp[row["sku"]] = row["total"]
            for row in c.execute(
                "SELECT sku, SUM(unidades) as total FROM liberaciones WHERE creado_en BETWEEN ? AND ? AND sku IS NOT NULL GROUP BY sku",
                (hace180, hace90)
            ).fetchall():
                anterior_erp[row["sku"]] = row["total"]
        except Exception:
            pass

        # ── Merge sources, build crecimiento list ────────────────────────────
        todos_sku = set(
            list(reciente_sh.keys()) + list(anterior_sh.keys()) +
            list(reciente_erp.keys()) + list(anterior_erp.keys())
        )
        crecimiento = []
        for sku in todos_sku:
            rec_rev = reciente_sh.get(sku, {}).get("rev", 0) + reciente_erp.get(sku, 0)
            ant_rev = anterior_sh.get(sku, {}).get("rev", 0) + anterior_erp.get(sku, 0)
            rec_qty = reciente_sh.get(sku, {}).get("qty", 0) + reciente_erp.get(sku, 0)
            ant_qty = anterior_sh.get(sku, {}).get("qty", 0) + anterior_erp.get(sku, 0)
            if ant_rev > 0:
                pct = round((rec_rev - ant_rev) / ant_rev * 100, 1)
            elif rec_rev > 0:
                pct = 100.0
            else:
                pct = 0.0
            crecimiento.append({
                "sku": sku,
                "reciente_90d": round(rec_rev, 0),
                "anterior_90d": round(ant_rev, 0),
                "crecimiento_pct": pct
            })
        crecimiento.sort(key=lambda x: x["crecimiento_pct"], reverse=True)

        # ── Ventas mensuales por SKU (period window for sparklines) ──────────
        rows_periodo = c.execute("""
            SELECT sku_items, total, strftime('%Y-%m', creado_en) as mes
            FROM animus_shopify_orders WHERE creado_en >= ?
        """, (desde,)).fetchall()
        por_sku_mes_map = {}
        for row in rows_periodo:
            try:
                items = json.loads(row["sku_items"] or "[]")
                if not items:
                    continue
                rev_per = row["total"] / len(items)
                for item in items:
                    sku = (item.get("sku") or "").strip()
                    if not sku:
                        continue
                    key = (sku, row["mes"])
                    por_sku_mes_map[key] = por_sku_mes_map.get(key, 0.0) + rev_per
            except Exception:
                pass
        por_sku_mes = [{"sku": k[0], "mes": k[1], "revenue": round(v, 0)} for k, v in sorted(por_sku_mes_map.items())]

        return jsonify({
            "por_sku_mes": por_sku_mes,
            "crecimiento": crecimiento[:20],
            "periodo_meses": meses,
            "fuente": "shopify" if rows_rec else "sin_datos"
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── CONEXIONES / SYNC ─────────────────────────────────────────────────────────

@bp.route("/api/marketing/ghl-debug")
def ghl_debug():
    """Diagnóstico: key en BD + 3 variantes de llamada a GHL."""
    import urllib.error as _ue
    with get_db() as conn:
        key = _cfg(conn, "ghl_api_key") or ""
        loc = _cfg(conn, "ghl_location_id") or ""
    results = {}
    tests = [
        ("v2_con_loc", f"https://services.leadconnectorhq.com/contacts/?locationId={loc}&limit=1"),
        ("v2_sin_loc", "https://services.leadconnectorhq.com/contacts/?limit=1"),
        ("v1",         "https://rest.gohighlevel.com/v1/contacts/?limit=1"),
    ]
    for label, url in tests:
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "Version": "2021-07-28",
                "User-Agent": "GHL-Integration/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                results[label] = {"status": r.status, "preview": r.read().decode()[:200]}
        except _ue.HTTPError as e:
            results[label] = {"status": e.code, "body": e.read().decode("utf-8", errors="replace")[:300]}
        except Exception as ex:
            results[label] = {"error": str(ex)}
    return jsonify({"key_preview": key[:12]+"..." if key else "VACÍA", "loc_id": loc, "tests": results})

@bp.route("/api/marketing/connections")
def mkt_connections():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        connected = {
            "shopify":   bool(_cfg(conn, "shopify_token") and _cfg(conn, "shopify_shop")),
            "ghl":       bool(_cfg(conn, "ghl_api_key")),
            "instagram": bool(_cfg(conn, "instagram_token") and _cfg(conn, "instagram_user_id")),
        }
        last_sync = {}
        tables = {"shopify": "animus_shopify_orders", "ghl": "animus_ghl_contacts", "instagram": "animus_instagram_posts"}
        for plat, tbl in tables.items():
            try:
                row = conn.execute(f"SELECT MAX(synced_at) as ts FROM {tbl}").fetchone()
                last_sync[plat] = row["ts"] if row else None
            except Exception:
                last_sync[plat] = None
        return jsonify({"connected": connected, "last_sync": last_sync})
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

@bp.route("/api/marketing/sync/<platform>", methods=["POST"])
def mkt_sync(platform):
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        if platform == "shopify":
            token = _cfg(conn, "shopify_token")
            shop  = _cfg(conn, "shopify_shop")
            if not token or not shop:
                return jsonify({"error": "Shopify no configurado. Falta shopify_token o shopify_shop."}), 400

            # Sync incremental: sólo órdenes posteriores al último registro
            # full=1 → sync histórico completo (ignora incremental)
            full_sync = request.args.get("full") == "1"
            last = conn.execute(
                "SELECT MAX(creado_en) as m FROM animus_shopify_orders"
            ).fetchone()["m"]
            since = ("" if full_sync else f"&created_at_min={last}T00:00:00Z") if last else ""

            # Paginación cursor-based (Link header rel=next)
            url = f"https://{shop}/admin/api/2024-01/orders.json?status=any&limit=250{since}"
            synced = 0
            while url:
                req = urllib.request.Request(url, headers={
                    "X-Shopify-Access-Token": token,
                    "Content-Type": "application/json",
                })
                try:
                    with urllib.request.urlopen(req, timeout=20) as r:
                        orders = json.loads(r.read()).get("orders", [])
                        # Extraer página siguiente del header Link
                        link_hdr = r.headers.get("Link", "")
                        next_url = None
                        for part in link_hdr.split(","):
                            if 'rel="next"' in part:
                                next_url = part.strip().split(";")[0].strip().strip("<>")
                                break
                        url = next_url
                except urllib.error.HTTPError as he:
                    body = he.read().decode("utf-8", errors="replace")[:400]
                    return jsonify({"error": f"Shopify HTTP {he.code}", "detalle": body}), 400

                for o in orders:
                    line_items = o.get("line_items", [])
                    items_sku  = json.dumps([
                        {"sku": li.get("sku") or li.get("name",""), "qty": li.get("quantity",0)}
                        for li in line_items
                    ])
                    total_uds = sum(li.get("quantity", 0) for li in line_items)
                    addr = o.get("shipping_address") or o.get("billing_address") or {}
                    ciudad = addr.get("city") or addr.get("province") or ""
                    conn.execute("""INSERT OR REPLACE INTO animus_shopify_orders
                        (shopify_id,nombre,email,total,moneda,estado,estado_pago,
                         sku_items,unidades_total,ciudad,pais,creado_en,synced_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                        (str(o["id"]), o.get("name",""), o.get("email",""),
                         float(o.get("total_price") or 0),
                         o.get("currency","COP"),
                         o.get("fulfillment_status") or "unfulfilled",
                         o.get("financial_status",""),
                         items_sku, total_uds, ciudad,
                         addr.get("country_code","CO"),
                         (o.get("created_at") or "")[:10]))
                    synced += 1
                if not orders:
                    break

            conn.commit()
            return jsonify({"ok": True, "synced": synced, "platform": "shopify"})

        elif platform == "ghl":
            api_key = _cfg(conn, "ghl_api_key")
            loc_id  = _cfg(conn, "ghl_location_id")
            if not api_key or not loc_id:
                return jsonify({"error": "GHL no configurado (falta api_key o location_id)."}), 400
            # GHL v2 API — paginación por cursor (startAfter/startAfterId)
            synced = 0
            start_after = None
            start_after_id = None
            ghl_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28",
                "Accept": "application/json",
                "User-Agent": "GHL-Integration/1.0",
            }
            while True:
                params = f"locationId={loc_id}&limit=100"
                if start_after:
                    params += f"&startAfter={start_after}&startAfterId={start_after_id}"
                url = f"https://services.leadconnectorhq.com/contacts/?{params}"
                req = urllib.request.Request(url, headers=ghl_headers)
                try:
                    with urllib.request.urlopen(req, timeout=20) as r:
                        payload = json.loads(r.read())
                except urllib.error.HTTPError as http_err:
                    body = http_err.read().decode("utf-8", errors="replace")[:500]
                    return jsonify({"error": f"GHL HTTP {http_err.code}", "detalle": body}), 400
                contacts = payload.get("contacts", [])
                if not contacts:
                    break
                for ct in contacts:
                    tags = json.dumps(ct.get("tags", []))
                    fecha = (ct.get("dateAdded") or ct.get("createdAt") or "")[:10]
                    conn.execute("""INSERT OR REPLACE INTO animus_ghl_contacts
                        (ghl_id,nombre,email,telefono,etiquetas,fuente,creado_en,synced_at)
                        VALUES(?,?,?,?,?,?,?,datetime('now'))""",
                        (ct.get("id",""),
                         f"{ct.get('firstName','')} {ct.get('lastName','')}".strip(),
                         ct.get("email",""), ct.get("phone",""),
                         tags, ct.get("source",""), fecha))
                    synced += 1
                # Cursor para siguiente página
                meta = payload.get("meta", {})
                start_after    = meta.get("startAfter")
                start_after_id = meta.get("startAfterId")
                if not start_after or len(contacts) < 100:
                    break
            conn.commit()
            return jsonify({"ok": True, "synced": synced, "platform": "ghl"})

        elif platform == "instagram":
            # _ig_resolve_token autodescubre el Page Access Token correcto
            # y el IG user ID real desde /me/accounts → instagram_business_account.
            # Los Page Access Tokens son permanentes (no necesitan refresh).
            token, user_id = _ig_resolve_token(conn)
            if not token or not user_id:
                return jsonify({"error": "Instagram no configurado o token inválido."}), 400

            fields = "id,media_type,caption,media_url,permalink,like_count,comments_count,timestamp"
            url = f"https://graph.facebook.com/v21.0/{user_id}/media?fields={fields}&access_token={token}&limit=50"
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    posts = json.loads(r.read()).get("data", [])
            except urllib.error.HTTPError as he:
                body = {}
                try:
                    body = json.loads(he.read().decode())
                except Exception:
                    pass
                return jsonify({"error": f"Media API error {he.code}", "detalle": json.dumps(body)}), 502
            synced = 0
            for p in posts:
                conn.execute("""INSERT OR REPLACE INTO animus_instagram_posts
                    (instagram_id,tipo,descripcion,url_media,url_permalink,likes,comentarios,publicado_en,synced_at)
                    VALUES(?,?,?,?,?,?,?,?,datetime('now'))""",
                    (p.get("id",""), p.get("media_type",""),
                     (p.get("caption","") or "")[:500],
                     p.get("media_url",""), p.get("permalink",""),
                     p.get("like_count",0), p.get("comments_count",0),
                     p.get("timestamp","")[:10] if p.get("timestamp") else ""))
                synced += 1
            conn.commit()
            return jsonify({"ok": True, "synced": synced, "platform": "instagram"})
        else:
            return jsonify({"error": "Plataforma desconocida"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INSTAGRAM TOKEN REFRESH ──────────────────────────────────────────────────
@bp.route("/api/marketing/ig-refresh", methods=["POST"])
def mkt_ig_refresh():
    """Intercambia el token de Instagram corto por uno de 60 dias.
    Requiere META_APP_ID y META_APP_SECRET en animus_config (o env vars).
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        short_token = _cfg(conn, "instagram_token")
        app_id      = _cfg(conn, "meta_app_id")
        app_secret  = _cfg(conn, "meta_app_secret")
        if not short_token:
            return jsonify({"error": "No hay instagram_token configurado"}), 400
        if not app_id or not app_secret:
            return jsonify({"error": "Falta meta_app_id o meta_app_secret en config"}), 400
        url = (
            f"https://graph.facebook.com/v19.0/oauth/access_token"
            f"?grant_type=fb_exchange_token"
            f"&client_id={app_id}"
            f"&client_secret={app_secret}"
            f"&fb_exchange_token={short_token}"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        long_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)
        if not long_token:
            return jsonify({"error": "Facebook no devolvio token", "detail": data}), 502
        from datetime import date as _d2, timedelta as _td2
        conn.execute(
            "INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
            ("instagram_token", long_token)
        )
        new_expiry = (_d2.today() + _td2(seconds=int(expires_in))).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
            ("instagram_token_expiry", new_expiry)
        )
        conn.commit()
        days = round(expires_in / 86400)
        return jsonify({"ok": True, "expires_days": days, "expiry_date": new_expiry, "msg": f"Token renovado — valido {days} dias hasta {new_expiry}"})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return jsonify({"error": f"HTTP {e.code}", "detalle": body}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INSTAGRAM TOKEN UPDATE (desde el dashboard) ──────────────────────────────
@bp.route("/api/marketing/ig-update-token", methods=["POST"])
def mkt_ig_update_token():
    """Cadena completa:
    1. Recibe token corto del Graph API Explorer
    2. Lo intercambia por token largo (60 dias)
    3. Llama /me/accounts para obtener Page Access Token permanente
    4. Verifica cual pagina tiene el IG account vinculado
    5. Guarda ese Page Token — NO EXPIRA NUNCA
    """
    u, err, code = _auth()
    if err: return err, code
    data = request.get_json() or {}
    short_token = (data.get("token") or "").strip()
    if not short_token or not short_token.startswith("EAA"):
        return jsonify({"error": "Token invalido — debe comenzar con EAA"}), 400

    conn = _db()
    try:
        app_id     = _cfg(conn, "meta_app_id")
        app_secret = _cfg(conn, "meta_app_secret")
        ig_user_id = _cfg(conn, "instagram_user_id") or "17841445400789819"
        steps      = []

        # Paso 1: guardar token corto como fallback
        conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                     ("instagram_token", short_token))
        conn.commit()
        steps.append("token_corto_guardado")

        # Paso 2: exchange a token largo (60 dias)
        long_token = short_token
        if app_id and app_secret:
            try:
                exch_url = (
                    f"https://graph.facebook.com/v19.0/oauth/access_token"
                    f"?grant_type=fb_exchange_token"
                    f"&client_id={app_id}&client_secret={app_secret}"
                    f"&fb_exchange_token={short_token}"
                )
                r = urllib.request.urlopen(urllib.request.Request(exch_url), timeout=12)
                rd = json.loads(r.read())
                if rd.get("access_token"):
                    long_token = rd["access_token"]
                    conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                                 ("instagram_token", long_token))
                    conn.commit()
                    steps.append("exchange_60d_ok")
            except Exception as ex:
                steps.append(f"exchange_error:{ex}")

        # Paso 3: obtener Page Access Token permanente via /me/accounts
        permanent_token = None
        try:
            pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={long_token}"
            r2 = urllib.request.urlopen(urllib.request.Request(pages_url), timeout=12)
            pages_data = json.loads(r2.read())
            pages = pages_data.get("data", [])
            steps.append(f"pages_encontradas:{len(pages)}")

            # Paso 4: identificar cual pagina tiene el IG account vinculado
            for page in pages:
                page_id    = page.get("id")
                page_token = page.get("access_token")
                if not page_id or not page_token:
                    continue
                try:
                    ig_url = (f"https://graph.facebook.com/v19.0/{page_id}"
                              f"?fields=instagram_business_account&access_token={page_token}")
                    r3 = urllib.request.urlopen(urllib.request.Request(ig_url), timeout=10)
                    ig_data = json.loads(r3.read())
                    linked_ig = ig_data.get("instagram_business_account", {}).get("id")
                    if linked_ig == ig_user_id:
                        permanent_token = page_token
                        conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                                     ("instagram_token", page_token))
                        conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                                     ("instagram_page_id", page_id))
                        conn.commit()
                        steps.append(f"page_token_permanente_ok:pagina={page.get('name')}")
                        break
                except Exception:
                    continue
        except Exception as ex:
            steps.append(f"pages_error:{ex}")

        token_type = "permanente" if permanent_token else ("60_dias" if "exchange_60d_ok" in steps else "corto")
        # Guardar fecha de vencimiento (60 dias desde hoy — aplica a todos los tipos)
        from datetime import date as _d3, timedelta as _td3
        expiry_60 = (_d3.today() + _td3(days=60)).isoformat()
        conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)",
                     ("instagram_token_expiry", expiry_60))
        conn.commit()
        steps.append(f"expiry_guardado:{expiry_60}")
        return jsonify({
            "ok": True,
            "token_type": token_type,
            "steps": steps,
            "msg": {
                "permanente": "✅ Token permanente de Pagina guardado — nunca expira",
                "60_dias":    "✅ Token de 60 dias guardado (se renueva solo al sincronizar)",
                "corto":      "⚠️ Token corto guardado — expira en ~2h",
            }[token_type]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INSTAGRAM DEBUG ───────────────────────────────────────────────────────────
@bp.route("/api/marketing/ig-debug", methods=["GET"])
def mkt_ig_debug():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        raw_token  = _cfg(conn, "instagram_token")
        stored_uid = _cfg(conn, "instagram_user_id")
        app_id     = _cfg(conn, "meta_app_id")
        result = {
            "stored_user_id": stored_uid,
            "app_id_ok": bool(app_id),
            "raw_token_present": bool(raw_token),
        }

        def _fetch_debug(url):
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    return json.loads(r.read()), None
            except urllib.error.HTTPError as e:
                try:
                    return None, json.loads(e.read().decode())
                except Exception:
                    return None, {"http_status": e.code}
            except Exception as ex:
                return None, {"exception": str(ex)}

        if raw_token:
            # Step 1: /me con el token almacenado
            me, me_err = _fetch_debug(
                f"https://graph.facebook.com/v19.0/me?access_token={raw_token}")
            result["step1_me"] = me or me_err

            # Step 2: intentar leer IG account del /me id — capturar error también
            if me:
                me_id = me.get("id", "")
                ig_from_me, ig_from_me_err = _fetch_debug(
                    f"https://graph.facebook.com/v19.0/{me_id}"
                    f"?fields=instagram_business_account,name,link&access_token={raw_token}")
                result["step2_ig_from_me"] = ig_from_me
                if ig_from_me_err:
                    result["step2_error"] = ig_from_me_err

                # Step 2b: probar con campos básicos solamente (permiso básico de página)
                page_basic, page_basic_err = _fetch_debug(
                    f"https://graph.facebook.com/v19.0/{me_id}"
                    f"?fields=name,id,category&access_token={raw_token}")
                result["step2b_page_basic"] = page_basic
                if page_basic_err:
                    result["step2b_error"] = page_basic_err

            # Step 3: /me/accounts (solo funciona con UAT)
            accounts, accounts_err = _fetch_debug(
                f"https://graph.facebook.com/v19.0/me/accounts"
                f"?access_token={raw_token}&limit=10")
            result["step3_accounts"] = accounts
            if accounts_err:
                result["step3_error"] = accounts_err

            # Step 4: por cada página, buscar instagram_business_account
            if accounts:
                pages_ig = []
                for page in accounts.get("data", []):
                    pt = page.get("access_token")
                    pid = page.get("id")
                    pname = page.get("name")
                    if pt and pid:
                        ig2, _ = _fetch_debug(
                            f"https://graph.facebook.com/v19.0/{pid}"
                            f"?fields=instagram_business_account&access_token={pt}")
                        linked = (ig2.get("instagram_business_account") or {}).get("id") if ig2 else None
                        pages_ig.append({
                            "page_id": pid, "page_name": pname,
                            "ig_account_id": linked
                        })
                result["step4_pages_ig"] = pages_ig

        # Step 5: resolución automática + test de media
        resolved_token, resolved_uid = _ig_resolve_token(conn)
        result["step5_resolved"] = {
            "token_resolved": bool(resolved_token),
            "ig_user_id": resolved_uid,
        }
        if resolved_token and resolved_uid:
            fields = "id,media_type,caption,like_count,timestamp"
            media, media_err = _fetch_debug(
                f"https://graph.facebook.com/v19.0/{resolved_uid}/media"
                f"?fields={fields}&access_token={resolved_token}&limit=3")
            result["step5_media"] = media or media_err

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── AGENTES IA (10 agentes ÁNIMUS con Claude) ─────────────────────────────────

AGENTES_DISPONIBLES = {
    "estacionalidad", "oportunidad", "roi", "tendencias",
    "brief", "pricing", "reorden", "canibal", "contenido_auto", "alerta_stock"
}

@bp.route("/api/marketing/agentes/<agente>", methods=["POST"])
def mkt_ejecutar_agente(agente):
    u, err, code = _auth()
    if err:
        return err, code
    if agente not in AGENTES_DISPONIBLES:
        return jsonify({"error": f"Agente desconocido. Válidos: {list(AGENTES_DISPONIBLES)}"}), 400

    conn = _db()
    c = conn.cursor()
    try:
        hoy    = datetime.now()
        hace30 = (hoy - timedelta(days=30)).strftime("%Y-%m-%d")
        hace90 = (hoy - timedelta(days=90)).strftime("%Y-%m-%d")
        resultado = {}

        # ── Agente 1: Estacionalidad ──────────────────────────────────────────
        if agente == "estacionalidad":
            alertas = []
            for ev in CALENDARIO_COSMETICO:
                dias = (datetime.strptime(ev["fecha"], "%Y-%m-%d") - hoy).days
                if dias < 0 or dias > 120: continue
                campanas = c.execute("""
                    SELECT nombre, sku_objetivo, objetivo_unidades, fecha_inicio
                    FROM marketing_campanas
                    WHERE fecha_inicio <= ? AND estado IN ('Planificada','Activa')
                    ORDER BY fecha_inicio
                """, (ev["fecha"],)).fetchall()
                skus_revisados = set()
                for cmp in campanas:
                    sku = cmp["sku_objetivo"]
                    if not sku or sku in skus_revisados: continue
                    skus_revisados.add(sku)
                    stock = c.execute("SELECT COALESCE(SUM(unidades_disponible),0) as s FROM stock_pt WHERE sku=? AND estado='Disponible'", (sku,)).fetchone()["s"]
                    lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                    rotacion = lib_90 / 3.0
                    demanda_ev = round(rotacion * ev["multiplicador"])
                    deficit = max(0, demanda_ev - stock)
                    semanas_prod = max(3, round(deficit / max(rotacion / 4.0, 1))) if deficit > 0 else 0
                    deadline_prod = (datetime.strptime(ev["fecha"], "%Y-%m-%d") - timedelta(weeks=semanas_prod)).strftime("%Y-%m-%d") if deficit > 0 else None
                    estado = "ok" if deficit == 0 else ("advertencia" if deficit < demanda_ev * 0.3 else "critico")
                    alertas.append({"evento": ev["evento"], "fecha_evento": ev["fecha"],
                        "color": ev["color"], "dias_restantes": dias, "sku": sku,
                        "campana": cmp["nombre"], "stock_actual": stock,
                        "demanda_proyectada": demanda_ev, "deficit": deficit,
                        "deadline_produccion": deadline_prod, "semanas_para_producir": semanas_prod,
                        "estado": estado, "multiplicador": ev["multiplicador"]})
                if not campanas:
                    top_skus = c.execute("SELECT sku, SUM(unidades_disponible) as stock FROM stock_pt WHERE estado='Disponible' GROUP BY sku ORDER BY stock DESC LIMIT 3").fetchall()
                    for s in top_skus:
                        sku = s["sku"]
                        if sku in skus_revisados: continue
                        skus_revisados.add(sku)
                        lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                        rotacion = lib_90 / 3.0
                        demanda_ev = round(rotacion * ev["multiplicador"])
                        deficit = max(0, demanda_ev - s["stock"])
                        alertas.append({"evento": ev["evento"], "fecha_evento": ev["fecha"],
                            "color": ev["color"], "dias_restantes": dias, "sku": sku,
                            "campana": None, "stock_actual": s["stock"],
                            "demanda_proyectada": demanda_ev, "deficit": deficit,
                            "deadline_produccion": None, "semanas_para_producir": 0,
                            "estado": "ok" if deficit == 0 else "advertencia",
                            "multiplicador": ev["multiplicador"]})
            alertas.sort(key=lambda x: (x["estado"] == "ok", x["dias_restantes"]))
            criticos = [a for a in alertas if a["estado"] == "critico"]
            resultado = {"titulo": "Análisis de Estacionalidad", "total_alertas": len(alertas),
                "criticos": len(criticos), "alertas": alertas[:20],
                "resumen": f"{len(criticos)} SKUs en estado crítico para eventos próximos."}

        # ── Agente 2: Oportunidad ─────────────────────────────────────────────
        elif agente == "oportunidad":
            stock_rows = c.execute("""
                SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio
                FROM stock_pt WHERE estado='Disponible' GROUP BY sku ORDER BY stock DESC LIMIT 15
            """).fetchall()
            recos = []
            for row in stock_rows:
                sku, stock, precio = row["sku"], row["stock"], row["precio"] or 0
                lib_30 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace30)).fetchone()["t"]
                lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                rotacion = lib_90 / 3.0
                meses_cob = round(stock / rotacion, 1) if rotacion > 0 else 99
                shopify_30 = c.execute("SELECT COALESCE(SUM(unidades_total),0) as t FROM animus_shopify_orders WHERE sku_items LIKE ? AND creado_en>=?", (f'%{sku}%', hace30)).fetchone()["t"]
                score = 0; razones = []
                if meses_cob > 3: score += 1; razones.append(f"{meses_cob} meses de inventario")
                if rotacion < 10 and stock > 50: score += 1; razones.append("baja rotación")
                if shopify_30 == 0 and stock > 20: score += 1; razones.append("sin ventas Shopify en 30d")
                if score > 0:
                    recos.append({"sku": sku, "stock": stock, "precio": precio,
                        "rotacion_mes": round(rotacion,1), "lib_30d": lib_30,
                        "meses_cobertura": meses_cob, "shopify_30d": shopify_30,
                        "score": score, "razones": razones,
                        "accion": f"Campaña {'urgente' if score>=2 else 'recomendada'} para {sku}: {stock} uds. Canal: {'Shopify + Influencer' if shopify_30==0 else 'Influencer + Promo'}."})
            recos.sort(key=lambda x: -x["score"])
            resultado = {"titulo": "SKUs con Oportunidad de Campaña", "recomendaciones": recos[:10], "total": len(recos)}

        # ── Agente 3: ROI ──────────────────────────────────────────────────────
        elif agente == "roi":
            campanas = c.execute("""
                SELECT id, nombre, canal, tipo, presupuesto, presupuesto_gastado,
                       resultado_ventas, resultado_unidades, fecha_inicio, fecha_fin
                FROM marketing_campanas WHERE presupuesto_gastado > 0
            """).fetchall()
            analisis = []
            for cp in campanas:
                gastado = cp["presupuesto_gastado"] or 0
                ventas  = cp["resultado_ventas"] or 0
                roi = round((ventas - gastado) / gastado * 100, 1) if gastado > 0 else 0
                analisis.append({**dict(cp), "roi_pct": roi,
                    "estado_roi": "excelente" if roi >= 200 else ("bueno" if roi >= 50 else ("neutro" if roi >= 0 else "negativo"))})
            analisis.sort(key=lambda x: -x["roi_pct"])
            shopify_rev = c.execute("SELECT COALESCE(SUM(total),0) as t FROM animus_shopify_orders WHERE creado_en>=?", (hace30,)).fetchone()["t"]
            resultado = {"titulo": "Análisis de ROI por Campaña", "campanas": analisis, "shopify_revenue_30d": shopify_rev}

        # ── Agente 4: Tendencias ───────────────────────────────────────────────
        elif agente == "tendencias":
            hace180 = (hoy - timedelta(days=180)).strftime("%Y-%m-%d")
            skus = c.execute("SELECT DISTINCT sku FROM liberaciones WHERE creado_en>=?", (hace180,)).fetchall()
            tendencias = []
            for s in skus:
                sku = s["sku"]
                r = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                a = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=? AND creado_en<?", (sku, hace180, hace90)).fetchone()["t"]
                if a > 0:
                    cambio = round((r - a) / a * 100, 1)
                    tendencias.append({"sku": sku, "reciente": r, "anterior": a, "cambio_pct": cambio,
                        "tendencia": "alza" if cambio > 15 else ("baja" if cambio < -15 else "estable")})
            tendencias.sort(key=lambda x: -abs(x["cambio_pct"]))
            shopify_trend = _fmt_many(c.execute("""
                SELECT strftime('%Y-%m', creado_en) as mes, SUM(total) as ventas, COUNT(*) as pedidos
                FROM animus_shopify_orders GROUP BY mes ORDER BY mes DESC LIMIT 6
            """).fetchall())
            resultado = {"titulo": "Tendencias de Producto y Ventas", "tendencias_erp": tendencias[:10], "shopify_mensual": shopify_trend}

        # ── Agente 5: Brief ────────────────────────────────────────────────────
        elif agente == "brief":
            params = request.get_json() or {}
            campana_id = params.get("campana_id")
            campana = None
            if campana_id:
                row = c.execute("SELECT * FROM marketing_campanas WHERE id=?", (campana_id,)).fetchone()
                if row: campana = dict(row)
            top = c.execute("""
                SELECT sku, SUM(unidades) as total FROM liberaciones WHERE creado_en>=?
                GROUP BY sku ORDER BY total DESC LIMIT 5
            """, (hace90,)).fetchall()
            briefs = []
            for t in top:
                sku = t["sku"]
                precio = c.execute("SELECT MAX(precio_base) as p FROM stock_pt WHERE sku=?", (sku,)).fetchone()["p"] or 0
                ig_mentions = c.execute("SELECT COUNT(*) as n FROM animus_instagram_posts WHERE descripcion LIKE ?", (f'%{sku}%',)).fetchone()["n"]
                briefs.append({"sku": sku, "uds_90d": t["total"], "precio": precio, "ig_menciones": ig_mentions,
                    "brief": f"SKU {sku}: {t['total']} uds liberadas en 90d. Canal recomendado: {'Instagram Reels' if ig_mentions==0 else 'Instagram + stories'}. Claim: activos para piel latina. Formato: video 30s."})
            resultado = {"titulo": "Brief de Contenido por SKU Top", "briefs": briefs, "campana": campana}

        # ── Agente 6: Pricing ──────────────────────────────────────────────────
        elif agente == "pricing":
            stock_rows = c.execute("""
                SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio
                FROM stock_pt WHERE estado='Disponible' AND precio_base > 0 GROUP BY sku
            """).fetchall()
            propuestas = []
            for row in stock_rows:
                sku, stock, precio = row["sku"], row["stock"], row["precio"]
                lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                rotacion = lib_90 / 3.0
                meses_cob = round(stock / rotacion, 1) if rotacion > 0 else 99
                precio_costo_aprox = precio * 0.35
                margen_actual = ((precio - precio_costo_aprox) / precio) * 100
                max_dto_seguro = int(max(0, margen_actual - 40))
                if meses_cob > 4 and max_dto_seguro >= 5:
                    propuestas.append({"sku": sku, "stock": stock, "precio_normal": precio,
                        "max_descuento_pct": max_dto_seguro,
                        "precio_promo": round(precio * (1 - max_dto_seguro/100), 0),
                        "meses_cobertura": meses_cob,
                        "razon": f"{meses_cob} meses de inventario → descuento del {max_dto_seguro}% mantiene margen ≥40%"})
            propuestas.sort(key=lambda x: -x["meses_cobertura"])
            resultado = {"titulo": "Propuestas de Pricing y Promociones", "propuestas": propuestas[:8]}

        # ── Agente 7: Reorden B2B ──────────────────────────────────────────────
        elif agente == "reorden":
            clientes_b2b = c.execute("""
                SELECT email, COUNT(*) as pedidos, SUM(total) as revenue,
                       MIN(creado_en) as primer_pedido, MAX(creado_en) as ultimo_pedido,
                       AVG(total) as ticket_promedio
                FROM animus_shopify_orders GROUP BY email HAVING pedidos >= 2
                ORDER BY revenue DESC LIMIT 10
            """).fetchall()
            predicciones = []
            for cl in clientes_b2b:
                primer = cl["primer_pedido"]; ultimo = cl["ultimo_pedido"]; pedidos = cl["pedidos"]
                if primer and ultimo and primer != ultimo:
                    d1 = datetime.strptime(primer[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(ultimo[:10], "%Y-%m-%d")
                    intervalo_dias = (d2 - d1).days / max(pedidos - 1, 1)
                    proximo = (d2 + timedelta(days=intervalo_dias)).strftime("%Y-%m-%d")
                    dias_para_reorden = (datetime.strptime(proximo, "%Y-%m-%d") - hoy).days
                    predicciones.append({"email": cl["email"], "pedidos": pedidos,
                        "revenue_total": round(cl["revenue"], 0),
                        "ticket_promedio": round(cl["ticket_promedio"], 0),
                        "intervalo_dias": round(intervalo_dias),
                        "ultimo_pedido": ultimo[:10],
                        "proximo_reorden_estimado": proximo,
                        "dias_para_reorden": dias_para_reorden,
                        "urgencia": "hoy" if dias_para_reorden <= 0 else ("esta semana" if dias_para_reorden <= 7 else ("este mes" if dias_para_reorden <= 30 else "próximos meses"))})
            predicciones.sort(key=lambda x: x["dias_para_reorden"])
            resultado = {"titulo": "Predicción de Reórdenes B2B", "predicciones": predicciones, "total": len(predicciones)}

        # ── Agente 8: Canibalización ───────────────────────────────────────────
        elif agente == "canibal":
            activas = list(c.execute("""
                SELECT id, nombre, canal, sku_objetivo, fecha_inicio, fecha_fin
                FROM marketing_campanas WHERE estado IN ('Activa','Planificada')
            """).fetchall())
            conflictos = []
            for i in range(len(activas)):
                for j in range(i+1, len(activas)):
                    a, b = activas[i], activas[j]
                    mismo_sku = a["sku_objetivo"] and b["sku_objetivo"] and a["sku_objetivo"] == b["sku_objetivo"]
                    mismo_canal = a["canal"] == b["canal"]
                    try:
                        ai, af = a["fecha_inicio"] or "9999", a["fecha_fin"] or "9999"
                        bi, bf = b["fecha_inicio"] or "9999", b["fecha_fin"] or "9999"
                        solapan = ai <= bf and bi <= af
                    except: solapan = False
                    if solapan and (mismo_canal or mismo_sku):
                        conflictos.append({"campana_a": a["nombre"], "campana_b": b["nombre"],
                            "conflicto": "Mismo SKU" if mismo_sku else "Mismo canal",
                            "canal": a["canal"], "sku": a["sku_objetivo"],
                            "recomendacion": "Escalonar al menos 2 semanas entre campañas."})
            resultado = {"titulo": "Detección de Canibalización", "conflictos": conflictos, "campanas_revisadas": len(activas)}

        # ── Agente 9: Contenido Auto ───────────────────────────────────────────
        elif agente == "contenido_auto":
            top_skus = c.execute("""
                SELECT sku, SUM(unidades) as total FROM liberaciones WHERE creado_en>=?
                GROUP BY sku ORDER BY total DESC LIMIT 3
            """, (hace30,)).fetchall()
            generados = []
            for s in top_skus:
                sku = s["sku"]
                precio = c.execute("SELECT MAX(precio_base) as p FROM stock_pt WHERE sku=?", (sku,)).fetchone()["p"] or 0
                caption = f"✨ {sku} — tu aliado para una piel que brilla.\n\n🧬 Activos de última generación para piel latina.\n💛 ÁNIMUS Lab | Ciencia para tu piel\n.\n#AnimusLab #SkincareLatino #PielLatina"
                generados.append({"sku": sku, "uds_30d": s["total"], "precio": precio,
                    "caption_instagram": caption,
                    "asunto_email": f"{sku} — Tu piel lo estaba esperando",
                    "texto_whatsapp": f"Hola\! Te cuento sobre {sku} de ÁNIMUS Lab. ¿Te interesa? 🧴✨"})
            resultado = {"titulo": "Contenido Auto-Generado para Top SKUs", "piezas": generados}

        # ── Agente 10: Alerta Stock ────────────────────────────────────────────
        elif agente == "alerta_stock":
            stock_rows = c.execute("""
                SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio
                FROM stock_pt WHERE estado='Disponible' GROUP BY sku
            """).fetchall()
            alertas = []
            for row in stock_rows:
                sku, stock, precio = row["sku"], row["stock"], row["precio"] or 0
                lib_30 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace30)).fetchone()["t"]
                rotacion = lib_30
                shopify_30 = c.execute("SELECT COALESCE(SUM(unidades_total),0) as t FROM animus_shopify_orders WHERE sku_items LIKE ? AND creado_en>=?", (f'%{sku}%', hace30)).fetchone()["t"]
                demanda_total = rotacion + shopify_30
                dias_real = round(stock / (demanda_total / 30.0), 0) if demanda_total > 0 else 999
                nivel = "critico" if dias_real <= 7 else ("advertencia" if dias_real <= 21 else "ok")
                if nivel != "ok":
                    alertas.append({"sku": sku, "stock": stock, "dias_cobertura_real": dias_real,
                        "rotacion_erp": rotacion, "demanda_shopify_30d": shopify_30, "nivel": nivel,
                        "accion": f"{'REPOSICIÓN URGENTE' if nivel=='critico' else 'Planificar producción'}: {sku} tiene {dias_real} días de cobertura."})
            alertas.sort(key=lambda x: x["dias_cobertura_real"])
            resultado = {"titulo": "Alertas de Stock vs Demanda Real", "alertas": alertas, "total": len(alertas)}

        # Enriquecer con Claude IA
        try:
            analisis = _call_claude(conn, agente, resultado)
            if analisis:
                resultado["analisis_ia"] = analisis
        except Exception:
            pass

        # Guardar log
        c.execute("""INSERT INTO marketing_agentes_log(agente,accion,resultado,ejecutado_por)
            VALUES(?,?,?,?)""",
            (agente.capitalize(), "Ejecutado",
             json.dumps(resultado, ensure_ascii=False)[:2000], u))
        conn.commit()
        resultado["agente"] = agente
        resultado["fecha"] = datetime.now().isoformat()
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

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
        pass  # conexión cerrada automáticamente por teardown_appcontext
