import sqlite3, json, traceback, urllib.request
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from config import DB_PATH, ADMIN_USERS, ANIMUS_ACCESS
from database import get_db

bp = Blueprint("animus", __name__)

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

def _db():
    conn = get_db()

    return conn

def _auth():
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in ANIMUS_ACCESS:
        return None, jsonify({"error": "Sin acceso al módulo ÁNIMUS"}), 403
    return u, None, None

def _fmt(row):
    return dict(row) if row else None

def _fmt_many(rows):
    return [dict(r) for r in rows]

def _cfg(conn, clave, default=None):
    row = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (clave,)).fetchone()
    return row["valor"] if row else default

def _call_claude(conn, agente, datos):
    """Llama Claude API para generar análisis inteligente en español sobre los datos del agente."""
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

# ── CONFIG ──────────────────────────────────────────────────────────────────

@bp.route("/api/animus/config", methods=["GET", "POST"])
def animus_config():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        if request.method == "POST":
            data = request.json or {}
            for k, v in data.items():
                conn.execute("INSERT OR REPLACE INTO animus_config(clave,valor,actualizado) VALUES(?,?,datetime('now'))", (k, v))
            conn.commit()
            return jsonify({"ok": True})
        rows = conn.execute("SELECT clave, CASE WHEN clave LIKE '%token%' OR clave LIKE '%key%' OR clave LIKE '%secret%' THEN '***' ELSE valor END as valor, actualizado FROM animus_config").fetchall()
        cfg = {r["clave"]: {"valor": r["valor"], "actualizado": r["actualizado"]} for r in rows}
        connected = {
            "shopify": bool(_cfg(conn, "shopify_token") and _cfg(conn, "shopify_shop")),
            "ghl":     bool(_cfg(conn, "ghl_api_key") and _cfg(conn, "ghl_location_id")),
            "instagram": bool(_cfg(conn, "instagram_token") and _cfg(conn, "instagram_user_id")),
        }
        return jsonify({"config": cfg, "connected": connected})
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── SYNC ────────────────────────────────────────────────────────────────────

@bp.route("/api/animus/sync/<platform>", methods=["POST"])
def animus_sync(platform):
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        if platform == "shopify":
            token  = _cfg(conn, "shopify_token")
            shop   = _cfg(conn, "shopify_shop")
            if not token or not shop:
                return jsonify({"error": "Shopify no configurado. Agrega shopify_token y shopify_shop en Configuración."}), 400
            try:
                import urllib.request as ur
                url = f"https://{shop}/admin/api/2024-01/orders.json?status=any&limit=250"
                req = ur.Request(url, headers={"X-Shopify-Access-Token": token})
                with ur.urlopen(req, timeout=15) as r:
                    orders = json.loads(r.read())["orders"]
                synced = 0
                for o in orders:
                    items_sku = json.dumps([{"sku": li.get("sku",""), "qty": li.get("quantity",0)} for li in o.get("line_items",[])])
                    total_uds = sum(li.get("quantity",0) for li in o.get("line_items",[]))
                    addr = o.get("billing_address") or {}
                    conn.execute("""INSERT OR REPLACE INTO animus_shopify_orders
                        (shopify_id,nombre,email,total,moneda,estado,estado_pago,sku_items,unidades_total,ciudad,pais,creado_en,synced_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                        (str(o["id"]), o.get("name",""), o.get("email",""),
                         float(o.get("total_price",0)), o.get("currency","COP"),
                         o.get("fulfillment_status",""), o.get("financial_status",""),
                         items_sku, total_uds,
                         addr.get("city",""), addr.get("country_code","CO"),
                         o.get("created_at","")[:10]))
                    synced += 1
                conn.commit()
                return jsonify({"ok": True, "synced": synced, "platform": "shopify"})
            except Exception as e:
                return jsonify({"error": f"Error Shopify API: {str(e)}"}), 502

        elif platform == "ghl":
            api_key  = _cfg(conn, "ghl_api_key")
            loc_id   = _cfg(conn, "ghl_location_id")
            if not api_key:
                return jsonify({"error": "GHL no configurado. Agrega ghl_api_key en Configuración."}), 400
            try:
                import urllib.request as ur
                url = f"https://rest.gohighlevel.com/v1/contacts/?locationId={loc_id}&limit=100" if loc_id else "https://rest.gohighlevel.com/v1/contacts/?limit=100"
                req = ur.Request(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
                with ur.urlopen(req, timeout=15) as r:
                    contacts = json.loads(r.read()).get("contacts", [])
                synced = 0
                for c in contacts:
                    tags = json.dumps(c.get("tags", []))
                    conn.execute("""INSERT OR REPLACE INTO animus_ghl_contacts
                        (ghl_id,nombre,email,telefono,etiquetas,fuente,creado_en,synced_at)
                        VALUES(?,?,?,?,?,?,?,datetime('now'))""",
                        (c.get("id",""), f"{c.get('firstName','')} {c.get('lastName','')}".strip(),
                         c.get("email",""), c.get("phone",""), tags,
                         c.get("source",""), c.get("dateAdded","")[:10] if c.get("dateAdded") else ""))
                    synced += 1
                conn.commit()
                return jsonify({"ok": True, "synced": synced, "platform": "ghl"})
            except Exception as e:
                return jsonify({"error": f"Error GHL API: {str(e)}"}), 502

        elif platform == "instagram":
            token   = _cfg(conn, "instagram_token")
            user_id = _cfg(conn, "instagram_user_id")
            if not token or not user_id:
                return jsonify({"error": "Instagram no configurado. Agrega instagram_token e instagram_user_id."}), 400
            try:
                import urllib.request as ur
                fields = "id,media_type,caption,media_url,permalink,like_count,comments_count,timestamp"
                url = f"https://graph.instagram.com/v19.0/{user_id}/media?fields={fields}&access_token={token}&limit=50"
                req = ur.Request(url)
                with ur.urlopen(req, timeout=15) as r:
                    posts = json.loads(r.read()).get("data", [])
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
            except Exception as e:
                return jsonify({"error": f"Error Instagram API: {str(e)}"}), 502
        else:
            return jsonify({"error": "Plataforma desconocida"}), 400
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── COMANDO GENERAL ──────────────────────────────────────────────────────────

@bp.route("/api/animus/comando")
def animus_comando():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    try:
        hoy = datetime.now().strftime("%Y-%m-%d")
        hace30  = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        hace90  = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        # Stock PT por SKU
        stock_pt = _fmt_many(c.execute("""
            SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio
            FROM stock_pt WHERE estado='Disponible'
            GROUP BY sku ORDER BY stock DESC LIMIT 10
        """).fetchall())

        # Liberaciones últimos 30 días
        lib_30 = c.execute("SELECT COALESCE(SUM(unidades),0) as total FROM liberaciones WHERE creado_en >= ?", (hace30,)).fetchone()["total"]
        lib_30_skus = _fmt_many(c.execute("""
            SELECT sku, SUM(unidades) as uds FROM liberaciones
            WHERE creado_en >= ? GROUP BY sku ORDER BY uds DESC LIMIT 5
        """, (hace30,)).fetchall())

        # Campañas activas
        campanas_activas = _fmt_many(c.execute("""
            SELECT nombre, canal, presupuesto, presupuesto_gastado, resultado_ventas,
                   fecha_inicio, fecha_fin, sku_objetivo, objetivo_unidades
            FROM marketing_campanas WHERE estado IN ('Activa','En ejecución')
            ORDER BY fecha_inicio DESC LIMIT 5
        """).fetchall())

        # Influencers activos
        influencers = c.execute("SELECT COUNT(*) as n FROM marketing_influencers WHERE estado='Activo'").fetchone()["n"]

        # Shopify: ventas últimos 30 días
        shopify_ventas = c.execute("SELECT COALESCE(SUM(total),0) as total, COUNT(*) as pedidos FROM animus_shopify_orders WHERE creado_en >= ?", (hace30,)).fetchone()
        shopify_clientes = c.execute("SELECT COUNT(DISTINCT email) as n FROM animus_shopify_customers").fetchone()["n"]

        # GHL: contactos y oportunidades
        ghl_contactos = c.execute("SELECT COUNT(*) as n FROM animus_ghl_contacts").fetchone()["n"]
        ghl_valor = c.execute("SELECT COALESCE(SUM(valor),0) as total FROM animus_ghl_oportunidades WHERE estado='Open'").fetchone()["total"]

        # Instagram: últimas métricas
        ig_reciente = _fmt_many(c.execute("""
            SELECT likes, comentarios, publicado_en FROM animus_instagram_posts
            ORDER BY publicado_en DESC LIMIT 5
        """).fetchall())
        ig_avg_likes = c.execute("SELECT COALESCE(AVG(likes),0) as avg FROM animus_instagram_posts").fetchone()["avg"]
        ig_total = c.execute("SELECT COUNT(*) as n FROM animus_instagram_posts").fetchone()["n"]

        # Alertas de calidad activas
        alertas_calidad = c.execute("""
            SELECT COUNT(*) as n FROM compromisos
            WHERE estado IN ('Pendiente','En Proceso') AND prioridad IN ('Critico','Alta')
        """).fetchone()["n"]

        # Próximas fechas del calendario cosmético
        proximas = []
        for ev in CALENDARIO_COSMETICO:
            dias = (datetime.strptime(ev["fecha"], "%Y-%m-%d") - datetime.now()).days
            if -7 <= dias <= 90:
                proximas.append({**ev, "dias_restantes": dias})
        proximas.sort(key=lambda x: x["dias_restantes"])

        # Revenue total Shopify
        revenue_total = c.execute("SELECT COALESCE(SUM(total),0) as t FROM animus_shopify_orders").fetchone()["t"]

        # Sync status
        last_sync = {}
        for plat in ["shopify","ghl","instagram"]:
            row = c.execute("SELECT MAX(synced_at) as ts FROM animus_" + plat + ("_orders" if plat=="shopify" else "_contacts" if plat=="ghl" else "_posts")).fetchone()
            last_sync[plat] = row["ts"]

        connected = {
            "shopify":   bool(_cfg(conn, "shopify_token")),
            "ghl":       bool(_cfg(conn, "ghl_api_key")),
            "instagram": bool(_cfg(conn, "instagram_token")),
        }

        return jsonify({
            "kpis": {
                "lib_30d": lib_30,
                "campanas_activas": len(campanas_activas),
                "influencers_activos": influencers,
                "alertas_calidad": alertas_calidad,
                "shopify_ventas_30d": round(shopify_ventas["total"], 0),
                "shopify_pedidos_30d": shopify_ventas["pedidos"],
                "shopify_clientes_total": shopify_clientes,
                "ghl_contactos": ghl_contactos,
                "ghl_pipeline_valor": ghl_valor,
                "ig_avg_likes": round(ig_avg_likes, 0),
                "ig_total_posts": ig_total,
                "revenue_total": round(revenue_total, 0),
            },
            "stock_pt": stock_pt,
            "lib_30_top": lib_30_skus,
            "campanas_activas": campanas_activas,
            "ig_reciente": ig_reciente,
            "calendario": proximas[:5],
            "connected": connected,
            "last_sync": last_sync,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INTELIGENCIA DE PRODUCTO ─────────────────────────────────────────────────

@bp.route("/api/animus/productos")
def animus_productos():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    try:
        hace90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        skus_stock = _fmt_many(c.execute("""
            SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio
            FROM stock_pt WHERE estado='Disponible' GROUP BY sku
        """).fetchall())

        resultado = []
        for s in skus_stock:
            sku = s["sku"]
            stock = s["stock"] or 0
            precio = s["precio"] or 0

            lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
            lib_30 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace30)).fetchone()["t"]
            rotacion_mes = (lib_90 / 3.0) if lib_90 > 0 else 0
            meses_cob = round(stock / rotacion_mes, 1) if rotacion_mes > 0 else 99
            revenue_30 = round(lib_30 * precio, 0)

            # Clasificación ABC
            if rotacion_mes >= 50 or revenue_30 >= 5000000:
                clase = "A"
            elif rotacion_mes >= 20 or revenue_30 >= 1000000:
                clase = "B"
            else:
                clase = "C"

            # Shopify: ventas del SKU
            shopify_uds = c.execute("""
                SELECT COALESCE(SUM(unidades_total),0) as t FROM animus_shopify_orders
                WHERE sku_items LIKE ? AND creado_en >= ?
            """, (f'%"{sku}"%', hace30)).fetchone()["t"]

            resultado.append({
                "sku": sku, "stock": stock, "precio": precio,
                "rotacion_mes": round(rotacion_mes, 1),
                "meses_cobertura": meses_cob,
                "lib_30d": lib_30, "lib_90d": lib_90,
                "revenue_30d": revenue_30,
                "shopify_uds_30d": shopify_uds,
                "clase_abc": clase,
                "estado": "ok" if meses_cob <= 3 else ("alerta" if meses_cob <= 6 else "riesgo"),
            })

        resultado.sort(key=lambda x: x["revenue_30d"], reverse=True)
        return jsonify({"skus": resultado, "total": len(resultado)})
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INTELIGENCIA DE CLIENTES ─────────────────────────────────────────────────

@bp.route("/api/animus/clientes")
def animus_clientes():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    try:
        # Top clientes Shopify por valor
        top_shopify = _fmt_many(c.execute("""
            SELECT email, COUNT(*) as pedidos, SUM(total) as revenue,
                   MAX(creado_en) as ultimo_pedido
            FROM animus_shopify_orders
            GROUP BY email ORDER BY revenue DESC LIMIT 10
        """).fetchall())

        # Pipeline GHL
        pipeline = _fmt_many(c.execute("""
            SELECT etapa, COUNT(*) as contactos, COALESCE(SUM(valor_oportunidad),0) as valor
            FROM animus_ghl_contacts GROUP BY etapa ORDER BY valor DESC
        """).fetchall())

        # Nuevos contactos GHL últimos 30 días
        hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        nuevos_ghl = c.execute("SELECT COUNT(*) as n FROM animus_ghl_contacts WHERE creado_en >= ?", (hace30,)).fetchone()["n"]

        # Segmentación geográfica Shopify
        geo = _fmt_many(c.execute("""
            SELECT ciudad, COUNT(*) as pedidos, SUM(total) as revenue
            FROM animus_shopify_orders WHERE ciudad != ''
            GROUP BY ciudad ORDER BY revenue DESC LIMIT 8
        """).fetchall())

        # Recencia: clientes que no compran en 60+ días
        hace60 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        dormidos = c.execute("""
            SELECT COUNT(DISTINCT email) as n FROM animus_shopify_customers
            WHERE email NOT IN (
                SELECT DISTINCT email FROM animus_shopify_orders WHERE creado_en >= ?
            )
        """, (hace60,)).fetchone()["n"]

        return jsonify({
            "top_shopify": top_shopify,
            "pipeline_ghl": pipeline,
            "nuevos_ghl_30d": nuevos_ghl,
            "geo": geo,
            "clientes_dormidos": dormidos,
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── INSTAGRAM PANEL ──────────────────────────────────────────────────────────

@bp.route("/api/animus/instagram")
def animus_instagram():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    try:
        posts = _fmt_many(c.execute("""
            SELECT instagram_id, tipo, descripcion, url_permalink,
                   likes, comentarios, alcance, guardados, publicado_en
            FROM animus_instagram_posts ORDER BY publicado_en DESC LIMIT 20
        """).fetchall())

        stats = c.execute("""
            SELECT COUNT(*) as total,
                   COALESCE(AVG(likes),0) as avg_likes,
                   COALESCE(AVG(comentarios),0) as avg_comentarios,
                   COALESCE(SUM(likes),0) as total_likes,
                   COALESCE(SUM(alcance),0) as total_alcance
            FROM animus_instagram_posts
        """).fetchone()

        # Top posts por engagement
        top = _fmt_many(c.execute("""
            SELECT descripcion, likes, comentarios, guardados, url_permalink, publicado_en
            FROM animus_instagram_posts
            ORDER BY (likes + comentarios*3 + guardados*5) DESC LIMIT 5
        """).fetchall())

        return jsonify({
            "posts": posts,
            "stats": _fmt(stats),
            "top_posts": top,
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── GENERADOR DE CONTENIDO ────────────────────────────────────────────────────

@bp.route("/api/animus/contenido/generar", methods=["POST"])
def animus_generar_contenido():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    try:
        data = request.json or {}
        sku      = data.get("sku", "").upper()
        tipo     = data.get("tipo", "instagram_caption")  # instagram_caption | email | whatsapp | brief_influencer | tiktok
        tono     = data.get("tono", "premium")  # premium | cercano | cientifico | urgente
        contexto = data.get("contexto", "")

        # Obtener info del SKU desde ERP
        stock_row = c.execute("SELECT sku, SUM(unidades_disponible) as stock, MAX(precio_base) as precio FROM stock_pt WHERE estado='Disponible' AND sku=? GROUP BY sku", (sku,)).fetchone()
        lib_row = c.execute("SELECT COALESCE(SUM(unidades),0) as lib FROM liberaciones WHERE sku=?", (sku,)).fetchone()
        formula_row = c.execute("SELECT nombre FROM formulas_maestras WHERE codigo=? OR nombre LIKE ?", (sku, f"%{sku}%")).fetchone() if sku else None
        nombre_producto = formula_row["nombre"] if formula_row else sku

        stock = stock_row["stock"] if stock_row else 0
        precio = stock_row["precio"] if stock_row else 0

        # Templates de contenido por tipo y tono
        templates = {
            "instagram_caption": {
                "premium": f"""✨ {nombre_producto} — El secreto de la piel latina.\n\n🧬 Formulado con ciencia real para tu tipo de piel. Ingredientes activos que trabajan de verdad.\n\n{contexto}\n\n💛 ÁNIMUS Lab | Cosmética de alto rendimiento hecha para ti.\n.\n.\n#AnimusLab #SkincareLatino #PielLatina #Cosmética #CuidadoDePiel #BeautyScience""",
                "cercano":  f"""Oye, ¿ya conoces {nombre_producto}? 🤎\n\nTe cuento por qué lo amo...\n{contexto}\n\nEs de los que no puedo dejar de usar. ¿Lo has probado?\n\n👇 Cuéntame en los comentarios\n#AnimusLab #SkincareColombia""",
                "cientifico": f"""🔬 {nombre_producto} — Análisis de formulación.\n\nActivos clave: [ingredientes principales]\nMecanismo de acción: {contexto}\nResultados clínicos: visible en 4 semanas de uso continuo.\n\n📊 Eficacia respaldada por datos.\n#AnimusLab #EvidenceBasedSkincare #DermCommunity""",
                "urgente":  f"""⚡ ÚLTIMAS {stock} unidades disponibles — {nombre_producto}\n\n{contexto}\n\nNo lo dejes pasar. Link en bio 🔗\n#AnimusLab #AgotandoStock #SkincareSale""",
            },
            "email": {
                "premium": f"""Asunto: {nombre_producto} — Tu piel lo estaba esperando\n\nHola [nombre],\n\nHay productos que simplemente funcionan. {nombre_producto} es uno de ellos.\n\n{contexto}\n\nFormulado específicamente para piel latina — porque tu piel merece una ciencia que la entienda.\n\n→ Ver producto: [LINK]\n\nCon cariño,\nEl equipo ÁNIMUS Lab""",
                "urgente":  f"""Asunto: ⚡ Solo {stock} unidades — {nombre_producto}\n\nHola [nombre],\n\nSabemos que lo has estado considerando. Hoy es el momento.\n\n{nombre_producto} tiene {stock} unidades disponibles. Cuando se agote, tardamos en reponer.\n\n{contexto}\n\n→ Asegurar el mío ahora: [LINK]\n\nÁNIMUS Lab""",
            },
            "whatsapp": {
                "premium": f"""Hola 👋\n\nTe escribo de ÁNIMUS Lab. Quería contarte sobre {nombre_producto}.\n\n{contexto}\n\n¿Te interesa saber más? Te envío toda la información. 🧴✨""",
                "urgente":  f"""🚨 Última oportunidad — {nombre_producto}\n\nQuedan {stock} unidades disponibles.\n{contexto}\n\nEscríbeme si quieres asegurar el tuyo antes de que se agote 👆""",
            },
            "brief_influencer": {
                "premium": f"""━━━━━━━━━━━━━━━━━━━━━━━
BRIEF DE COLABORACIÓN — ÁNIMUS Lab
━━━━━━━━━━━━━━━━━━━━━━━

PRODUCTO: {nombre_producto}
PRECIO PVP: ${precio:,.0f} COP

MENSAJE CLAVE:
{contexto if contexto else f"{nombre_producto} está formulado para la piel latina. Ciencia real, resultados visibles."}

QUÉ COMUNICAR:
• Beneficio principal del producto
• Tu experiencia real de uso (mínimo 2 semanas)
• Una rutina sugerida (mañana/noche)

ENTREGABLES ESPERADOS:
□ 1 Reels o video de 30-60 seg
□ 3 Stories (unboxing + uso + resultado)
□ 1 Post en feed con caption y hashtags

HASHTAGS OBLIGATORIOS:
#AnimusLab #PielLatina #SkincareConCiencia

DO's: Mostrar textura, aplicación, skin before/after
DON'Ts: No comparar con otras marcas, no hacer claims médicos

━━━━━━━━━━━━━━━━━━━━━━━""",
            },
            "tiktok": {
                "cercano":  f"""Hook (0-3s): "¿Conoces {nombre_producto}? Esto fue lo que pasó después de 2 semanas..."\n\nDesarrollo (3-25s):\n- Muestra el producto\n- Aplícalo en cámara\n- {contexto}\n- Reacción/resultado\n\nCierre (25-30s): "Link en bio si lo quieres probar 🔗"\n\nSonido sugerido: trending audio beauty\nHashtags: #AnimusLab #SkincareCheck #PielLatina #TikTokBeauty""",
            },
        }

        # Seleccionar template
        tipo_templates = templates.get(tipo, templates["instagram_caption"])
        contenido = tipo_templates.get(tono, list(tipo_templates.values())[0])

        # Guardar en BD
        c.execute("""INSERT INTO animus_contenido_generado(sku,tipo,plataforma,tono,contenido,generado_por,creado_en)
            VALUES(?,?,?,?,?,?,datetime('now'))""",
            (sku, tipo, tipo.split("_")[0] if "_" in tipo else tipo, tono, contenido, u))
        conn.commit()

        return jsonify({
            "sku": sku, "tipo": tipo, "tono": tono,
            "contenido": contenido,
            "nombre_producto": nombre_producto,
            "stock_disponible": stock,
        })
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

@bp.route("/api/animus/contenido/historial")
def animus_contenido_historial():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        rows = conn.execute("""
            SELECT id, sku, tipo, plataforma, tono, usado,
                   SUBSTR(contenido,1,100) as preview, generado_por, creado_en
            FROM animus_contenido_generado ORDER BY creado_en DESC LIMIT 50
        """).fetchall()
        return jsonify(_fmt_many(rows))
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

@bp.route("/api/animus/contenido/<int:cid>/usar", methods=["POST"])
def animus_contenido_usar(cid):
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        conn.execute("UPDATE animus_contenido_generado SET usado=1 WHERE id=?", (cid,))
        conn.commit()
        row = conn.execute("SELECT * FROM animus_contenido_generado WHERE id=?", (cid,)).fetchone()
        return jsonify(_fmt(row))
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── AGENTES IA ───────────────────────────────────────────────────────────────

AGENTES_DISPONIBLES = {
    "estacionalidad", "oportunidad", "roi", "tendencias",
    "brief", "pricing", "reorden", "canibal", "contenido_auto", "alerta_stock"
}

@bp.route("/api/animus/agentes/<agente>", methods=["POST"])
def animus_agente(agente):
    u, err, code = _auth()
    if err: return err, code
    if agente not in AGENTES_DISPONIBLES:
        return jsonify({"error": f"Agente desconocido. Válidos: {AGENTES_DISPONIBLES}"}), 400

    conn = _db()
    c = conn.cursor()
    try:
        hoy    = datetime.now()
        hace30 = (hoy - timedelta(days=30)).strftime("%Y-%m-%d")
        hace90 = (hoy - timedelta(days=90)).strftime("%Y-%m-%d")
        resultado = {}

        # ── Agente 1: Estacionalidad ─────────────────────────────────────────
        if agente == "estacionalidad":
            alertas = []
            for ev in CALENDARIO_COSMETICO:
                dias = (datetime.strptime(ev["fecha"], "%Y-%m-%d") - hoy).days
                if dias < 0 or dias > 120: continue
                # Para cada evento, revisar campañas planeadas
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
                    alertas.append({
                        "evento": ev["evento"], "fecha_evento": ev["fecha"],
                        "color": ev["color"], "dias_restantes": dias,
                        "sku": sku, "campana": cmp["nombre"],
                        "stock_actual": stock, "demanda_proyectada": demanda_ev,
                        "deficit": deficit, "deadline_produccion": deadline_prod,
                        "semanas_para_producir": semanas_prod, "estado": estado,
                        "multiplicador": ev["multiplicador"],
                    })
                # Si no hay campaña pero hay stock del producto, alertar igual para top SKUs
                if not campanas:
                    top_skus = c.execute("""
                        SELECT sku, SUM(unidades_disponible) as stock FROM stock_pt
                        WHERE estado='Disponible' GROUP BY sku ORDER BY stock DESC LIMIT 3
                    """).fetchall()
                    for s in top_skus:
                        sku = s["sku"]
                        if sku in skus_revisados: continue
                        skus_revisados.add(sku)
                        lib_90 = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                        rotacion = lib_90 / 3.0
                        demanda_ev = round(rotacion * ev["multiplicador"])
                        deficit = max(0, demanda_ev - s["stock"])
                        estado = "ok" if deficit == 0 else "advertencia"
                        alertas.append({
                            "evento": ev["evento"], "fecha_evento": ev["fecha"],
                            "color": ev["color"], "dias_restantes": dias,
                            "sku": sku, "campana": None,
                            "stock_actual": s["stock"], "demanda_proyectada": demanda_ev,
                            "deficit": deficit, "deadline_produccion": None,
                            "semanas_para_producir": 0, "estado": estado,
                            "multiplicador": ev["multiplicador"],
                        })

            alertas.sort(key=lambda x: (x["estado"] == "ok", x["dias_restantes"]))
            criticos = [a for a in alertas if a["estado"] == "critico"]
            resultado = {
                "titulo": "Análisis de Estacionalidad",
                "total_alertas": len(alertas),
                "criticos": len(criticos),
                "alertas": alertas[:20],
                "resumen": f"{len(criticos)} SKUs en estado crítico para eventos próximos. {len(alertas)} alertas totales.",
            }

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
                score = 0
                razones = []
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
            shopify_roi = c.execute("SELECT COALESCE(SUM(total),0) as t FROM animus_shopify_orders WHERE creado_en>=?", (hace30,)).fetchone()["t"]
            resultado = {"titulo": "Análisis de ROI por Campaña", "campanas": analisis, "shopify_revenue_30d": shopify_roi}

        # ── Agente 4: Tendencias ───────────────────────────────────────────────
        elif agente == "tendencias":
            hace180 = (hoy - timedelta(days=180)).strftime("%Y-%m-%d")
            hace90b = (hoy - timedelta(days=180)).strftime("%Y-%m-%d")
            skus = c.execute("SELECT DISTINCT sku FROM liberaciones WHERE creado_en>=?", (hace180,)).fetchall()
            tendencias = []
            for s in skus:
                sku = s["sku"]
                r = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=?", (sku, hace90)).fetchone()["t"]
                a = c.execute("SELECT COALESCE(SUM(unidades),0) as t FROM liberaciones WHERE sku=? AND creado_en>=? AND creado_en<?", (sku, hace90b, hace90)).fetchone()["t"]
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

        # ── Agente 5: Brief ───────────────────────────────────────────────────
        elif agente == "brief":
            top = c.execute("""
                SELECT sku, SUM(unidades) as total
                FROM liberaciones WHERE creado_en>=?
                GROUP BY sku ORDER BY total DESC LIMIT 5
            """, (hace90,)).fetchall()
            briefs = []
            for t in top:
                sku = t["sku"]
                precio = c.execute("SELECT MAX(precio_base) as p FROM stock_pt WHERE sku=?", (sku,)).fetchone()["p"] or 0
                ig_mentions = c.execute("SELECT COUNT(*) as n FROM animus_instagram_posts WHERE descripcion LIKE ?", (f"%{sku}%",)).fetchone()["n"]
                briefs.append({"sku": sku, "uds_90d": t["total"], "precio": precio, "ig_menciones": ig_mentions,
                                "brief": f"SKU {sku}: {t['total']} uds liberadas en 90d. Canal recomendado: {'Instagram Reels' if ig_mentions==0 else 'Instagram + stories'}. Claim principal: activos para piel latina. Formato: video 30s mostrando textura y resultado."})
            resultado = {"titulo": "Brief de Contenido por SKU Top", "briefs": briefs}

        # ── Agente 6: Pricing ─────────────────────────────────────────────────
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
                # Descuento máximo seguro asumiendo margen mínimo del 40%
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

        # ── Agente 7: Reorden (B2B) ────────────────────────────────────────────
        elif agente == "reorden":
            # Analizar patrones de pedidos repetidos en Shopify y GHL
            clientes_b2b = c.execute("""
                SELECT email, COUNT(*) as pedidos, SUM(total) as revenue,
                       MIN(creado_en) as primer_pedido, MAX(creado_en) as ultimo_pedido,
                       AVG(total) as ticket_promedio
                FROM animus_shopify_orders
                GROUP BY email HAVING pedidos >= 2
                ORDER BY revenue DESC LIMIT 10
            """).fetchall()
            predicciones = []
            for cl in clientes_b2b:
                primer = cl["primer_pedido"]
                ultimo = cl["ultimo_pedido"]
                pedidos = cl["pedidos"]
                if primer and ultimo and primer != ultimo:
                    from datetime import date
                    d1 = datetime.strptime(primer[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(ultimo[:10], "%Y-%m-%d")
                    intervalo_dias = (d2 - d1).days / max(pedidos - 1, 1)
                    proximo = (d2 + timedelta(days=intervalo_dias)).strftime("%Y-%m-%d")
                    dias_para_reorden = (datetime.strptime(proximo, "%Y-%m-%d") - hoy).days
                    predicciones.append({
                        "email": cl["email"], "pedidos": pedidos,
                        "revenue_total": round(cl["revenue"], 0),
                        "ticket_promedio": round(cl["ticket_promedio"], 0),
                        "intervalo_dias": round(intervalo_dias),
                        "ultimo_pedido": ultimo[:10],
                        "proximo_reorden_estimado": proximo,
                        "dias_para_reorden": dias_para_reorden,
                        "urgencia": "hoy" if dias_para_reorden <= 0 else ("esta semana" if dias_para_reorden <= 7 else ("este mes" if dias_para_reorden <= 30 else "próximos meses")),
                    })
            predicciones.sort(key=lambda x: x["dias_para_reorden"])
            resultado = {"titulo": "Predicción de Reórdenes B2B", "predicciones": predicciones, "total": len(predicciones)}

        # ── Agente 8: Canibalización ───────────────────────────────────────────
        elif agente == "canibal":
            activas = c.execute("""
                SELECT id, nombre, canal, sku_objetivo, fecha_inicio, fecha_fin, presupuesto
                FROM marketing_campanas WHERE estado IN ('Activa','Planificada')
            """).fetchall()
            conflictos = []
            activas_list = list(activas)
            for i in range(len(activas_list)):
                for j in range(i+1, len(activas_list)):
                    a, b = activas_list[i], activas_list[j]
                    mismo_canal = a["canal"] == b["canal"]
                    mismo_sku   = a["sku_objetivo"] and b["sku_objetivo"] and a["sku_objetivo"] == b["sku_objetivo"]
                    # Solapamiento de fechas
                    try:
                        ai, af = a["fecha_inicio"] or "9999", a["fecha_fin"] or "9999"
                        bi, bf = b["fecha_inicio"] or "9999", b["fecha_fin"] or "9999"
                        solapan = ai <= bf and bi <= af
                    except: solapan = False
                    if solapan and (mismo_canal or mismo_sku):
                        conflictos.append({"campana_a": a["nombre"], "campana_b": b["nombre"],
                                           "conflicto": "Mismo SKU" if mismo_sku else "Mismo canal",
                                           "canal": a["canal"], "sku": a["sku_objetivo"],
                                           "recomendacion": f"Escalonar {'por canal' if mismo_canal else 'por SKU'}: separar al menos 2 semanas entre campañas."})
            resultado = {"titulo": "Detección de Canibalización de Campañas", "conflictos": conflictos, "campanas_revisadas": len(activas_list)}

        # ── Agente 9: Contenido Auto ───────────────────────────────────────────
        elif agente == "contenido_auto":
            top_skus = c.execute("""
                SELECT sku, SUM(unidades) as total
                FROM liberaciones WHERE creado_en>=?
                GROUP BY sku ORDER BY total DESC LIMIT 3
            """, (hace30,)).fetchall()
            generados = []
            for s in top_skus:
                sku = s["sku"]
                precio = c.execute("SELECT MAX(precio_base) as p FROM stock_pt WHERE sku=?", (sku,)).fetchone()["p"] or 0
                caption = f"✨ {sku} — tu aliado para una piel que brilla.\n\n🧬 Activos de última generación para piel latina.\nResultados visibles desde la primera semana.\n\n💛 ÁNIMUS Lab | Ciencia para tu piel\n.\n#AnimusLab #SkincareLatino #PielLatina #Cosmética"
                generados.append({"sku": sku, "uds_30d": s["total"], "precio": precio,
                                   "caption_instagram": caption,
                                   "asunto_email": f"{sku} — Tu piel lo estaba esperando",
                                   "texto_whatsapp": f"Hola! Te cuento sobre {sku} de ÁNIMUS Lab. ¿Te interesa? 🧴✨"})
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
                dias_cob = round(stock / (rotacion / 30.0), 0) if rotacion > 0 else 999
                shopify_30 = c.execute("SELECT COALESCE(SUM(unidades_total),0) as t FROM animus_shopify_orders WHERE sku_items LIKE ? AND creado_en>=?", (f'%{sku}%', hace30)).fetchone()["t"]
                demanda_total = rotacion + shopify_30
                dias_real = round(stock / (demanda_total / 30.0), 0) if demanda_total > 0 else 999
                nivel = "critico" if dias_real <= 7 else ("advertencia" if dias_real <= 21 else "ok")
                if nivel != "ok":
                    alertas.append({"sku": sku, "stock": stock, "dias_cobertura_erp": dias_cob,
                                    "dias_cobertura_real": dias_real, "rotacion_erp": rotacion,
                                    "demanda_shopify_30d": shopify_30, "nivel": nivel,
                                    "accion": f"{'REPOSICIÓN URGENTE' if nivel=='critico' else 'Planificar producción'}: {sku} tiene {dias_real} días de cobertura considerando demanda Shopify."})
            alertas.sort(key=lambda x: x["dias_cobertura_real"])
            resultado = {"titulo": "Alertas de Stock vs Demanda Real", "alertas": alertas, "total": len(alertas)}

        # Enriquecer con Claude IA
        try:
            analisis = _call_claude(conn, agente, resultado)
            if analisis:
                resultado["analisis_ia"] = analisis
        except Exception:
            pass  # Claude opcional — no bloquea si falla

        # Guardar log
        c.execute("""INSERT INTO marketing_agentes_log(agente,accion,resultado,ejecutado_por)
            VALUES(?,?,?,?)""",
            (agente.capitalize(), "Ejecutado desde Centro de Mando ÁNIMUS",
             json.dumps(resultado, ensure_ascii=False)[:2000], u))
        conn.commit()
        resultado["agente"] = agente
        resultado["fecha"] = datetime.now().isoformat()
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ── CALENDARIO COSMÉTICO ──────────────────────────────────────────────────────

@bp.route("/api/animus/calendario")
def animus_calendario():
    u, err, code = _auth()
    if err: return err, code
    hoy = datetime.now()
    eventos = []
    for ev in CALENDARIO_COSMETICO:
        dias = (datetime.strptime(ev["fecha"], "%Y-%m-%d") - hoy).days
        eventos.append({**ev, "dias_restantes": dias, "pasado": dias < 0})
    return jsonify({"eventos": eventos})

# ── REDIRECT /animus → /marketing ────────────────────────────────────────────
from flask import redirect as flask_redirect

@bp.route("/animus")
def animus_redirect():
    return flask_redirect("/marketing", code=301)

