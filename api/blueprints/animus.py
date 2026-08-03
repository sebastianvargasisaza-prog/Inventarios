import sqlite3, json, logging, re, traceback, unicodedata, urllib.request
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from config import (DB_PATH, ADMIN_USERS, ANIMUS_ACCESS, COMPRAS_ACCESS,
                    ESPAGIRIA_ACCESS)
from database import get_db
from audit_helpers import audit_log, siguiente_correlativo, intentar_insert_con_retry
from http_helpers import validate_money
# El "hoy" de un movimiento de DINERO se ancla en Colombia, nunca en el UTC del server (M24):
# Render corre en UTC y después de las 19:00 locales `datetime.now()` ya está en el día siguiente.
from tz_colombia import hoy_colombia as _hoy_col, now_colombia as _now_col

bp = Blueprint("animus", __name__)
log = logging.getLogger('animus')

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

def _ani_created_at_bogota(s):
    """SHOPIFY-FIX · 22-may-2026 · Bug #7 · ISO UTC→Bogotá date (slice safe)."""
    if not s:
        return ''
    try:
        from datetime import datetime as _dt2, timezone as _tz, timedelta as _td2
        dt = _dt2.fromisoformat((s or '').replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz.utc)
        return dt.astimezone(_tz(_td2(hours=-5))).strftime('%Y-%m-%d')
    except Exception:
        return (s or '')[:10]


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

_ANIMUS_CONFIG_KEYS = {
    # Keys permitidas en /api/animus/config POST · whitelist explícita
    # P0 audit 26-may · antes aceptaba cualquier key arbitraria, attacker
    # con sesión podía sustituir shopify_token y exfiltrar pedidos.
    "shopify_token", "shopify_shop", "shopify_api_version",
    "ghl_api_key", "ghl_location_id",
    "instagram_token", "instagram_user_id", "instagram_app_id", "instagram_app_secret",
    "anthropic_api_key",
    # Configuración no-secreta
    "umbral_mp_critico", "ventana_metricas_dias", "auto_sync_enabled",
}


@bp.route("/api/animus/config", methods=["GET", "POST"])
def animus_config():
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        if request.method == "POST":
            # P0 26-may · gate ADMIN_USERS · cualquier user con ANIMUS_ACCESS
            # (Daniela, etc) podía sustituir tokens y exfiltrar.
            try:
                from config import ADMIN_USERS as _AU
            except Exception:
                _AU = {'sebastian', 'alejandro'}
            if (u or '').lower() not in {x.lower() for x in _AU}:
                return jsonify({"error": "Solo admin"}), 403
            data = request.json or {}
            invalid_keys = [k for k in data.keys() if k not in _ANIMUS_CONFIG_KEYS]
            if invalid_keys:
                return jsonify({"error": f"keys no permitidas: {invalid_keys[:5]}",
                                 "permitidas": sorted(_ANIMUS_CONFIG_KEYS)}), 400
            c = conn.cursor()
            audit_despues = {}
            for k, v in data.items():
                c.execute("INSERT OR REPLACE INTO animus_config(clave,valor,actualizado) VALUES(?,?,datetime('now', '-5 hours'))", (k, v))
                # Enmascarar secrets en audit_log
                if any(s in k.lower() for s in ('token','key','secret','password')):
                    masked = (str(v)[:3] + '***' + str(v)[-3:]) if v and len(str(v)) > 6 else '***'
                else:
                    masked = str(v)[:80]
                audit_despues[k] = masked
            try:
                from audit_helpers import audit_log as _al
                _al(c, usuario=u, accion='ANIMUS_CONFIG_UPDATE', tabla='animus_config',
                    despues=audit_despues,
                    detalle=f'Animus config · {len(data)} keys actualizadas')
            except Exception as _ae:
                import logging as _lg
                _lg.getLogger('animus').warning('audit animus_config fallo: %s', _ae)
            conn.commit()
            return jsonify({"ok": True})
        rows = conn.execute("SELECT clave, CASE WHEN clave LIKE '%token%' OR clave LIKE '%key%' OR clave LIKE '%secret%' OR clave LIKE '%password%' OR clave LIKE '%api%' THEN '***' ELSE valor END as valor, actualizado FROM animus_config").fetchall()
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
            # Sebastián 23-may-2026 PM · consolidación 4→1 · delega al
            # helper unificado shopify_client.sync_shopify_orders.
            # incluir_movimientos=True para que cree movimientos
            # SHOPIFY_VENTA en kardex (caso exclusivo de este endpoint).
            from shopify_client import sync_shopify_orders as _sso
            # Ventana acotable (3-ago). El cron de las 6 AM trae 90 días, pero para "traer lo
            # de hoy" desde la caja eso son 7.000+ pedidos y >45s reteniendo uno de los 3
            # workers (M43/M89: un endpoint pesado llamado un par de veces satura la app).
            # Con una ventana corta la misma operación tarda segundos.
            _dias = request.args.get('dias') or (request.get_json(silent=True) or {}).get('dias')
            try:
                _dias = max(1, min(int(_dias), 90)) if _dias else 90
            except (TypeError, ValueError):
                _dias = 90
            d = _sso(conn, days=_dias, incluir_movimientos=True)
            if not d.get('ok'):
                return jsonify({"error": d.get('error') or 'Shopify sync falló'}), 502
            return jsonify({"ok": True, "synced": d.get('synced', 0),
                            "ventas_inventario": d.get('ventas_inventario', 0),
                            "platform": "shopify"})

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
                        VALUES(?,?,?,?,?,?,?,datetime('now', '-5 hours'))""",
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
                        VALUES(?,?,?,?,?,?,?,?,datetime('now', '-5 hours'))""",
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
        # Ventanas ancladas a Colombia (M24): con el UTC de Render, de noche "hoy" ya era
        # mañana y los KPIs del día salían vacíos con la operación todavía abierta.
        _ahora = _now_col()
        hoy = _ahora.strftime("%Y-%m-%d")
        hace30  = (_ahora - timedelta(days=30)).strftime("%Y-%m-%d")
        hace90  = (_ahora - timedelta(days=90)).strftime("%Y-%m-%d")

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

        # PERF-FIX 27-may-2026 PM · antes N+1 (3 SELECT por SKU · 50 SKUs =
        # 150+ queries al abrir ANIMUS Lab). Ahora 3 queries globales GROUP BY
        # + dict lookup O(1) en el loop.
        # Claves en UPPER(TRIM) · stock_pt/liberaciones/Shopify no comparten case (M2/M58);
        # sin normalizar, rotación/cobertura/ABC salían en 0 o clase C errónea en silencio.
        def _kup(x):
            return str(x or '').strip().upper()
        _lib90_por_sku = {}
        for _r in c.execute(
            "SELECT sku, COALESCE(SUM(unidades),0) FROM liberaciones "
            "WHERE creado_en>=? GROUP BY sku", (hace90,)).fetchall():
            _lib90_por_sku[_kup(_r[0])] = _lib90_por_sku.get(_kup(_r[0]), 0) + (_r[1] or 0)
        _lib30_por_sku = {}
        for _r in c.execute(
            "SELECT sku, COALESCE(SUM(unidades),0) FROM liberaciones "
            "WHERE creado_en>=? GROUP BY sku", (hace30,)).fetchall():
            _lib30_por_sku[_kup(_r[0])] = _lib30_por_sku.get(_kup(_r[0]), 0) + (_r[1] or 0)
        # Shopify · parsear el JSON de sku_items con json.loads e iterar los ítems (sku + qty).
        # Antes: regex de comillas → capturaba las CLAVES del JSON ('sku','qty') como SKUs y sumaba
        # el TOTAL de la orden por cada token → ventas infladas/mal atribuidas.
        import json as _json_an
        _shopify_por_sku = {}
        try:
            for _r in c.execute(
                "SELECT sku_items FROM animus_shopify_orders "
                "WHERE creado_en >= ? AND COALESCE(sku_items,'') != ''", (hace30,)).fetchall():
                try:
                    _items = _json_an.loads(_r[0]) if isinstance(_r[0], str) else _r[0]
                except Exception:
                    continue
                if not isinstance(_items, list):
                    continue
                for _it in _items:
                    if not isinstance(_it, dict):
                        continue
                    _sk = _kup(_it.get('sku') or _it.get('SKU'))
                    try:
                        _qty = int(_it.get('qty') or _it.get('quantity') or _it.get('cantidad') or 0)
                    except Exception:
                        _qty = 0
                    if _sk and _qty > 0:
                        _shopify_por_sku[_sk] = _shopify_por_sku.get(_sk, 0) + _qty
        except Exception:
            _shopify_por_sku = {}

        resultado = []
        for s in skus_stock:
            sku = s["sku"]
            stock = s["stock"] or 0
            precio = s["precio"] or 0

            _sk_up = _kup(sku)
            lib_90 = _lib90_por_sku.get(_sk_up, 0)
            lib_30 = _lib30_por_sku.get(_sk_up, 0)
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

            # Shopify: ventas del SKU · lookup O(1) normalizado
            shopify_uds = _shopify_por_sku.get(_sk_up, 0)

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
            SELECT pipeline_etapa, COUNT(*) as contactos, COALESCE(SUM(valor_oportunidad),0) as valor
            FROM animus_ghl_contacts GROUP BY pipeline_etapa ORDER BY valor DESC
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
            VALUES(?,?,?,?,?,?,datetime('now', '-5 hours'))""",
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

# ════════════════════════════════════════════════════════════════════
def registrar_movimiento_caja(c, *, tipo, concepto, monto, fecha, metodo='efectivo',
                              referencia='', observaciones='', usuario='',
                              empresa='ANIMUS', origen='', subtipo='', solicitud_id=None):
    """Da de alta un movimiento de caja CON su recibo numerado. Punto único de alta.

    Existe como helper y no inline porque hay dos caminos que dan de alta plata en caja (el
    registro manual y el cobro de un pedido contraentrega) y si cada uno arma su propio
    correlativo terminan con dos series que se pisan (M1/M3).

    El correlativo se calcula leyendo el máximo del año, que NO es race-safe con 3 workers: la
    garantía real es el UNIQUE `ux_caja_recibo_numero` y el retry resuelve la colisión (mismo
    patrón que el numerador de OC). El año sale de la FECHA del movimiento, no del reloj, para
    que la serie de cada año quede completa; si la fecha viene mal formada cae al año de
    Colombia, porque un prefijo basura ('RC-abc-') arrancaría una serie paralela que nadie
    podría auditar.

    Devuelve (recibo_numero, mov_id). NO hace commit: lo hace el caller.
    """
    anio = fecha[:4] if len(fecha) >= 4 and fecha[:4].isdigit() else _hoy_col().strftime('%Y')
    prefijo = 'RC-%s-' % anio

    def _insertar():
        n = siguiente_correlativo(c, 'animus_caja_menor', 'recibo_numero', prefijo)
        recibo = '%s%04d' % (prefijo, n)
        # `empresa` va en CADA movimiento: la gaveta es una sola pero la plata es de dos
        # empresas, y sin la marca el reporte no las puede separar después.
        # `subtipo` distingue el GASTO del TRASLADO a la cuenta -- consignar no es gastar.
        c.execute("""INSERT INTO animus_caja_menor
            (fecha, tipo, concepto, monto, metodo, referencia, observaciones,
             registrado_por, recibo_numero, empresa, origen, subtipo, solicitud_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fecha, tipo, concepto, monto, metodo, referencia, observaciones, usuario, recibo,
             (empresa or 'ANIMUS').upper(), origen or '', subtipo or '', solicitud_id))
        return recibo, c.lastrowid

    return intentar_insert_con_retry(_insertar, columna='recibo_numero')


# CAJA MENOR (Daniela) — efectivo de ventas contraentrega
# ════════════════════════════════════════════════════════════════════
# Daniela recibe efectivo cuando los clientes pagan contraentrega y
# necesita registrar:
#   - INGRESOS: pago recibido por orden, devolución de proveedor, etc.
#   - EGRESOS: gastos del local, compras pequeñas, devoluciones a clientes
#
# El saldo acumulado = SUM(ingresos) - SUM(egresos). Muestra:
#   - KPIs hoy + mes + saldo total
#   - Lista cronológica con filtros
#
# Decisión de modelo: una sola tabla con `tipo` en lugar de dos (ingresos/
# egresos separadas) — más simple para reportes y el saldo se calcula con
# CASE en el SELECT.

# ═══════════════════════════════════════════════════════════════════════════════
# SOLICITUDES DE PAGO DESDE CAJA MENOR (3-ago · Sebastián)
#
# "luz asistente de espagiria solicita un pago se autoriza pago con caja menor · catalina dice
#  hay que pagar tal cosa decimos paguen con caja menor · daniela es quien maneja caja menor
#  entonces ella paga registra solicita ok de gerencia paga sube el comprobante de ese pago y
#  ese dinero sale de la caja"
#
# Tres roles sobre UN registro que cambia de estado:
#   Catalina (Compras) / Luz (Espagiria)  ->  SOLICITA
#   Gerencia                              ->  AUTORIZA o RECHAZA
#   Daniela (Caja)                        ->  PAGA  + sube el comprobante
#
# Reglas que definen el modelo:
#  · El saldo baja cuando se PAGA, no cuando se autoriza. Una autorización no es plata que
#    salió: si el saldo bajara antes, dejaría de cuadrar contra el efectivo de la gaveta, que
#    es lo único que Daniela puede contar contra la realidad.
#  · Bajo el TOPE (app_settings · configurable sin desplegar) no hace falta gerencia, pero
#    igual queda registrado que pasó por ahí y por qué (`autorizacion_via`), porque un atajo
#    sin rastro es indistinguible de un salto del control.
#  · Cada transición va con CAS: dos clics no pueden autorizar dos veces ni pagar dos veces.
#  · El comprobante puede subirse DESPUÉS (decisión de Sebastián), pero lo que no tiene
#    respaldo se cuenta y se muestra: un egreso sin comprobante es una salida que nadie puede
#    verificar, así que tiene que incomodar hasta que se cierre.
# ═══════════════════════════════════════════════════════════════════════════════

EMPRESAS_CAJA = ('ANIMUS', 'ESPAGIRIA')
CAJA_ESTADOS = ('solicitada', 'autorizada', 'rechazada', 'pagada', 'anulada')


def caja_tope_sin_autorizar(conn):
    """Monto bajo el cual quien maneja la caja paga sin esperar a gerencia.

    Vive en `app_settings` porque es una decisión de gerencia, no de código: cambiarla no
    puede exigir un despliegue. Si el valor quedó basura, cae al default en vez de dejar la
    caja sin control (un tope inválido leído como 0 frenaría todo, y como infinito abriría todo).
    """
    try:
        row = conn.execute(
            "SELECT valor FROM app_settings WHERE clave='caja_tope_sin_autorizar'").fetchone()
        if row and str(row[0]).strip():
            v = float(str(row[0]).strip())
            if v >= 0:
                return v
    except Exception as e:
        log.warning('no pude leer el tope de caja: %s', e)
    return 200000.0


def _caja_auth():
    """Puerta de las SOLICITUDES de pago de caja.

    NO puede ser `_auth()` (ANIMUS_ACCESS): quienes SOLICITAN son Catalina desde Compras y Luz
    desde Espagiria, y ninguna de las dos está en ese set -- con la puerta de ÁNIMUS la feature
    nacía inalcanzable para justo la gente que la pidió (M121: el permiso se amplía en la
    PUERTA, no sólo al final de la cadena).

    Quién puede hacer QUÉ se decide después, por acción: autorizar es de gerencia y pagar es
    de quien maneja la caja. Acá sólo se decide quién entra.
    """
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in (ANIMUS_ACCESS | COMPRAS_ACCESS | ESPAGIRIA_ACCESS | ADMIN_USERS):
        return None, jsonify({"error": "Sin acceso a las solicitudes de caja"}), 403
    return u, None, None


def _caja_puede_autorizar(u):
    """Gerencia. El que PIDE no puede autorizarse a sí mismo (se valida en el endpoint)."""
    return u in ADMIN_USERS


def _caja_puede_pagar(u):
    """Quien maneja la caja. Admin incluido para no dejar la caja bloqueada si Daniela falta."""
    return u in ANIMUS_ACCESS or u in ADMIN_USERS


def _caja_sol_dict(r, cols):
    d = dict(zip(cols, r))
    d['monto'] = float(d.get('monto') or 0)
    return d


@bp.route("/api/caja/tope", methods=["GET", "PUT"])
def caja_tope():
    """Lee o cambia el tope de autorización (gerencia · sin desplegar)."""
    u, err, code = _caja_auth()
    if err: return err, code
    conn = _db()
    if request.method == "GET":
        return jsonify({"ok": True, "tope": caja_tope_sin_autorizar(conn)})
    if not _caja_puede_autorizar(u):
        return jsonify({"error": "Solo gerencia puede cambiar el tope"}), 403
    d = request.get_json(silent=True) or {}
    try:
        nuevo = float(d.get("tope"))
    except (TypeError, ValueError):
        return jsonify({"error": "Tope inválido"}), 400
    if nuevo < 0:
        return jsonify({"error": "El tope no puede ser negativo"}), 400
    c = conn.cursor()
    antes = caja_tope_sin_autorizar(conn)
    c.execute("INSERT INTO app_settings (clave, valor) VALUES ('caja_tope_sin_autorizar', ?) "
              "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (str(int(nuevo)),))
    audit_log(c, usuario=u, accion='CAJA_TOPE_CAMBIAR', tabla='app_settings', registro_id=0,
              antes={'tope': antes}, despues={'tope': nuevo},
              detalle='Tope de caja sin autorizar: %s -> %s' % (antes, nuevo))
    conn.commit()
    return jsonify({"ok": True, "tope": nuevo, "antes": antes})


@bp.route("/api/caja/solicitudes", methods=["GET", "POST"])
def caja_solicitudes():
    """GET: lista. POST: crea una solicitud de pago desde caja menor."""
    u, err, code = _caja_auth()
    if err: return err, code
    conn = _db()

    if request.method == "GET":
        estado = (request.args.get("estado") or "").strip().lower()
        empresa = (request.args.get("empresa") or "").strip().upper()
        cond, args = [], []
        if estado:
            cond.append("estado = ?"); args.append(estado)
        if empresa:
            cond.append("UPPER(empresa) = ?"); args.append(empresa)
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        cur = conn.execute(
            "SELECT * FROM caja_solicitudes_pago" + where +
            " ORDER BY solicitado_at DESC, id DESC LIMIT 300", args)
        cols = [x[0] for x in cur.description]
        filas = [_caja_sol_dict(r, cols) for r in cur.fetchall()]
        # Los KPIs se calculan sobre TODO, no sobre la página filtrada: si contaran sólo lo
        # visible, filtrar por estado cambiaría los totales y el número dejaría de significar
        # lo mismo que su etiqueta.
        tot = conn.execute(
            "SELECT estado, COUNT(*), COALESCE(SUM(monto),0) FROM caja_solicitudes_pago "
            "GROUP BY estado").fetchall()
        kpis = {e: {'n': int(n or 0), 'monto': round(float(m or 0), 2)} for e, n, m in tot}
        # Pagos sin respaldo: se cuentan y se muestran para que no se acumulen en silencio.
        sr = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(monto),0) FROM caja_solicitudes_pago "
            "WHERE estado='pagada' AND COALESCE(comprobante_url,'')=''").fetchone()
        return jsonify({"ok": True, "solicitudes": filas, "kpis": kpis,
                        "tope": caja_tope_sin_autorizar(conn),
                        "sin_comprobante": {"n": int(sr[0] or 0),
                                            "monto": round(float(sr[1] or 0), 2)}})

    # ── POST · crear
    d = request.get_json(silent=True) or {}
    concepto = (d.get("concepto") or "").strip()
    if not concepto:
        return jsonify({"error": "Concepto requerido · sin eso nadie sabe qué se está pagando"}), 400
    try:
        monto = float(d.get("monto") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Monto inválido"}), 400
    if monto <= 0:
        return jsonify({"error": "El monto debe ser mayor a 0"}), 400
    empresa = (d.get("empresa") or "ANIMUS").strip().upper()
    if empresa not in EMPRESAS_CAJA:
        return jsonify({"error": "Empresa inválida · debe ser ANIMUS o ESPAGIRIA"}), 400

    tope = caja_tope_sin_autorizar(conn)
    # Bajo el tope no espera a gerencia, pero se DECLARA por qué quedó autorizada: un atajo
    # sin rastro es indistinguible de alguien saltándose el control.
    bajo_tope = monto <= tope
    ahora = _now_col().strftime('%Y-%m-%d %H:%M:%S')
    c = conn.cursor()
    anio = _hoy_col().strftime('%Y')
    prefijo = 'SP-%s-' % anio

    def _insertar():
        n = siguiente_correlativo(c, 'caja_solicitudes_pago', 'numero', prefijo)
        numero = '%s%04d' % (prefijo, n)
        c.execute("""INSERT INTO caja_solicitudes_pago
            (numero, empresa, concepto, monto, beneficiario, modulo_origen, estado,
             solicitado_por, solicitado_at, observaciones,
             autorizado_por, autorizado_at, autorizacion_via)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (numero, empresa, concepto, monto, (d.get("beneficiario") or "").strip(),
             (d.get("modulo_origen") or "").strip(),
             'autorizada' if bajo_tope else 'solicitada',
             u, ahora, (d.get("observaciones") or "").strip(),
             (u if bajo_tope else None), (ahora if bajo_tope else None),
             ('bajo el tope de %s' % int(tope)) if bajo_tope else ''))
        return numero, c.lastrowid

    numero, sid = intentar_insert_con_retry(_insertar, columna='numero')
    audit_log(c, usuario=u, accion='CAJA_SOLICITUD_CREAR', tabla='caja_solicitudes_pago',
              registro_id=sid,
              despues={'numero': numero, 'monto': monto, 'empresa': empresa,
                       'concepto': concepto, 'bajo_tope': bajo_tope},
              detalle='Solicitud de pago %s por %s (%s)' % (numero, monto, empresa))
    conn.commit()
    return jsonify({"ok": True, "id": sid, "numero": numero,
                    "estado": 'autorizada' if bajo_tope else 'solicitada',
                    "bajo_tope": bajo_tope, "tope": tope,
                    "aviso": ('Bajo el tope: no necesita autorización, ya puede pagarse'
                              if bajo_tope else 'Enviada a gerencia para autorizar')}), 201


@bp.route("/api/caja/solicitudes/<int:sid>/autorizar", methods=["POST"])
def caja_solicitud_autorizar(sid):
    u, err, code = _caja_auth()
    if err: return err, code
    if not _caja_puede_autorizar(u):
        return jsonify({"error": "Solo gerencia autoriza pagos de caja"}), 403
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT numero, monto, solicitado_por, estado FROM caja_solicitudes_pago "
                    "WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "Esa solicitud no existe"}), 404
    # Separación de funciones: quien pide no se autoriza a sí mismo. Es el control que hace
    # que la autorización signifique algo.
    if (row[2] or '').lower() == (u or '').lower():
        return jsonify({"error": "No podés autorizar tu propia solicitud"}), 403
    # CAS: dos clics no pueden autorizar dos veces ni pisar un rechazo.
    c.execute("UPDATE caja_solicitudes_pago SET estado='autorizada', autorizado_por=?, "
              "autorizado_at=?, autorizacion_via='gerencia' "
              "WHERE id=? AND estado='solicitada'",
              (u, _now_col().strftime('%Y-%m-%d %H:%M:%S'), sid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "Esa solicitud ya no está pendiente (está '%s')" % row[3],
                        "estado": row[3]}), 409
    audit_log(c, usuario=u, accion='CAJA_SOLICITUD_AUTORIZAR', tabla='caja_solicitudes_pago',
              registro_id=sid, antes={'estado': 'solicitada'},
              despues={'estado': 'autorizada', 'monto': float(row[1] or 0)},
              detalle='Autorizada la solicitud %s por %s' % (row[0], row[1]))
    conn.commit()
    return jsonify({"ok": True, "numero": row[0], "estado": "autorizada"})


@bp.route("/api/caja/solicitudes/<int:sid>/rechazar", methods=["POST"])
def caja_solicitud_rechazar(sid):
    u, err, code = _caja_auth()
    if err: return err, code
    if not _caja_puede_autorizar(u):
        return jsonify({"error": "Solo gerencia rechaza pagos de caja"}), 403
    motivo = ((request.get_json(silent=True) or {}).get("motivo") or "").strip()
    if not motivo:
        # Un rechazo sin motivo deja al que pidió sin saber qué corregir, y a quien audite sin
        # saber por qué no se pagó.
        return jsonify({"error": "El motivo del rechazo es obligatorio"}), 400
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT numero, estado FROM caja_solicitudes_pago WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "Esa solicitud no existe"}), 404
    c.execute("UPDATE caja_solicitudes_pago SET estado='rechazada', rechazado_por=?, "
              "rechazado_at=?, motivo_rechazo=? WHERE id=? AND estado IN ('solicitada','autorizada')",
              (u, _now_col().strftime('%Y-%m-%d %H:%M:%S'), motivo, sid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "No se puede rechazar: está '%s'" % row[1]}), 409
    audit_log(c, usuario=u, accion='CAJA_SOLICITUD_RECHAZAR', tabla='caja_solicitudes_pago',
              registro_id=sid, despues={'estado': 'rechazada', 'motivo': motivo},
              detalle='Rechazada la solicitud %s: %s' % (row[0], motivo))
    conn.commit()
    return jsonify({"ok": True, "numero": row[0], "estado": "rechazada"})


@bp.route("/api/caja/solicitudes/<int:sid>/pagar", methods=["POST"])
def caja_solicitud_pagar(sid):
    """Daniela paga: acá SÍ baja el saldo, con su recibo numerado."""
    u, err, code = _caja_auth()
    if err: return err, code
    if not _caja_puede_pagar(u):
        return jsonify({"error": "No estás autorizado para pagar desde la caja"}), 403
    d = request.get_json(silent=True) or {}
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT numero, empresa, concepto, monto, beneficiario, estado "
                    "FROM caja_solicitudes_pago WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "Esa solicitud no existe"}), 404
    if row[5] != 'autorizada':
        return jsonify({"error": "Solo se paga lo AUTORIZADO · esta está '%s'" % row[5],
                        "estado": row[5]}), 409

    monto = float(row[3] or 0)
    # Un pago que deja la caja en negativo es un pago que no ocurrió: el efectivo de la gaveta
    # no puede ser menor que cero. Se avisa con el saldo real para que se pueda decidir.
    saldo = float(c.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),0) "
        "FROM animus_caja_menor WHERE COALESCE(anulado,0)=0").fetchone()[0] or 0)
    if monto > saldo and not d.get("forzar"):
        return jsonify({"error": "No hay efectivo suficiente en la caja",
                        "saldo": round(saldo, 2), "monto": monto,
                        "puede_forzar": True,
                        "aviso": "Si el efectivo está y el saldo no lo refleja, primero "
                                 "registrá el ingreso que falta"}), 409

    # CAS: dos clics no pagan dos veces la misma solicitud.
    ahora = _now_col().strftime('%Y-%m-%d %H:%M:%S')
    metodo = (d.get("metodo") or "efectivo").strip()
    c.execute("UPDATE caja_solicitudes_pago SET estado='pagada', pagado_por=?, pagado_at=?, "
              "metodo_pago=? WHERE id=? AND estado='autorizada'", (u, ahora, metodo, sid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "Esa solicitud ya fue pagada por otra persona"}), 409

    fecha = (d.get("fecha") or _hoy_col().isoformat()).strip()
    concepto = row[2] + ((' · ' + row[4]) if row[4] else '')
    recibo, mov_id = registrar_movimiento_caja(
        c, tipo='egreso', concepto=concepto, monto=monto, fecha=fecha, metodo=metodo,
        referencia=row[0], observaciones=(d.get("observaciones") or "").strip(),
        usuario=u, empresa=row[1], subtipo='gasto', solicitud_id=sid)
    c.execute("UPDATE caja_solicitudes_pago SET caja_mov_id=? WHERE id=?", (mov_id, sid))
    audit_log(c, usuario=u, accion='CAJA_SOLICITUD_PAGAR', tabla='caja_solicitudes_pago',
              registro_id=sid, antes={'estado': 'autorizada'},
              despues={'estado': 'pagada', 'monto': monto, 'recibo': recibo},
              detalle='Pagada la solicitud %s por %s · recibo %s' % (row[0], monto, recibo))
    conn.commit()
    return jsonify({"ok": True, "numero": row[0], "estado": "pagada",
                    "recibo_numero": recibo, "caja_mov_id": mov_id,
                    "falta_comprobante": True})


@bp.route("/api/caja/solicitudes/<int:sid>/comprobante", methods=["POST"])
def caja_solicitud_comprobante(sid):
    """Sube (o corrige) el respaldo del pago. Se permite DESPUÉS de pagar, a propósito."""
    u, err, code = _caja_auth()
    if err: return err, code
    if not _caja_puede_pagar(u):
        return jsonify({"error": "No estás autorizado"}), 403
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not url:
        return jsonify({"error": "Falta el archivo o el enlace del comprobante"}), 400
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT numero, estado, caja_mov_id, COALESCE(comprobante_url,'') "
                    "FROM caja_solicitudes_pago WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "Esa solicitud no existe"}), 404
    if row[1] != 'pagada':
        return jsonify({"error": "El comprobante es del PAGO · esta solicitud está '%s'" % row[1]}), 409
    ahora = _now_col().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE caja_solicitudes_pago SET comprobante_url=?, comprobante_at=?, "
              "comprobante_por=? WHERE id=?", (url, ahora, u, sid))
    # El movimiento de caja también lo lleva: quien audita la caja mira el movimiento, no la
    # solicitud, y un egreso sin su respaldo a la vista es un egreso sin respaldo.
    if row[2]:
        c.execute("UPDATE animus_caja_menor SET comprobante_url=?, comprobante_at=? WHERE id=?",
                  (url, ahora, row[2]))
    audit_log(c, usuario=u, accion='CAJA_COMPROBANTE_SUBIR', tabla='caja_solicitudes_pago',
              registro_id=sid, antes={'comprobante': row[3]}, despues={'comprobante': url},
              detalle='Comprobante de %s' % row[0])
    conn.commit()
    return jsonify({"ok": True, "numero": row[0], "comprobante_url": url})


@bp.route("/api/caja/traslado", methods=["POST"])
def caja_traslado_cuenta():
    """Consignar efectivo de la caja a la cuenta bancaria.

    NO es un gasto: la plata cambia de bolsillo. Va con `subtipo='traslado'` para que los
    reportes de gasto no la cuenten -- si entrara como egreso común, los gastos del mes
    saldrían inflados y la contabilidad reportaría como gastado algo que está en el banco.
    """
    u, err, code = _caja_auth()
    if err: return err, code
    if not _caja_puede_pagar(u):
        return jsonify({"error": "No estás autorizado para mover la caja"}), 403
    d = request.get_json(silent=True) or {}
    try:
        monto = float(d.get("monto") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Monto inválido"}), 400
    if monto <= 0:
        return jsonify({"error": "El monto debe ser mayor a 0"}), 400
    empresa = (d.get("empresa") or "ANIMUS").strip().upper()
    if empresa not in EMPRESAS_CAJA:
        return jsonify({"error": "Empresa inválida"}), 400
    conn = _db(); c = conn.cursor()
    saldo = float(c.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),0) "
        "FROM animus_caja_menor WHERE COALESCE(anulado,0)=0").fetchone()[0] or 0)
    if monto > saldo and not d.get("forzar"):
        return jsonify({"error": "No hay efectivo suficiente para consignar",
                        "saldo": round(saldo, 2), "puede_forzar": True}), 409
    fecha = (d.get("fecha") or _hoy_col().isoformat()).strip()
    cuenta = (d.get("cuenta") or "").strip()
    recibo, mov_id = registrar_movimiento_caja(
        c, tipo='egreso',
        concepto='Consignación a la cuenta' + ((' · ' + cuenta) if cuenta else ''),
        monto=monto, fecha=fecha, metodo='transferencia',
        referencia=cuenta, observaciones=(d.get("observaciones") or "").strip(),
        usuario=u, empresa=empresa, subtipo='traslado')
    audit_log(c, usuario=u, accion='CAJA_TRASLADO_CUENTA', tabla='animus_caja_menor',
              registro_id=mov_id,
              despues={'monto': monto, 'cuenta': cuenta, 'empresa': empresa, 'recibo': recibo},
              detalle='Consignados %s de la caja a la cuenta %s' % (monto, cuenta or '(sin detallar)'))
    conn.commit()
    return jsonify({"ok": True, "recibo_numero": recibo, "caja_mov_id": mov_id,
                    "saldo_antes": round(saldo, 2), "saldo_despues": round(saldo - monto, 2)})


@bp.route("/api/animus/caja", methods=["GET"])
def animus_caja_listar():
    """Lista movimientos de caja menor con KPIs y saldo."""
    u, err, code = _auth()
    if err: return err, code
    desde = (request.args.get("desde") or "").strip()
    tipo  = (request.args.get("tipo") or "").strip()
    q     = (request.args.get("q") or "").strip()

    conn = _db(); c = conn.cursor()
    sql = """
        SELECT id, fecha, tipo, concepto, monto, metodo, referencia,
               observaciones, registrado_por, fecha_creacion,
               COALESCE(recibo_numero,'') AS recibo_numero,
               COALESCE(anulado,0)        AS anulado,
               COALESCE(anulado_por,'')   AS anulado_por,
               COALESCE(anulado_motivo,'') AS anulado_motivo,
               COALESCE(anulado_at,'')    AS anulado_at
        FROM animus_caja_menor WHERE 1=1
    """
    params = []
    if desde:
        sql += " AND fecha >= ?"; params.append(desde)
    if tipo in ("ingreso", "egreso"):
        sql += " AND tipo = ?"; params.append(tipo)
    if q:
        sql += " AND (concepto LIKE ? OR referencia LIKE ? OR observaciones LIKE ? "
        sql += "      OR recibo_numero LIKE ?)"
        ql = f"%{q}%"; params += [ql, ql, ql, ql]
    sql += " ORDER BY fecha DESC, id DESC LIMIT 500"
    movs = [dict(r) for r in c.execute(sql, params).fetchall()]

    # KPIs globales (sin filtros) para no confundir.
    # El "hoy" de un movimiento de DINERO va en hora Colombia (M24): Render corre en UTC, así que
    # después de las 19:00 locales `datetime.now()` ya está en el día siguiente y los KPIs del día
    # aparecían vacíos mientras la caja seguía operando.
    hoy = _hoy_col().isoformat()
    mes = hoy[:7]
    # Un movimiento ANULADO no suma al saldo ni a los KPIs (sigue existiendo y se ve en la lista,
    # que es justamente el punto de anular en vez de borrar).
    kpis = c.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END), 0) as saldo_total,
          COALESCE(SUM(CASE WHEN tipo='ingreso' AND fecha=? THEN monto ELSE 0 END), 0) as ingreso_hoy,
          COALESCE(SUM(CASE WHEN tipo='egreso'  AND fecha=? THEN monto ELSE 0 END), 0) as egreso_hoy,
          COALESCE(SUM(CASE WHEN tipo='ingreso' AND substr(fecha,1,7)=? THEN monto ELSE 0 END), 0) as ingreso_mes,
          COALESCE(SUM(CASE WHEN tipo='egreso'  AND substr(fecha,1,7)=? THEN monto ELSE 0 END), 0) as egreso_mes,
          COUNT(*) as n_total
        FROM animus_caja_menor
        WHERE COALESCE(anulado,0) = 0
    """, (hoy, hoy, mes, mes)).fetchone()

    return jsonify({
        "ok": True,
        "movimientos": movs,
        "kpis": dict(kpis) if kpis else {},
    })


@bp.route("/api/animus/caja", methods=["POST"])
def animus_caja_registrar():
    """Registra un nuevo movimiento de caja (ingreso o egreso)."""
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json() or {}
    tipo = (d.get("tipo") or "").strip().lower()
    if tipo not in ("ingreso", "egreso"):
        return jsonify({"error": "tipo debe ser 'ingreso' o 'egreso'"}), 400
    concepto = (d.get("concepto") or "").strip()
    if not concepto:
        return jsonify({"error": "concepto requerido"}), 400
    monto, err = validate_money(d.get("monto"), allow_zero=False, field_name='monto')
    if err:
        return jsonify(err), 400
    # El "hoy" de un movimiento de dinero se ancla en Colombia, no en el UTC del server (M24).
    fecha = (d.get("fecha") or _hoy_col().isoformat()).strip()
    metodo = (d.get("metodo") or "efectivo").strip()
    referencia = (d.get("referencia") or "").strip()
    obs = (d.get("observaciones") or "").strip()

    conn = _db()
    c = conn.cursor()
    recibo, mov_id = registrar_movimiento_caja(
        c, tipo=tipo, concepto=concepto, monto=monto, fecha=fecha,
        metodo=metodo, referencia=referencia, observaciones=obs, usuario=u)
    try:
        audit_log(c, usuario=u, accion='ANIMUS_CAJA_MOV',
                  tabla='animus_caja_menor', registro_id=mov_id,
                  despues={'tipo': tipo, 'concepto': concepto[:120],
                            'monto': monto, 'metodo': metodo,
                            'fecha': fecha, 'recibo': recibo},
                  detalle=f"Caja ÁNIMUS · {recibo} · {tipo} · {concepto[:60]} · ${monto/1000:.0f}K")
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "id": mov_id, "recibo_numero": recibo})


@bp.route("/api/animus/caja/<int:mov_id>", methods=["DELETE"])
def animus_caja_eliminar(mov_id):
    """ANULA un movimiento de caja (no lo borra). ADMIN ONLY.

    Antes hacía `DELETE` de verdad, lo que contradecía al propio módulo: la caja existe para
    reemplazar los recibos sueltos SIN numeración, y un talonario del que se pueden arrancar
    hojas no prueba nada — el valor de numerar es justamente que el hueco se vea. Ahora el
    movimiento se conserva con su número de recibo, deja de sumar al saldo, y guarda quién lo
    anuló, cuándo y por qué. Es el mismo criterio que el resto del sistema con un registro ya
    emitido: se reversa, no se destruye.
    """
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin puede anular movimientos de caja"}), 403
    motivo = ((request.get_json(silent=True) or {}).get("motivo")
              or request.args.get("motivo") or "").strip()
    if not motivo:
        return jsonify({"error": "Indicá el motivo de la anulación (queda en el recibo)"}), 400
    conn = _db()
    c = conn.cursor()
    antes_row = c.execute(
        "SELECT tipo, concepto, monto, COALESCE(recibo_numero,''), COALESCE(anulado,0) "
        "FROM animus_caja_menor WHERE id=?", (mov_id,)
    ).fetchone()
    if not antes_row:
        return jsonify({"error": "Movimiento no encontrado"}), 404
    antes = {'tipo': antes_row[0], 'concepto': antes_row[1], 'monto': antes_row[2],
             'recibo': antes_row[3]}
    if int(antes_row[4] or 0):
        return jsonify({"error": "Ese recibo ya está anulado",
                        "recibo_numero": antes_row[3]}), 409
    # CAS: la condición de estado va en el WHERE · con 3 workers dos anulaciones concurrentes
    # pasarían ambas el chequeo de arriba y la segunda pisaría el motivo de la primera.
    c.execute("UPDATE animus_caja_menor SET anulado=1, anulado_por=?, anulado_motivo=?, "
              "anulado_at=? WHERE id=? AND COALESCE(anulado,0)=0",
              (u, motivo[:300], _now_col().strftime('%Y-%m-%d %H:%M:%S'), mov_id))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "Ese recibo ya está anulado"}), 409
    try:
        audit_log(c, usuario=u, accion='ANIMUS_CAJA_ANULAR',
                  tabla='animus_caja_menor', registro_id=mov_id,
                  antes=antes, despues={'anulado': 1, 'motivo': motivo[:300]},
                  detalle=f"Anuló recibo de caja {antes['recibo'] or ('id=%d' % mov_id)} "
                          f"({antes['tipo']} ${antes['monto']/1000:.0f}K) · {motivo[:80]}")
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "anulado": mov_id, "recibo_numero": antes['recibo']})


# ════════════════════════════════════════════════════════════════════
# CONTRAENTREGA — la plata que llega cuando entregan el pedido
# ════════════════════════════════════════════════════════════════════
# Sebastián 27-jul: "caja menor es toda la plata que llega por envíos contraentrega · en Shopify
# les ponen contraentrega · saber pedido tal, tanto valor, que marquen que sí ingresó esa plata,
# y saber en tiempo real cuánto ingresa".
#
# La marca la escribe una persona al crear el pedido, así que NO viene en un campo estructurado:
# va en la NOTA del pedido, y a veces como ETIQUETA. El medio de pago la trae solo cuando la
# tienda usa una pasarela COD. Se miran las TRES y el detector dice cuál fue la que matcheó —
# depender de una sola pierde pedidos en silencio, que es el peor modo de fallar acá.
#
# El patrón vive en `app_settings` para poder ajustarlo sin desplegar: si mañana empiezan a
# escribir "pago al recibir", se corrige desde la app y no con un deploy.

COD_PATRON_DEFAULT = (r'contra\s*-?\s*entrega|contraentrega|cash\s+on\s+delivery|\bcod\b'
                      r'|pago\s+al\s+recibir|pago\s+contra\s+entrega')


def _norm_txt(s):
    """Minúsculas y sin tildes: 'CONTRA-ENTREGA' y 'Contraentrega' son la misma marca."""
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(ch for ch in s if not unicodedata.combining(ch)).lower()


def cod_patron(conn):
    """El patrón configurable. Si quedó vacío o inválido, cae al default (nunca deja de detectar)."""
    try:
        row = conn.execute(
            "SELECT valor FROM app_settings WHERE clave='cod_patron'").fetchone()
        p = (row[0] if row else '') or ''
        if p.strip():
            re.compile(p)          # si no compila, mejor el default que quedarse sin detección
            return p.strip()
    except Exception:
        pass
    return COD_PATRON_DEFAULT


def es_contraentrega(nota, tags, gateway, patron=None, direccion=None):
    """¿Este pedido es contraentrega? Devuelve (bool, dónde matcheó).

    El "dónde" no es adorno: cuando alguien pregunte por qué un pedido entró (o no) a la caja de
    contraentrega, la respuesta tiene que ser verificable sin abrir el código.

    La DIRECCIÓN es la cuarta señal y resultó ser la principal (3-ago). Escriben cosas como
    "CONTRAENTREGA ENVIAR CON EL PROFE" en la dirección de envío; el buscador de Shopify las
    encuentra porque busca ahí, y por eso en Shopify se veían decenas y en EOS 4. `direccion`
    va como argumento con nombre para no correr `patron`, que ya era el cuarto posicional en
    todas las llamadas existentes.
    """
    rx = re.compile(patron or COD_PATRON_DEFAULT)
    for campo, valor in (('nota', nota), ('etiqueta', tags),
                         ('direccion', direccion), ('medio de pago', gateway)):
        if valor and rx.search(_norm_txt(valor)):
            return True, campo
    return False, ''


def _cod_pedidos(conn, desde=None, hasta=None, incluir_cobrados=True):
    """Los pedidos contraentrega del rango, con su estado de cobro.

    La detección se hace en Python y no en SQL a propósito: el patrón es una expresión regular
    configurable, y traducirla a LIKE encadenados la volvería otra regla distinta de la que el
    diagnóstico muestra (M5: el número que se ve tiene que ser el que decide). El rango de fechas
    acota el escaneo.
    """
    patron = cod_patron(conn)
    desde = desde or (_hoy_col() - timedelta(days=90)).isoformat()
    hasta = hasta or _hoy_col().isoformat()
    filas = conn.execute(
        """SELECT o.shopify_id, o.nombre, o.total, o.creado_en, o.ciudad,
                  COALESCE(o.nota,''), COALESCE(o.tags,''), COALESCE(o.gateway,''),
                  COALESCE(o.estado,''), COALESCE(o.estado_pago,''),
                  cc.id, cc.valor_recibido, cc.estado, cc.cobrado_por, cc.cobrado_at,
                  COALESCE(cc.observaciones,''), cc.caja_mov_id,
                  COALESCE(o.direccion,'')
             FROM animus_shopify_orders o
             LEFT JOIN animus_cod_cobros cc
                    ON cc.shopify_id = o.shopify_id AND cc.estado <> 'anulado'
            WHERE substr(COALESCE(o.creado_en,''),1,10) >= ?
              AND substr(COALESCE(o.creado_en,''),1,10) <= ?
              AND LOWER(COALESCE(o.estado,'')) <> 'cancelled'
            ORDER BY o.creado_en DESC, o.shopify_id DESC""",
        (desde, hasta)).fetchall()

    # Los BORRADORES son la otra mitad (3-ago). El pedido contraentrega se crea como borrador
    # y se completa recién cuando la plata entra, así que hasta ahora no existía para EOS.
    #
    # ANTI-DOBLE-COBRO: al completarse, el borrador genera una ORDEN con otro id, y el mismo
    # pedido físico quedaría en las dos fuentes. `order_id` guarda ese vínculo; acá se arma el
    # conjunto de órdenes que YA vienen de un borrador para no listarlas dos veces. Se prefiere
    # el borrador porque es donde está la marca que escribió la persona.
    borradores, ordenes_de_borrador = [], set()
    try:
        borradores = conn.execute(
            """SELECT b.shopify_id, b.nombre, b.total, b.creado_en, b.ciudad,
                      COALESCE(b.nota,''), COALESCE(b.tags,''), COALESCE(b.estado,''),
                      COALESCE(b.order_id,''),
                      COALESCE(b.direccion,''),
                      cc.id, cc.valor_recibido, cc.estado, cc.cobrado_por, cc.cobrado_at,
                      COALESCE(cc.observaciones,''), cc.caja_mov_id
                 FROM animus_shopify_borradores b
                 LEFT JOIN animus_cod_cobros cc
                        ON cc.shopify_id = b.shopify_id AND cc.estado <> 'anulado'
                WHERE substr(COALESCE(b.creado_en,''),1,10) >= ?
                  AND substr(COALESCE(b.creado_en,''),1,10) <= ?
                ORDER BY b.creado_en DESC, b.shopify_id DESC""",
            (desde, hasta)).fetchall()
        ordenes_de_borrador = {str(b[8]) for b in borradores if b[8]}
    except Exception as e:
        # La tabla puede no existir todavía (migración 407 sin aplicar). Se declara, no se
        # oculta: una lista sin borradores que se lea como completa contesta al revés (M100).
        log.warning('no pude leer los borradores de contraentrega: %s', e)

    out = []
    for f in filas:
        # esta orden nació de un borrador que ya está en la lista · no se cuenta dos veces
        if str(f[0]) in ordenes_de_borrador:
            continue
        ok, donde = es_contraentrega(f[5], f[6], f[7], patron, direccion=f[17])
        if not ok:
            continue
        cobrado = f[10] is not None
        if cobrado and not incluir_cobrados:
            continue
        esperado = float(f[2] or 0)
        recibido = float(f[11] or 0) if cobrado else 0.0
        out.append({
            'shopify_id': f[0], 'pedido': f[1] or '', 'valor_esperado': esperado,
            'fecha': (f[3] or '')[:10], 'ciudad': f[4] or '',
            'detectado_por': donde, 'nota': (f[5] or '')[:200],
            'entrega': f[8], 'estado_pago': f[9],
            'cobrado': cobrado, 'valor_recibido': recibido,
            'estado_cobro': f[12] or 'pendiente', 'cobrado_por': f[13] or '',
            'cobrado_at': f[14] or '', 'observaciones': f[15] or '',
            'caja_mov_id': f[16],
            'diferencia': round(recibido - esperado, 2) if cobrado else 0.0,
            # Cuántos días lleva esa plata en la calle. Sin esto, "esperado pendiente" es un
            # bulto: no distingue un pedido de ayer (normal) de uno de hace 45 días (esa plata
            # probablemente no vuelve, o la transportadora ya la consignó y nadie la registró).
            # Se deriva de la fecha del pedido, que ya está -- no hace falta ningún dato nuevo.
            'dias_en_calle': _dias_desde(f[3]) if not cobrado else None,
            'origen': 'orden',
        })

    for b in borradores:
        # El medio de pago no aplica: un borrador todavía no se pagó por ningún lado. Se miran
        # la nota y las etiquetas, que es donde la persona escribe la marca.
        ok, donde = es_contraentrega(b[5], b[6], '', patron, direccion=b[9])
        if not ok:
            continue
        cobrado = b[10] is not None
        if cobrado and not incluir_cobrados:
            continue
        esperado = float(b[2] or 0)
        recibido = float(b[11] or 0) if cobrado else 0.0
        out.append({
            'shopify_id': b[0], 'pedido': b[1] or '', 'valor_esperado': esperado,
            'fecha': (b[3] or '')[:10], 'ciudad': b[4] or '',
            'detectado_por': donde, 'nota': (b[5] or '')[:200],
            'entrega': b[7], 'estado_pago': 'borrador',
            'cobrado': cobrado, 'valor_recibido': recibido,
            'estado_cobro': b[12] or 'pendiente', 'cobrado_por': b[13] or '',
            'cobrado_at': b[14] or '', 'observaciones': b[15] or '',
            'caja_mov_id': b[16],
            'diferencia': round(recibido - esperado, 2) if cobrado else 0.0,
            'dias_en_calle': _dias_desde(b[3]) if not cobrado else None,
            # Se DECLARA de dónde salió: cuando alguien pregunte por qué un pedido está en la
            # caja, la respuesta tiene que ser verificable sin abrir el código.
            'origen': 'borrador',
        })

    out.sort(key=lambda p: (p['fecha'] or '', str(p['shopify_id'])), reverse=True)
    return out


def _dias_desde(fecha_txt):
    """Días entre una fecha ISO y hoy en Colombia (el server corre en UTC · M24).

    `date` NO está importado a nivel de módulo en este archivo (sólo `datetime` y
    `timedelta`), así que va local -- igual que el otro uso del archivo. Verificarlo antes
    de escribirlo es M78: un nombre que no está en scope es un NameError en producción.
    """
    from datetime import date as _date
    try:
        return (_hoy_col() - _date.fromisoformat((fecha_txt or '')[:10])).days
    except (ValueError, TypeError):
        return None


@bp.route("/api/animus/contraentrega", methods=["GET"])
def animus_cod_listar():
    """Pedidos contraentrega + cuánta plata se espera y cuánta entró de verdad."""
    u, err, code = _auth()
    if err: return err, code
    desde = (request.args.get("desde") or "").strip() or None
    hasta = (request.args.get("hasta") or "").strip() or None
    filtro = (request.args.get("estado") or "").strip().lower()

    conn = _db()
    pedidos = _cod_pedidos(conn, desde, hasta)
    hoy = _hoy_col().isoformat()
    mes = hoy[:7]

    # PAGADO EN SHOPIFY vs EN LA CALLE (3-ago · Sebastián: "quiero que se tome todo lo que
    # está pagado que diga contraentrega"). El flujo real es: el mensajero cobra y el pedido se
    # marca PAGADO en Shopify. Entonces un contraentrega `paid` NO es plata en la calle: es
    # plata que YA entró y a la caja le falta registrarla. Mezclarlos hacía que la pantalla
    # mostrara $411.200 "por cobrar" que Shopify ya daba por cobrados (M5).
    _pagado = lambda p: str(p.get('estado_pago') or '').lower() == 'paid'
    por_registrar = [p for p in pedidos if not p['cobrado'] and _pagado(p)]
    en_la_calle   = [p for p in pedidos if not p['cobrado'] and not _pagado(p)]
    kpis = {
        'por_registrar':      round(sum(p['valor_esperado'] for p in por_registrar), 2),
        'n_por_registrar':    len(por_registrar),
        'esperado_pendiente': round(sum(p['valor_esperado'] for p in en_la_calle), 2),
        'n_pendientes':       len(en_la_calle),
        'cobrado_hoy':        round(sum(p['valor_recibido'] for p in pedidos
                                        if p['cobrado'] and p['cobrado_at'][:10] == hoy), 2),
        'cobrado_mes':        round(sum(p['valor_recibido'] for p in pedidos
                                        if p['cobrado'] and p['cobrado_at'][:7] == mes), 2),
        'n_cobrados':         sum(1 for p in pedidos if p['cobrado']),
        # Descuadre = lo que se recibió de menos (o de más) respecto de lo que decía el pedido.
        'descuadre':          round(sum(p['diferencia'] for p in pedidos if p['cobrado']), 2),
        'n_descuadres':       sum(1 for p in pedidos if p['cobrado'] and abs(p['diferencia']) >= 1),
        # Plata VIEJA en la calle: más de 21 días sin entrar. Un contraentrega normal se cobra
        # en días; a las tres semanas, o la transportadora ya consignó y nadie lo registró, o
        # esa plata no vuelve. Sin separarlo, el total "pendiente" mezcla lo de ayer con lo
        # perdido y no se puede actuar sobre ninguno de los dos.
        'anejo_21d':          round(sum(p['valor_esperado'] for p in pedidos
                                        if not p['cobrado'] and (p.get('dias_en_calle') or 0) >= 21), 2),
        'n_anejos_21d':       sum(1 for p in pedidos
                                  if not p['cobrado'] and (p.get('dias_en_calle') or 0) >= 21),
    }
    if filtro == 'pendiente':
        pedidos = [p for p in pedidos if not p['cobrado']]
    elif filtro == 'cobrado':
        pedidos = [p for p in pedidos if p['cobrado']]
    elif filtro == 'descuadre':
        pedidos = [p for p in pedidos if p['cobrado'] and abs(p['diferencia']) >= 1]

    return jsonify({"ok": True, "pedidos": pedidos, "kpis": kpis,
                    "patron": cod_patron(conn),
                    "rango": {"desde": desde or (_hoy_col() - timedelta(days=90)).isoformat(),
                              "hasta": hasta or hoy}})


@bp.route("/api/animus/contraentrega/diagnostico", methods=["GET"])
def animus_cod_diagnostico():
    """Read-only: por qué se detecta (o no) la contraentrega, contra los datos REALES.

    Existe porque la marca la escribe una persona a mano y nadie puede afirmar de memoria cómo
    la escribe. Muestra cuántos pedidos hay, cuántos matchean y por cuál de las tres señales, y
    una muestra de las notas/etiquetas que NO matchearon — que es donde se ve si están usando una
    palabra que el patrón no contempla.
    """
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin"}), 403
    conn = _db()
    patron = cod_patron(conn)
    desde = (request.args.get("desde") or (_hoy_col() - timedelta(days=90)).isoformat())
    filas = conn.execute(
        "SELECT COALESCE(nota,''), COALESCE(tags,''), COALESCE(gateway,''), nombre, "
        "       COALESCE(total,0), LOWER(COALESCE(estado_pago,'')), COALESCE(direccion,'') "
        "FROM animus_shopify_orders "
        "WHERE substr(COALESCE(creado_en,''),1,10) >= ? "
        "  AND LOWER(COALESCE(estado,'')) <> 'cancelled'", (desde,)).fetchall()
    por_señal = {'nota': 0, 'etiqueta': 0, 'direccion': 0, 'medio de pago': 0}
    sin_match, con_texto = [], 0
    # Reparto REAL de etiquetas y medios de pago, con su plata. Es lo único que contesta "¿con
    # qué palabra la escriben?": una MUESTRA de 25 pedidos no sirve porque los más recientes
    # pueden ser todos del mismo canal y esconder justo el que se busca (pasó · los 25 que
    # devolvía eran todos de Mercado Pago, o sea pagos en línea, y con eso era imposible ver
    # si existe una etiqueta de contraentrega).
    tag_n, tag_v = {}, {}
    gw_n, gw_v = {}, {}
    # ¿La plata de esos pedidos YA entró? Es lo que decide si una etiqueta es contraentrega,
    # y no hace falta que nadie se acuerde: Shopify guarda el estado de pago de cada pedido.
    # Una etiqueta cuyos pedidos están casi todos SIN PAGAR es plata en la calle (contraentrega);
    # una cuyos pedidos están pagados es plata que ya entró por otro lado y NO va a esta caja
    # -- meterla ahí haría que el saldo diga que hay efectivo que no existe.
    tag_sin_pagar, gw_sin_pagar = {}, {}
    SIN_PAGAR = ('pending', 'authorized', 'partially_paid', '')
    # Contar por separado CUÁNTOS traen nota, etiqueta y medio de pago. La primera versión sólo
    # decía "con nota o etiqueta", y como casi todos los pedidos traen etiquetas de transportadora
    # ('CM: ENTREGADA', 'Facturado'), ese número daba 7.233 y no permitía ver que las NOTAS eran
    # otra cosa. Un diagnóstico que agrega dos señales distintas en un solo contador no sirve para
    # decidir cuál de las dos está fallando.
    con_nota = con_tags = con_gw = 0
    notas_reales = []      # muestra de notas NO vacías, matcheen o no: acá se ve cómo la escriben
    for nota, tags, gw, nombre, _total, _pago, _dir in filas:
        _n, _t, _g = (nota or '').strip(), (tags or '').strip(), (gw or '').strip()
        _v = float(_total or 0)
        _impago = 1 if (_pago or '').strip() in SIN_PAGAR else 0
        for _tag in _t.split(','):
            _tag = _tag.strip()
            if _tag:
                tag_n[_tag] = tag_n.get(_tag, 0) + 1
                tag_v[_tag] = tag_v.get(_tag, 0.0) + _v
                tag_sin_pagar[_tag] = tag_sin_pagar.get(_tag, 0) + _impago
        if _g:
            gw_n[_g] = gw_n.get(_g, 0) + 1
            gw_v[_g] = gw_v.get(_g, 0.0) + _v
            gw_sin_pagar[_g] = gw_sin_pagar.get(_g, 0) + _impago
        if _n:
            con_nota += 1
            if len(notas_reales) < 30:
                notas_reales.append({'pedido': nombre or '', 'nota': _n[:160]})
        if _t:
            con_tags += 1
        if _g:
            con_gw += 1
        if _n or _t:
            con_texto += 1
        ok, donde = es_contraentrega(nota, tags, gw, patron, direccion=_dir)
        if ok:
            por_señal[donde] += 1
        elif (_n or _t) and len(sin_match) < 25:
            sin_match.append({'pedido': nombre or '', 'nota': _n[:120],
                              'etiquetas': _t[:120], 'medio_pago': _g[:60]})
    return jsonify({
        "ok": True, "patron": patron, "desde": desde,
        "pedidos_en_rango": len(filas),
        "con_nota_o_etiqueta": con_texto,
        # Desglosado: sin esto no se distingue "no escriben la nota" de "la escriben distinto".
        "con_nota": con_nota,
        "con_etiquetas": con_tags,
        "con_medio_pago": con_gw,
        "muestra_notas_reales": notas_reales,
        "detectados": sum(por_señal.values()),
        "por_señal": por_señal,
        # Si `detectados` es 0 pero `con_nota_o_etiqueta` no lo es, la respuesta está acá:
        # se está escribiendo la marca de una forma que el patrón no contempla.
        "muestra_sin_match": sin_match,
        # El reparto completo, ordenado por cuántos pedidos lleva cada una. Acá se elige la
        # etiqueta mirando números (cuántos pedidos y cuánta plata) en vez de recordarla. Las
        # que aparecen una sola vez son por-pedido (número de factura, guía) y quedan al final.
        # `sin_pagar` es la columna que DECIDE: una etiqueta cuyos pedidos estan casi todos sin
        # pagar es plata en la calle; una cuyos pedidos ya estan pagados no va a esta caja.
        "etiquetas": [{"valor": k, "pedidos": tag_n[k], "monto": round(tag_v[k], 2),
                       "sin_pagar": tag_sin_pagar.get(k, 0),
                       "pct_sin_pagar": round(100.0 * tag_sin_pagar.get(k, 0) / tag_n[k]),
                       "detecta": bool(es_contraentrega(None, k, None, patron)[0])}
                      for k in sorted(tag_n, key=lambda x: -tag_n[x])[:60]],
        "etiquetas_distintas": len(tag_n),
        "medios_pago": [{"valor": k, "pedidos": gw_n[k], "monto": round(gw_v[k], 2),
                         "sin_pagar": gw_sin_pagar.get(k, 0),
                         "pct_sin_pagar": round(100.0 * gw_sin_pagar.get(k, 0) / gw_n[k]),
                         "detecta": bool(es_contraentrega(None, None, k, patron)[0])}
                        for k in sorted(gw_n, key=lambda x: -gw_n[x])[:30]],
        "como_ajustar": "PUT /api/animus/contraentrega/patron con {patron: '...'} (admin · sin deploy)",
    })


def sincronizar_borradores(conn, *, dias=120, paginas_max=12, presupuesto_seg=45):
    """Trae los BORRADORES de Shopify a su propia tabla. Devuelve un resumen.

    Por qué existe: los pedidos contraentrega se crean como borrador y se completan recién
    cuando la plata entra. El sync de EOS lee `orders.json`, así que hasta hoy esos pedidos no
    existían para el sistema -- de 7.032 órdenes el detector hallaba 4, y no era el patrón.

    Por qué en tabla PROPIA y no en `animus_shopify_orders`: esa tabla la leen 10 blueprints
    para calcular la velocidad de venta y planear producción. Un borrador NO es una venta
    todavía; meterlo ahí inflaría la demanda y haría fabricar de más.

    `order_id` es el anti-doble-cobro: al completarse, el borrador genera una orden con OTRO
    id, así que el mismo pedido físico aparecería en las dos fuentes y se podría cobrar dos
    veces. Guardar el vínculo permite excluir la orden si el borrador ya se cobró.
    """
    res = {'ok': False, 'vistos': 0, 'guardados': 0, 'paginas': 0,
           'se_corto_por': None, 'error': None}
    try:
        from shopify_client import _get_shopify_config
        from http_helpers import fetch_with_retry
    except Exception as e:
        res['error'] = 'cliente de Shopify no disponible: %s' % e
        return res
    token, shop = _get_shopify_config(conn)
    if not token or not shop:
        res['error'] = 'Shopify no configurado (shopify_token/shopify_shop)'
        return res

    import time
    t0 = time.monotonic()
    ahora = _now_col().strftime('%Y-%m-%d %H:%M:%S')
    # ACOTADO POR FECHA a propósito. Shopify devuelve los borradores del más VIEJO al más nuevo,
    # y hay más de 1.500 abiertos desde 2023 (quedaron sin completar y nadie los cerró). Sin
    # este filtro el presupuesto de tiempo se consume leyendo borradores de hace dos años y
    # NUNCA se llega a los de esta semana -- que son justo los que hay que cobrar. Medido: la
    # primera lectura se cortó en la página 6, toda en 2023-2024.
    desde_iso = (_hoy_col() - timedelta(days=dias)).strftime('%Y-%m-%dT00:00:00Z')
    url = ("https://%s/admin/api/2024-01/draft_orders.json?limit=250&updated_at_min=%s"
           % (shop, desde_iso))
    c = conn.cursor()
    try:
        while url and res['paginas'] < paginas_max:
            # Presupuesto de pared y timeout de socket (M92): un loop de red sin tope puede
            # retener un worker hasta que gunicorn lo mate, y eso tumba la app entera.
            if time.monotonic() - t0 > presupuesto_seg:
                res['se_corto_por'] = 'presupuesto de tiempo (%ss)' % presupuesto_seg
                break
            req = urllib.request.Request(url, headers={'X-Shopify-Access-Token': token})
            with fetch_with_retry(req, timeout=20, max_intentos=2) as r:
                body = r.read()
                link = r.headers.get('Link', '') or ''
            for d in (json.loads(body).get('draft_orders') or []):
                res['vistos'] += 1
                sid = str(d.get('id') or '').strip()
                if not sid:
                    continue
                addr = d.get('shipping_address') or d.get('billing_address') or {}
                _dir_b = ' '.join(x for x in (addr.get('address1') or '',
                                              addr.get('address2') or '',
                                              addr.get('company') or '') if x).strip()
                oid = d.get('order_id')
                # UPSERT con SOLO las columnas de este sync (M108): si otro proceso escribe
                # esta tabla mañana, ninguno puede borrar lo del otro.
                c.execute(
                    """INSERT INTO animus_shopify_borradores
                       (shopify_id, nombre, total, moneda, estado, nota, tags, ciudad,
                        creado_en, actualizado_en, order_id, sincronizado_at, direccion)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT (shopify_id) DO UPDATE SET
                         nombre=excluded.nombre, total=excluded.total, estado=excluded.estado,
                         nota=excluded.nota, tags=excluded.tags, ciudad=excluded.ciudad,
                         actualizado_en=excluded.actualizado_en, order_id=excluded.order_id,
                         sincronizado_at=excluded.sincronizado_at,
                         direccion=excluded.direccion""",
                    (sid, (d.get('name') or '').strip(), float(d.get('total_price') or 0),
                     (d.get('currency') or 'COP'), (d.get('status') or '').strip(),
                     (d.get('note') or ''), (d.get('tags') or ''),
                     (addr.get('city') or ''), (d.get('created_at') or '')[:19],
                     (d.get('updated_at') or '')[:19],
                     (str(oid) if oid else None), ahora, _dir_b))
                res['guardados'] += 1
            res['paginas'] += 1
            url = None
            for parte in link.split(','):
                if 'rel="next"' in parte and '<' in parte:
                    url = parte.split('<', 1)[1].split('>', 1)[0]
                    break
        conn.commit()
        res['ok'] = True
    except Exception as e:
        conn.rollback()
        res['error'] = 'Shopify no respondió: %s' % e
    return res


@bp.route("/api/animus/contraentrega/importar-pagados", methods=["GET", "POST"])
def animus_cod_importar_pagados():
    """Asienta en caja las contraentregas que Shopify YA da por pagadas.

    Sebastián 3-ago: "quiero que se tome todo lo que está pagado que diga contraentrega".
    El flujo real es ese: el mensajero cobra y el pedido se marca PAGADO en Shopify. Los 4
    contraentrega detectados están los 4 en `paid`, así que esa plata YA entró y lo único que
    faltaba era registrarla con su recibo -- pedirle a alguien que le diera "Sí entró" uno por
    uno era pedirle que repitiera un hecho que Shopify ya tiene.

    GET = vista previa (no escribe nada). POST = aplica.

    NO inventa el monto: usa el total del pedido, que es lo que Shopify dice que se pagó. Y va
    por el MISMO camino que el cobro manual (`registrar_movimiento_caja` + `animus_cod_cobros`),
    así que comparte el correlativo de recibo y el UNIQUE que impide cobrar dos veces -- dos
    numeradores para la misma caja serían dos series que se pisan.
    """
    u, err, code = _auth()
    if err: return err, code

    conn = _db(); c = conn.cursor()
    desde = (request.args.get("desde") or "").strip() or None
    hasta = (request.args.get("hasta") or "").strip() or None
    candidatos = [p for p in _cod_pedidos(conn, desde, hasta)
                  if not p['cobrado'] and str(p.get('estado_pago') or '').lower() == 'paid']

    if request.method == "GET":
        return jsonify({
            "ok": True, "n": len(candidatos),
            "monto": round(sum(p['valor_esperado'] for p in candidatos), 2),
            # La MISMA lista que se va a aplicar, no un recuento aparte: si la previa contara
            # con un filtro distinto del que escribe, mostraría un número y haría otro (M101).
            "pedidos": [{"pedido": p['pedido'], "fecha": p['fecha'],
                         "valor": p['valor_esperado'], "origen": p['origen'],
                         "marca": p['detectado_por']} for p in candidatos],
        })

    fecha_hoy = _hoy_col().isoformat()
    hechos, saltados = [], []
    for p in candidatos:
        sid = str(p['shopify_id'])
        try:
            c.execute("""INSERT INTO animus_cod_cobros
                  (shopify_id, pedido, valor_esperado, valor_recibido, estado,
                   cobrado_por, cobrado_at, observaciones)
                  VALUES (?,?,?,?,?,?,?,?)""",
                (sid, p['pedido'], p['valor_esperado'], p['valor_esperado'], 'cobrado', u,
                 _now_col().strftime('%Y-%m-%d %H:%M:%S'),
                 'Importado: Shopify lo da por pagado'))
        except sqlite3.IntegrityError:
            # Ya estaba cobrado por otro camino · no es un error, es la garantía funcionando
            saltados.append(p['pedido'])
            continue
        cobro_id = c.lastrowid
        recibo, mov_id = registrar_movimiento_caja(
            c, tipo='ingreso',
            concepto='Contraentrega %s' % p['pedido'],
            monto=p['valor_esperado'],
            # La fecha del HECHO es la del pedido, no la de hoy: si no, todo lo viejo aterriza
            # en el mes en curso y el período contable queda mal (M106).
            fecha=(p['fecha'] or fecha_hoy), metodo='efectivo',
            referencia=sid,
            observaciones='Cobro contraentrega · Shopify lo da por pagado', usuario=u)
        c.execute("UPDATE animus_cod_cobros SET caja_mov_id=? WHERE id=?", (mov_id, cobro_id))
        audit_log(c, usuario=u, accion='ANIMUS_COD_IMPORTAR_PAGADO',
                  tabla='animus_cod_cobros', registro_id=cobro_id,
                  despues={'pedido': p['pedido'], 'monto': p['valor_esperado'],
                           'recibo': recibo},
                  detalle='Contraentrega %s asentada en caja · recibo %s (Shopify: pagado)'
                          % (p['pedido'], recibo))
        hechos.append({'pedido': p['pedido'], 'recibo': recibo,
                       'monto': p['valor_esperado']})
    conn.commit()
    return jsonify({"ok": True, "registrados": len(hechos),
                    "monto": round(sum(h['monto'] for h in hechos), 2),
                    "ya_estaban": saltados, "detalle": hechos})


@bp.route("/api/animus/contraentrega/borradores/sync", methods=["POST"])
def animus_cod_borradores_sync():
    """Trae los borradores de Shopify (admin). Idempotente: se puede repetir sin duplicar."""
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin"}), 403
    conn = _db()
    res = sincronizar_borradores(conn)
    if not res['ok']:
        return jsonify({"error": res['error'] or 'no se pudo sincronizar', **res}), 502
    audit_log(None, usuario=u, accion='ANIMUS_BORRADORES_SYNC',
              tabla='animus_shopify_borradores', registro_id=0,
              despues={'vistos': res['vistos'], 'guardados': res['guardados']},
              detalle='Sync de borradores de Shopify · %d vistos' % res['vistos'])
    return jsonify({"ok": True, **res})


@bp.route("/api/animus/contraentrega/borradores", methods=["GET"])
def animus_cod_borradores():
    """Read-only: ¿hay contraentregas viviendo como BORRADOR en Shopify?

    Punto ciego encontrado el 3-ago: el sync de EOS lee `orders.json` y NUNCA `draft_orders.json`
    (cero referencias en todo el repo). Un borrador es otro recurso: existe en Shopify, tiene su
    nota y sus etiquetas, y **no aparece en orders hasta que alguien lo completa**. Si el flujo de
    contraentrega es "creo el borrador, lo despacho, lo cobro y recién ahí lo marco pagado",
    entonces esos pedidos son invisibles para EOS por construcción -- y la caja no puede estar
    completa por más que se afine el patrón.

    Esto NO sincroniza nada: pregunta, cuenta y devuelve. Decidir si los borradores entran a la
    caja es de negocio (un borrador todavía no es una venta), así que primero se mira el tamaño.
    """
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin"}), 403

    conn = _db()
    patron = cod_patron(conn)
    try:
        from shopify_client import _get_shopify_config
        from http_helpers import fetch_with_retry
    except Exception as e:
        return jsonify({"error": "no pude cargar el cliente de Shopify: %s" % e}), 500
    token, shop = _get_shopify_config(conn)
    if not token or not shop:
        return jsonify({"error": "Shopify no configurado"}), 400

    # Presupuesto de pared + tope de páginas (M92): esto corre en un request y no puede
    # acercarse al timeout de gunicorn. Si se corta, se DECLARA (M100) -- una lista parcial
    # que se lea como total contestaría la pregunta al revés.
    import time
    t0 = time.monotonic()
    # Acotado por fecha: Shopify los devuelve del más VIEJO al más nuevo y hay 1.500+ abiertos
    # desde 2023. Sin el filtro, el presupuesto se gasta leyendo borradores de hace dos años y
    # el informe habla de 2023 mientras uno cree que habla de esta semana.
    _dias = max(1, min(int(request.args.get('dias') or 120), 730))
    _desde_iso = (_hoy_col() - timedelta(days=_dias)).strftime('%Y-%m-%dT00:00:00Z')
    url = ("https://%s/admin/api/2024-01/draft_orders.json?limit=250&updated_at_min=%s"
           % (shop, _desde_iso))
    vistos, con_nota, con_tags, detectados = 0, 0, 0, 0
    muestra, tag_n, por_señal = [], {}, {'nota': 0, 'etiqueta': 0, 'direccion': 0,
                                        'medio de pago': 0}
    paginas, corto = 0, None
    try:
        while url and paginas < 8:
            if time.monotonic() - t0 > 25:
                corto = "presupuesto de tiempo (25s)"
                break
            req = urllib.request.Request(url, headers={'X-Shopify-Access-Token': token})
            with fetch_with_retry(req, timeout=20, max_intentos=2) as r:
                body = r.read()
                link = r.headers.get('Link', '') or ''
            for d in (json.loads(body).get('draft_orders') or []):
                vistos += 1
                nota = (d.get('note') or '').strip()
                tags = (d.get('tags') or '').strip()
                # La dirección se arma acá, con el `d` de ESTE loop: la del sync vive en otra
                # función y usarla sería un NameError en producción (M78).
                _ad = d.get('shipping_address') or d.get('billing_address') or {}
                direccion = ' '.join(x for x in (_ad.get('address1') or '',
                                                 _ad.get('address2') or '',
                                                 _ad.get('company') or '') if x).strip()
                if nota:
                    con_nota += 1
                if tags:
                    con_tags += 1
                for t in tags.split(','):
                    t = t.strip()
                    if t:
                        tag_n[t] = tag_n.get(t, 0) + 1
                ok, donde = es_contraentrega(nota, tags, '', patron, direccion=direccion)
                if ok:
                    detectados += 1
                    por_señal[donde] += 1
                if len(muestra) < 25 and (nota or tags):
                    muestra.append({'nombre': d.get('name') or '',
                                    'total': d.get('total_price') or '0',
                                    'nota': nota[:120], 'etiquetas': tags[:120],
                                    'creado': (d.get('created_at') or '')[:10]})
            paginas += 1
            url = None
            for parte in link.split(','):
                if 'rel="next"' in parte and '<' in parte:
                    url = parte.split('<', 1)[1].split('>', 1)[0]
                    break
    except Exception as e:
        return jsonify({"error": "Shopify no respondió: %s" % e,
                        "borradores_vistos": vistos}), 502

    return jsonify({
        "ok": True, "patron": patron,
        "dias": _dias, "desde": _desde_iso[:10],
        "borradores_abiertos": vistos,
        "paginas_leidas": paginas,
        # Si esto NO es None, la respuesta es PARCIAL: un cero acá abajo no probaría nada.
        "se_corto_por": corto,
        "con_nota": con_nota, "con_etiquetas": con_tags,
        "detectados_como_contraentrega": detectados,
        "por_señal": por_señal,
        "etiquetas": [{"valor": k, "borradores": tag_n[k]}
                      for k in sorted(tag_n, key=lambda x: -tag_n[x])[:40]],
        "muestra": muestra,
        "para_que_sirve": ("Si aca aparecen contraentregas, el patron no es el problema: el sync "
                           "de EOS solo lee orders.json y nunca draft_orders.json"),
    })


@bp.route("/api/animus/contraentrega/patron", methods=["PUT"])
def animus_cod_patron_set():
    """Ajusta el patrón de detección sin desplegar (admin)."""
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin"}), 403
    nuevo = ((request.get_json(silent=True) or {}).get("patron") or "").strip()
    if not nuevo:
        return jsonify({"error": "patrón vacío · dejaría la caja de contraentrega sin detectar nada"}), 400
    try:
        re.compile(nuevo)
    except re.error as e:
        return jsonify({"error": "expresión inválida: %s" % e}), 400
    conn = _db(); c = conn.cursor()
    antes = cod_patron(conn)
    c.execute("INSERT INTO app_settings (clave, valor) VALUES ('cod_patron', ?) "
              "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (nuevo,))
    audit_log(c, usuario=u, accion='ANIMUS_COD_PATRON', tabla='app_settings',
              registro_id='cod_patron', antes={'patron': antes}, despues={'patron': nuevo},
              detalle='Cambió el patrón de detección de contraentrega')
    conn.commit()
    return jsonify({"ok": True, "patron": nuevo})


@bp.route("/api/animus/contraentrega/<path:shopify_id>/cobrar", methods=["POST"])
def animus_cod_cobrar(shopify_id):
    """Marca que la plata de ese pedido SÍ entró, y la asienta en caja con su recibo."""
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json(silent=True) or {}
    conn = _db(); c = conn.cursor()

    row = c.execute(
        "SELECT nombre, total, COALESCE(nota,''), COALESCE(tags,''), COALESCE(gateway,''), "
        "       COALESCE(creado_en,''), COALESCE(direccion,'') FROM animus_shopify_orders "
        "WHERE shopify_id=?",
        (str(shopify_id),)).fetchone()
    es_borrador = False
    if not row:
        # Puede ser un BORRADOR (3-ago): el pedido contraentrega se crea así y se completa
        # recién cuando la plata entra, así que la mayoría se cobra estando todavía en
        # borrador. Sin esta rama, cobrarlos daba 404 y la caja no se podía usar.
        try:
            row = c.execute(
                "SELECT nombre, total, COALESCE(nota,''), COALESCE(tags,''), '', "
                "       COALESCE(creado_en,''), COALESCE(direccion,'') "
                "FROM animus_shopify_borradores WHERE shopify_id=?",
                (str(shopify_id),)).fetchone()
            es_borrador = row is not None
        except Exception as e:
            log.warning('no pude buscar el borrador %s: %s', shopify_id, e)
    if not row:
        return jsonify({"error": "Ese pedido no está en EOS · corré el sync de Shopify"}), 404
    ok_cod, _donde = es_contraentrega(row[2], row[3], row[4], cod_patron(conn),
                                     direccion=(row[6] if len(row) > 6 else ''))
    if not ok_cod:
        # No es un capricho: cobrar en esta caja un pedido que NO es contraentrega mete plata que
        # ya entró por la pasarela y descuadra el saldo contra la realidad.
        return jsonify({"error": "Ese pedido no está marcado como contraentrega",
                        "pedido": row[0] or ''}), 409

    esperado = float(row[1] or 0)
    recibido = d.get("valor_recibido")
    recibido = esperado if recibido in (None, '') else float(recibido)
    if recibido < 0:
        return jsonify({"error": "El valor recibido no puede ser negativo"}), 400
    obs = (d.get("observaciones") or "").strip()
    dif = round(recibido - esperado, 2)
    if abs(dif) >= 1 and not obs:
        # Un descuadre sin explicación es justo el dato que después nadie puede reconstruir.
        return jsonify({"error": "Recibiste %s y el pedido dice %s · explicá la diferencia"
                                 % (f'{recibido:,.0f}', f'{esperado:,.0f}')}), 400
    estado = 'descuadre' if abs(dif) >= 1 else 'cobrado'
    fecha = (d.get("fecha") or _hoy_col().isoformat()).strip()
    pedido = row[0] or str(shopify_id)

    # El UNIQUE de shopify_id es lo que impide cobrar dos veces el mismo pedido: el chequeo
    # previo no sirve con 3 workers (los dos pasarían). Se intenta y se traduce el choque.
    try:
        c.execute("""INSERT INTO animus_cod_cobros
              (shopify_id, pedido, valor_esperado, valor_recibido, estado,
               cobrado_por, cobrado_at, observaciones)
              VALUES (?,?,?,?,?,?,?,?)""",
            (str(shopify_id), pedido, esperado, recibido, estado, u,
             _now_col().strftime('%Y-%m-%d %H:%M:%S'), obs))
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "Ese pedido ya está cobrado", "pedido": pedido}), 409
    cobro_id = c.lastrowid

    # La plata entra a caja por el MISMO camino que un ingreso manual: mismo correlativo, mismo
    # recibo. Dos numeradores distintos para la misma caja serían dos series que se pisan.
    # De dónde salió queda escrito en el recibo: un borrador y una orden son dos registros
    # distintos de Shopify, y cuando alguien audite la caja tiene que poder rastrearlo.
    recibo, mov_id = registrar_movimiento_caja(
        c, tipo='ingreso',
        concepto='Contraentrega %s%s' % (pedido, ' (borrador)' if es_borrador else ''),
        monto=recibido, fecha=fecha, metodo='efectivo',
        referencia=str(shopify_id),
        observaciones=(obs or ('Cobro de pedido contraentrega'
                               + (' · creado como borrador en Shopify' if es_borrador else ''))),
        usuario=u)
    c.execute("UPDATE animus_cod_cobros SET caja_mov_id=? WHERE id=?", (mov_id, cobro_id))

    audit_log(c, usuario=u, accion='ANIMUS_COD_COBRAR', tabla='animus_cod_cobros',
              registro_id=cobro_id,
              despues={'pedido': pedido, 'esperado': esperado, 'recibido': recibido,
                       'estado': estado, 'recibo': recibo},
              detalle='Contraentrega %s cobrada · recibo %s · %s' % (pedido, recibo, estado))
    conn.commit()
    return jsonify({"ok": True, "pedido": pedido, "recibo_numero": recibo,
                    "estado": estado, "diferencia": dif, "caja_mov_id": mov_id})


@bp.route("/api/animus/contraentrega/<path:shopify_id>/anular", methods=["POST"])
def animus_cod_anular(shopify_id):
    """Deshace un cobro mal marcado: anula el cobro Y su recibo de caja, sin borrar ninguno."""
    u, err, code = _auth()
    if err: return err, code
    if u not in ADMIN_USERS:
        return jsonify({"error": "Solo admin puede anular un cobro"}), 403
    motivo = ((request.get_json(silent=True) or {}).get("motivo") or "").strip()
    if not motivo:
        return jsonify({"error": "Indicá el motivo de la anulación"}), 400
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT id, pedido, caja_mov_id FROM animus_cod_cobros "
                    "WHERE shopify_id=? AND estado <> 'anulado'", (str(shopify_id),)).fetchone()
    if not row:
        return jsonify({"error": "Ese pedido no tiene un cobro activo"}), 404
    # CAS: la condición de estado va en el WHERE, para que dos anulaciones a la vez no dejen
    # el recibo de caja anulado dos veces con motivos distintos.
    if c.execute("UPDATE animus_cod_cobros SET estado='anulado', "
                 "observaciones = COALESCE(observaciones,'') || ' · ANULADO: ' || ? "
                 "WHERE id=? AND estado <> 'anulado'", (motivo[:200], row[0])).rowcount != 1:
        conn.rollback()
        return jsonify({"error": "Ese cobro ya está anulado"}), 409
    if row[2]:
        c.execute("UPDATE animus_caja_menor SET anulado=1, anulado_por=?, anulado_motivo=?, "
                  "anulado_at=? WHERE id=? AND COALESCE(anulado,0)=0",
                  (u, ('Cobro contraentrega anulado: ' + motivo)[:300],
                   _now_col().strftime('%Y-%m-%d %H:%M:%S'), row[2]))
    audit_log(c, usuario=u, accion='ANIMUS_COD_ANULAR', tabla='animus_cod_cobros',
              registro_id=row[0], despues={'motivo': motivo[:200]},
              detalle='Anuló el cobro contraentrega de %s · %s' % (row[1], motivo[:80]))
    conn.commit()
    return jsonify({"ok": True, "pedido": row[1]})


# ════════════════════════════════════════════════════════════════════
# INVENTARIO CÍCLICO — Conteo físico vs Shopify
# ════════════════════════════════════════════════════════════════════
# Daniela cuenta físicamente cada producto de la tienda y registra:
#   - cantidad_shopify: lo que dice Shopify (sync más reciente o ventas)
#   - cantidad_fisica: lo que ella cuenta
#   - diferencia: calculada (puede ser negativa = falta, positiva = sobrante)
#   - explicacion: por qué la diferencia (devolución no registrada,
#     producto roto, regalo, robo sospechoso, error de carga, etc.)
#
# El backend deriva cantidad_shopify de animus_shopify_orders sumando
# unidades vendidas + un baseline de stock (que en el futuro vendrá de
# webhook de Shopify inventory). Por ahora: SUM(unidades vendidas en el
# periodo desde último conteo).

@bp.route("/api/animus/inventario-ciclico/skus", methods=["GET"])
def animus_inv_ciclico_skus():
    """Devuelve los SKUs vendidos en Shopify con cantidad acumulada para
    que Daniela elija cuál contar. Ordenados por último vendido."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    c = conn.cursor()
    # Extraemos SKUs únicos de animus_shopify_orders.sku_items (JSON).
    # sku_items es un JSON: [{"sku":"X","qty":1}, ...] — parseamos en Python.
    rows = c.execute("""
        SELECT sku_items, unidades_total, creado_en
        FROM animus_shopify_orders
        WHERE sku_items IS NOT NULL AND sku_items != ''
        ORDER BY creado_en DESC
        LIMIT 500
    """).fetchall()

    sku_stats = {}  # sku → {n_orders, uds_vendidas, ult_venta}
    for r in rows:
        try:
            items = json.loads(r["sku_items"]) if r["sku_items"] else []
        except Exception:
            continue
        for it in items:
            sku = (it.get("sku") or "").strip().upper()
            qty = float(it.get("qty") or 0)
            if not sku:
                continue
            if sku not in sku_stats:
                sku_stats[sku] = {
                    "sku": sku,
                    "n_orders": 0,
                    "uds_vendidas": 0,
                    "ultima_venta": r["creado_en"],
                }
            sku_stats[sku]["n_orders"] += 1
            sku_stats[sku]["uds_vendidas"] += qty
            # ultima_venta: como rows están DESC ya, el primer hit es el más reciente
            if not sku_stats[sku]["ultima_venta"]:
                sku_stats[sku]["ultima_venta"] = r["creado_en"]

    # Anexar último conteo si existe
    for sku in list(sku_stats.keys()):
        last = c.execute("""
            SELECT cantidad_fisica, diferencia, fecha_conteo
            FROM animus_conteos_ciclicos
            WHERE sku = ? ORDER BY fecha_conteo DESC LIMIT 1
        """, (sku,)).fetchone()
        if last:
            d = dict(last)
            sku_stats[sku]["ultimo_conteo"] = {
                "cantidad_fisica": d["cantidad_fisica"],
                "diferencia": d["diferencia"],
                "fecha": d["fecha_conteo"],
            }
        else:
            sku_stats[sku]["ultimo_conteo"] = None

    items = sorted(
        sku_stats.values(),
        key=lambda x: x.get("ultima_venta") or "",
        reverse=True,
    )
    return jsonify({"ok": True, "skus": items})


@bp.route("/api/animus/inventario-ciclico", methods=["GET"])
def animus_inv_ciclico_listar():
    """Historial de conteos cíclicos con filtros."""
    u, err, code = _auth()
    if err: return err, code
    sku    = (request.args.get("sku") or "").strip().upper()
    desde  = (request.args.get("desde") or "").strip()

    conn = _db(); c = conn.cursor()
    sql = """
        SELECT id, sku, producto_nombre, fecha_conteo,
               cantidad_shopify, cantidad_fisica, diferencia,
               explicacion, registrado_por, fecha_creacion
        FROM animus_conteos_ciclicos WHERE 1=1
    """
    params = []
    if sku:
        sql += " AND UPPER(sku) = ?"; params.append(sku)
    if desde:
        sql += " AND fecha_conteo >= ?"; params.append(desde)
    sql += " ORDER BY fecha_conteo DESC, id DESC LIMIT 300"
    conteos = [dict(r) for r in c.execute(sql, params).fetchall()]

    # KPIs: total con diferencia, SKUs con problemas recurrentes
    kpis = c.execute("""
        SELECT
          COUNT(*) as n_total,
          COALESCE(SUM(CASE WHEN diferencia != 0 THEN 1 ELSE 0 END), 0) as n_con_dif,
          COALESCE(SUM(CASE WHEN diferencia < 0 THEN -diferencia ELSE 0 END), 0) as uds_faltantes,
          COALESCE(SUM(CASE WHEN diferencia > 0 THEN diferencia ELSE 0 END), 0) as uds_sobrantes
        FROM animus_conteos_ciclicos
    """).fetchone()

    return jsonify({
        "ok": True,
        "conteos": conteos,
        "kpis": dict(kpis) if kpis else {},
    })


@bp.route("/api/animus/inventario-ciclico", methods=["POST"])
def animus_inv_ciclico_registrar():
    """Registra un conteo cíclico. Calcula diferencia automáticamente."""
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json() or {}
    sku = (d.get("sku") or "").strip().upper()
    if not sku:
        return jsonify({"error": "sku requerido"}), 400
    try:
        cant_shopify = int(d.get("cantidad_shopify") or 0)
        cant_fisica  = int(d.get("cantidad_fisica") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "cantidades inválidas"}), 400
    diferencia = cant_fisica - cant_shopify
    explicacion = (d.get("explicacion") or "").strip()
    fecha = (d.get("fecha_conteo") or _hoy_col().isoformat()).strip()   # Colombia, no UTC (M24)
    nombre = (d.get("producto_nombre") or "").strip()

    # Si hay diferencia y no hay explicación, advertir pero no bloquear
    if diferencia != 0 and not explicacion:
        # Permitimos guardar pero marcamos en respuesta
        pass

    conn = _db()
    c = conn.cursor()
    c.execute("""INSERT INTO animus_conteos_ciclicos
        (sku, producto_nombre, fecha_conteo, cantidad_shopify, cantidad_fisica,
         diferencia, explicacion, registrado_por)
        VALUES (?,?,?,?,?,?,?,?)""",
        (sku, nombre, fecha, cant_shopify, cant_fisica, diferencia, explicacion, u))
    conn.commit()
    return jsonify({
        "ok": True,
        "id": c.lastrowid,
        "diferencia": diferencia,
        "requiere_explicacion": diferencia != 0 and not explicacion,
    })


@bp.route("/api/animus/conteos/<int:conteo_id>/aplicar-ajuste", methods=["POST"])
def aplicar_ajuste_conteo(conteo_id):
    """Cierra el ciclo del conteo: aplica el ajuste a stock real (Gap 8).

    Cuando Daniela registra un conteo Animus que tiene diferencia con Shopify,
    la diferencia queda anotada pero el stock NO se ajusta. Este endpoint
    crea el movimiento correspondiente para sincronizar el stock fisico
    con la realidad contada.

    Body opcional: {operador: 'daniela', tipo_ajuste: 'inventario_ciclico'}

    Idempotente: marca el conteo con flag aplicado=1 + movimiento_id para
    no duplicar.
    """
    u, err, code = _auth()
    if err: return err, code

    conn = _db()
    c = conn.cursor()

    conteo = c.execute("""
        SELECT id, sku, producto_nombre, cantidad_shopify, cantidad_fisica,
               diferencia, explicacion, aplicado, movimiento_id_ajuste
        FROM animus_conteos_ciclicos WHERE id=?
    """, (conteo_id,)).fetchone()
    if not conteo:
        return jsonify({"error": "Conteo no encontrado"}), 404
    conteo_d = dict(conteo)

    if conteo_d.get("aplicado"):
        return jsonify({
            "ok": True, "ya_aplicado": True,
            "movimiento_id": conteo_d.get("movimiento_id_ajuste"),
            "mensaje": "Conteo ya tenia ajuste aplicado",
        })

    diferencia = conteo_d["diferencia"] or 0
    if diferencia == 0:
        # Marcar aplicado pero sin movimiento
        c.execute("UPDATE animus_conteos_ciclicos SET aplicado=1 WHERE id=?",
                  (conteo_id,))
        conn.commit()
        return jsonify({"ok": True, "diferencia_cero": True,
                        "mensaje": "Conteo coincide con Shopify, no requiere ajuste"})

    if diferencia != 0 and not conteo_d.get("explicacion"):
        return jsonify({
            "error": "Diferencia != 0 requiere explicacion antes de aplicar ajuste",
        }), 400

    # Crear movimiento ajuste
    sku = conteo_d["sku"]
    producto = conteo_d["producto_nombre"] or sku
    explicacion = conteo_d.get("explicacion", '')
    cantidad_abs = abs(diferencia)
    # Si fisica > shopify: ajuste positivo (encontramos mas stock)
    # Si fisica < shopify: ajuste negativo (faltante)
    tipo_mov = 'Ajuste +' if diferencia > 0 else 'Ajuste -'

    try:
        c.execute("""INSERT INTO movimientos
            (material_id, material_nombre, tipo, cantidad, fecha,
             observaciones, operador, estado_lote)
            VALUES (?,?,?,?,date('now', '-5 hours'),?,?,'OK')""",
            (sku, producto, tipo_mov, cantidad_abs,
             f'Ajuste conteo ciclico Animus #{conteo_id}: {explicacion}',
             u or 'sistema_animus'))
        mov_id = c.lastrowid

        # P0 audit 26-may · CLAUDE.md exige audit_log en cada INSERT movimientos
        # (kardex regulado · trazabilidad INVIMA).
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=u or 'sistema_animus',
                accion='ANIMUS_AJUSTE_CICLICO', tabla='movimientos',
                registro_id=mov_id,
                despues={'sku': sku, 'producto': producto[:80],
                         'tipo_mov': tipo_mov, 'cantidad': cantidad_abs,
                         'conteo_id': conteo_id,
                         'explicacion': (explicacion or '')[:200]},
                detalle=f'Ajuste cíclico Animus #{conteo_id} · {tipo_mov} {cantidad_abs} de {sku}')
        except Exception as _ae:
            import logging as _lg
            _lg.getLogger('animus').warning('audit ANIMUS_AJUSTE_CICLICO fallo: %s', _ae)

        c.execute("""UPDATE animus_conteos_ciclicos
                     SET aplicado=1, movimiento_id_ajuste=?
                     WHERE id=?""", (mov_id, conteo_id))
        conn.commit()
        return jsonify({
            "ok": True,
            "movimiento_id": mov_id,
            "tipo_movimiento": tipo_mov,
            "cantidad": cantidad_abs,
            "mensaje": f'Ajuste aplicado: {tipo_mov} {cantidad_abs} unidades de {sku}',
        })
    except Exception as _e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({"error": f"Error aplicando ajuste: {_e}"}), 500


# ════════════════════════════════════════════════════════════════════════
# INVENTARIO FISICO (asistente Daniela) · ecuacion contable
# ════════════════════════════════════════════════════════════════════════
# Sebastian 3-may-2026: para cada SKU debe cumplirse
#   stock_esperado = baseline + Σ(entradas) − Σ(ventas_shopify) − Σ(salidas)
# Si conteo_fisico ≠ stock_esperado → discrepancia rastreable.
#
# Tablas (mig 95):
#   animus_inventario_baseline (sku UNIQUE, unidades_baseline, fecha_baseline)
#   animus_inventario_movimientos (sku, tipo, cantidad, fecha, ...)
#   animus_conteos_asignados (cron diario asigna SKUs a contar)
#
# tipo movimiento ∈ {ENTRADA, SALIDA, SHOPIFY_VENTA, CONTEO, AJUSTE, BASELINE}

def _sync_shopify_a_movimientos(conn):
    """Crea movimientos SHOPIFY_VENTA por cada SKU+pedido de Shopify
    que aun no este reflejado en animus_inventario_movimientos.

    Idempotente: usa referencia = '<shopify_id>:<sku>' como key UNIQUE
    logica.

    Solo inserta movimientos para SKUs que tengan baseline activo (sino
    no aplica la ecuacion contable y el SKU no se rastrea).
    """
    c = conn.cursor()
    # Cargar SKUs con baseline · solo esos rastreamos
    skus_con_baseline = set()
    for r in c.execute("SELECT sku FROM animus_inventario_baseline").fetchall():
        skus_con_baseline.add((r['sku'] or '').upper())
    if not skus_con_baseline:
        return 0
    # Cargar referencias ya insertadas
    refs_existentes = set()
    for r in c.execute(
        "SELECT referencia FROM animus_inventario_movimientos WHERE tipo='SHOPIFY_VENTA'"
    ).fetchall():
        refs_existentes.add(r['referencia'])
    # Recorrer pedidos Shopify
    pedidos = c.execute("""
        SELECT shopify_id, sku_items, creado_en
          FROM animus_shopify_orders
         WHERE sku_items IS NOT NULL AND sku_items != ''
    """).fetchall()
    creados = 0
    for p in pedidos:
        try:
            items = json.loads(p['sku_items']) if p['sku_items'] else []
        except Exception:
            continue
        fecha = (p['creado_en'] or '')[:10]
        if not fecha:
            continue
        for it in items:
            sku = (it.get('sku') or '').strip().upper()
            qty = int(it.get('qty') or 0)
            if not sku or qty <= 0:
                continue
            if sku not in skus_con_baseline:
                continue
            ref = f"{p['shopify_id']}:{sku}"
            if ref in refs_existentes:
                continue
            c.execute("""INSERT INTO animus_inventario_movimientos
                         (sku, tipo, cantidad, fecha, origen, referencia, usuario)
                         VALUES (?, 'SHOPIFY_VENTA', ?, ?, 'shopify', ?, 'sistema')""",
                      (sku, qty, fecha, ref))
            refs_existentes.add(ref)
            creados += 1
    if creados:
        conn.commit()
    return creados


def _calcular_esperado(c, sku):
    """Retorna stock_esperado(sku) = baseline + entradas - shopify - salidas.

    Si el SKU no tiene baseline, retorna None (debe registrarse uno primero).
    """
    base_row = c.execute(
        "SELECT unidades_baseline, fecha_baseline FROM animus_inventario_baseline WHERE sku=?",
        (sku,)).fetchone()
    if not base_row:
        return None
    baseline = int(base_row['unidades_baseline'] or 0)
    fecha_b = base_row['fecha_baseline']
    # Sumas posteriores al baseline
    sums_row = c.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN tipo='ENTRADA' THEN cantidad ELSE 0 END),0) as entradas,
          COALESCE(SUM(CASE WHEN tipo='SALIDA' THEN cantidad ELSE 0 END),0) as salidas,
          COALESCE(SUM(CASE WHEN tipo='SHOPIFY_VENTA' THEN cantidad ELSE 0 END),0) as shopify,
          COALESCE(SUM(CASE WHEN tipo='AJUSTE' THEN cantidad ELSE 0 END),0) as ajustes
        FROM animus_inventario_movimientos
        WHERE sku=? AND fecha >= ?
    """, (sku, fecha_b)).fetchone()
    s = dict(sums_row) if sums_row else {'entradas': 0, 'salidas': 0, 'shopify': 0, 'ajustes': 0}
    esperado = baseline + int(s['entradas'] or 0) - int(s['shopify'] or 0) - int(s['salidas'] or 0) + int(s['ajustes'] or 0)
    return {
        'sku': sku,
        'baseline': baseline,
        'fecha_baseline': fecha_b,
        'entradas': int(s['entradas'] or 0),
        'salidas': int(s['salidas'] or 0),
        'shopify': int(s['shopify'] or 0),
        'ajustes': int(s['ajustes'] or 0),
        'esperado': esperado,
    }


@bp.route("/api/animus/inv-fisico/baseline", methods=["GET", "POST"])
def animus_inv_fisico_baseline():
    """GET: lista baseline de todos los SKUs.
    POST: registra/actualiza baseline para un SKU (idempotente)."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    if request.method == "POST":
        d = request.get_json() or {}
        sku = (d.get("sku") or "").strip().upper()
        if not sku:
            return jsonify({"error": "sku requerido"}), 400
        try:
            unidades = int(d.get("unidades_baseline"))
        except (TypeError, ValueError):
            return jsonify({"error": "unidades_baseline debe ser entero"}), 400
        if unidades < 0:
            return jsonify({"error": "unidades_baseline no puede ser negativo"}), 400
        fecha_baseline = d.get("fecha_baseline") or _hoy_col().isoformat()   # M24
        descripcion = d.get("descripcion") or ""
        observaciones = d.get("observaciones") or ""
        # Verificar si ya hay baseline (UPSERT-like)
        existe = c.execute(
            "SELECT id, unidades_baseline FROM animus_inventario_baseline WHERE sku=?",
            (sku,)).fetchone()
        if existe:
            antes_uds = existe['unidades_baseline']
            c.execute("""UPDATE animus_inventario_baseline
                         SET unidades_baseline=?, fecha_baseline=?,
                             descripcion=?, observaciones=?, creado_por=?
                         WHERE sku=?""",
                      (unidades, fecha_baseline, descripcion, observaciones, u, sku))
            audit_log(c, usuario=u, accion='ANIMUS_BASELINE_UPDATE',
                      tabla='animus_inventario_baseline', registro_id=existe['id'],
                      antes={'unidades_baseline': antes_uds},
                      despues={'unidades_baseline': unidades, 'fecha': fecha_baseline},
                      detalle=f"SKU {sku}: {antes_uds} → {unidades} (baseline {fecha_baseline})")
            bid = existe['id']
        else:
            c.execute("""INSERT INTO animus_inventario_baseline
                         (sku, descripcion, unidades_baseline, fecha_baseline,
                          creado_por, observaciones)
                         VALUES (?,?,?,?,?,?)""",
                      (sku, descripcion, unidades, fecha_baseline, u, observaciones))
            bid = c.lastrowid
            audit_log(c, usuario=u, accion='ANIMUS_BASELINE_CREATE',
                      tabla='animus_inventario_baseline', registro_id=bid,
                      despues={'sku': sku, 'unidades_baseline': unidades,
                                'fecha': fecha_baseline},
                      detalle=f"Baseline {sku}: {unidades} uds @ {fecha_baseline}")
        conn.commit()
        return jsonify({"ok": True, "id": bid, "sku": sku,
                        "unidades_baseline": unidades, "fecha_baseline": fecha_baseline})
    # GET
    rows = c.execute("""SELECT id, sku, descripcion, unidades_baseline,
                               fecha_baseline, creado_por, observaciones, creado_en
                         FROM animus_inventario_baseline ORDER BY sku""").fetchall()
    return jsonify({"baseline": [dict(r) for r in rows]})


@bp.route("/api/animus/inv-fisico/entrada", methods=["POST"])
def animus_inv_fisico_entrada():
    """Registra entrada de inventario (produccion / devolucion / ajuste +).

    Body: {sku, cantidad (>0), origen, referencia?, fecha?, motivo?}
    """
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json() or {}
    sku = (d.get("sku") or "").strip().upper()
    if not sku:
        return jsonify({"error": "sku requerido"}), 400
    try:
        cantidad = int(d.get("cantidad"))
    except (TypeError, ValueError):
        return jsonify({"error": "cantidad debe ser entero"}), 400
    if cantidad <= 0:
        return jsonify({"error": "cantidad debe ser > 0 (usa /salida para descontar)"}), 400
    origen = (d.get("origen") or "produccion").strip()
    if origen not in ('produccion','devolucion','ajuste','otro'):
        return jsonify({"error": "origen invalido (produccion|devolucion|ajuste|otro)"}), 400
    fecha = d.get("fecha") or _hoy_col().isoformat()   # M24
    conn = _db(); c = conn.cursor()
    c.execute("""INSERT INTO animus_inventario_movimientos
                 (sku, tipo, cantidad, fecha, origen, referencia, motivo, usuario)
                 VALUES (?,'ENTRADA',?,?,?,?,?,?)""",
              (sku, cantidad, fecha, origen, d.get("referencia",""), d.get("motivo",""), u))
    mid = c.lastrowid
    audit_log(c, usuario=u, accion='ANIMUS_INV_ENTRADA',
              tabla='animus_inventario_movimientos', registro_id=mid,
              despues={'sku': sku, 'cantidad': cantidad, 'origen': origen, 'fecha': fecha},
              detalle=f"+{cantidad} uds {sku} ({origen}) {fecha}")
    conn.commit()
    return jsonify({"ok": True, "id": mid, "sku": sku, "cantidad": cantidad})


@bp.route("/api/animus/inv-fisico/salida", methods=["POST"])
def animus_inv_fisico_salida():
    """Registra salida de inventario NO-Shopify (presencial / regalo / dano /
    vencido / devolucion a planta).

    Body: {sku, cantidad (>0), origen, referencia?, fecha?, motivo?}
    """
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json() or {}
    sku = (d.get("sku") or "").strip().upper()
    if not sku:
        return jsonify({"error": "sku requerido"}), 400
    try:
        cantidad = int(d.get("cantidad"))
    except (TypeError, ValueError):
        return jsonify({"error": "cantidad debe ser entero"}), 400
    if cantidad <= 0:
        return jsonify({"error": "cantidad debe ser > 0"}), 400
    origen = (d.get("origen") or "presencial").strip()
    if origen not in ('presencial','regalo','dano','vencido','devolucion_planta','otro'):
        return jsonify({"error": "origen invalido"}), 400
    fecha = d.get("fecha") or _hoy_col().isoformat()   # M24
    conn = _db(); c = conn.cursor()
    c.execute("""INSERT INTO animus_inventario_movimientos
                 (sku, tipo, cantidad, fecha, origen, referencia, motivo, usuario)
                 VALUES (?,'SALIDA',?,?,?,?,?,?)""",
              (sku, cantidad, fecha, origen, d.get("referencia",""), d.get("motivo",""), u))
    mid = c.lastrowid
    audit_log(c, usuario=u, accion='ANIMUS_INV_SALIDA',
              tabla='animus_inventario_movimientos', registro_id=mid,
              despues={'sku': sku, 'cantidad': cantidad, 'origen': origen, 'fecha': fecha},
              detalle=f"-{cantidad} uds {sku} ({origen}) {fecha}")
    conn.commit()
    return jsonify({"ok": True, "id": mid, "sku": sku, "cantidad": cantidad})


@bp.route("/api/animus/inv-fisico/esperado/<sku>", methods=["GET"])
def animus_inv_fisico_esperado_sku(sku):
    """Calcula stock_esperado para un SKU especifico (con desglose)."""
    u, err, code = _auth()
    if err: return err, code
    sku = (sku or "").strip().upper()
    conn = _db(); c = conn.cursor()
    info = _calcular_esperado(c, sku)
    if info is None:
        return jsonify({"error": "SKU sin baseline · registra uno primero"}), 404
    return jsonify(info)


@bp.route("/api/animus/inv-fisico/esperado", methods=["GET"])
def animus_inv_fisico_esperado_todos():
    """Lista esperado para TODOS los SKUs con baseline."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    skus = c.execute(
        "SELECT sku FROM animus_inventario_baseline ORDER BY sku").fetchall()
    out = []
    for r in skus:
        info = _calcular_esperado(c, r['sku'])
        if info:
            out.append(info)
    return jsonify({"items": out, "total_skus": len(out)})


# ── CONTEO CICLICO Fase 2 ─────────────────────────────────────────

@bp.route("/api/animus/inv-fisico/conteo/asignar-hoy", methods=["POST"])
def animus_inv_fisico_asignar_hoy():
    """Asigna N SKUs para contar HOY. Llamado por cron o manualmente.

    Algoritmo prioridad:
      1. SKUs sin baseline (urgente · sembrar primero)
      2. SKUs con mas dias sin contar
      3. SKUs con mas movimientos recientes (volatiles)

    Body opcional: {n: int default 5, asignar_a: usuario default 'daniela'}
    """
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json(silent=True) or {}
    try:
        n = int(d.get("n", 5))
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(n, 20))
    asignar_a = (d.get("asignar_a") or "daniela").strip().lower()
    conn = _db(); c = conn.cursor()

    # ¿Ya hay asignaciones pendientes para hoy?
    pendientes = c.execute("""
        SELECT sku FROM animus_conteos_asignados
         WHERE fecha_asignado = date('now', '-5 hours') AND estado = 'pendiente'
    """).fetchall()
    if pendientes:
        return jsonify({
            "ok": True, "ya_asignados_hoy": len(pendientes),
            "skus": [r['sku'] for r in pendientes],
            "mensaje": "Ya hay SKUs asignados hoy."
        })

    # Score: dias_sin_contar * 1.0 + volatilidad (mov ultimos 7d) * 0.5
    candidatos = c.execute("""
        WITH baseline_skus AS (
            SELECT sku, fecha_baseline FROM animus_inventario_baseline
        ),
        ultimo_conteo AS (
            SELECT sku, MAX(fecha_asignado) as ult
              FROM animus_conteos_asignados
             WHERE estado = 'contado'
             GROUP BY sku
        ),
        volatilidad AS (
            SELECT sku, COUNT(*) as movs
              FROM animus_inventario_movimientos
             WHERE fecha >= date('now', '-5 hours', '-7 day')
             GROUP BY sku
        )
        SELECT b.sku,
               COALESCE(julianday('now') - julianday(uc.ult), 999) as dias_sin_contar,
               COALESCE(v.movs, 0) as movs_7d
          FROM baseline_skus b
          LEFT JOIN ultimo_conteo uc ON uc.sku = b.sku
          LEFT JOIN volatilidad v ON v.sku = b.sku
          ORDER BY dias_sin_contar DESC, movs_7d DESC
          LIMIT ?
    """, (n,)).fetchall()

    asignados = []
    for r in candidatos:
        # #2 (12-jun): setear fecha_asignado en hora Colombia (date('now','-5 hours'))
        # EXPLICITO · el default de columna es date('now') (UTC) pero el check de
        # idempotencia (arriba) compara date('now','-5 hours') -> de noche la fecha UTC
        # rodaba al dia siguiente y NO matcheaba -> re-asignaba (no idempotente).
        c.execute("""INSERT INTO animus_conteos_asignados
                     (sku, asignado_a, estado, fecha_asignado)
                     VALUES (?, ?, 'pendiente', date('now', '-5 hours'))""",
                  (r['sku'], asignar_a))
        asignados.append({
            'sku': r['sku'],
            'dias_sin_contar': round(r['dias_sin_contar'], 1),
            'movs_7d': r['movs_7d'],
        })
    audit_log(c, usuario=u, accion='ANIMUS_CONTEO_ASIGNAR',
              tabla='animus_conteos_asignados', registro_id=None,
              despues={'n': len(asignados), 'asignar_a': asignar_a},
              detalle=f"Asignados {len(asignados)} SKUs a {asignar_a}: " +
                       ', '.join(x['sku'] for x in asignados))
    conn.commit()
    return jsonify({"ok": True, "asignados": asignados, "asignar_a": asignar_a})


@bp.route("/api/animus/inv-fisico/conteo/pendientes", methods=["GET"])
def animus_inv_fisico_conteo_pendientes():
    """Lista SKUs asignados pendientes de contar."""
    u, err, code = _auth()
    if err: return err, code
    asignar_a = request.args.get("asignar_a")
    conn = _db(); c = conn.cursor()
    sql = """SELECT id, sku, fecha_asignado, asignado_a, creado_en
               FROM animus_conteos_asignados
              WHERE estado = 'pendiente'"""
    params = []
    if asignar_a:
        sql += " AND asignado_a = ?"; params.append(asignar_a.lower())
    sql += " ORDER BY fecha_asignado DESC"
    rows = c.execute(sql, params).fetchall()
    out = []
    for r in rows:
        info = _calcular_esperado(c, r['sku'])
        out.append({
            'id': r['id'], 'sku': r['sku'],
            'fecha_asignado': r['fecha_asignado'],
            'asignado_a': r['asignado_a'],
            'esperado': info['esperado'] if info else None,
        })
    return jsonify({"pendientes": out})


@bp.route("/api/animus/inv-fisico/conteo/<int:asig_id>/registrar", methods=["POST"])
def animus_inv_fisico_conteo_registrar(asig_id):
    """Registra el conteo fisico de un SKU asignado.

    Body: {cantidad_fisica, motivo_diferencia? (si != esperado)}
    """
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json() or {}
    try:
        fisica = int(d.get("cantidad_fisica"))
    except (TypeError, ValueError):
        return jsonify({"error": "cantidad_fisica debe ser entero"}), 400
    if fisica < 0:
        return jsonify({"error": "cantidad_fisica no puede ser negativo"}), 400
    motivo = (d.get("motivo_diferencia") or "").strip()
    aplicar_ajuste = bool(d.get("aplicar_ajuste", False))

    conn = _db(); c = conn.cursor()
    asig = c.execute(
        "SELECT id, sku, estado FROM animus_conteos_asignados WHERE id=?",
        (asig_id,)).fetchone()
    if not asig:
        return jsonify({"error": "asignacion no encontrada"}), 404
    if asig['estado'] != 'pendiente':
        return jsonify({"error": f"asignacion en estado {asig['estado']}, no se puede registrar"}), 400

    info = _calcular_esperado(c, asig['sku'])
    if not info:
        return jsonify({"error": "SKU sin baseline"}), 400
    esperado = info['esperado']
    diferencia = fisica - esperado

    # Si hay diferencia y no se da motivo y >| 2 |, requerir motivo
    if abs(diferencia) > 2 and not motivo:
        return jsonify({
            "error": "Diferencia significativa requiere motivo",
            "diferencia": diferencia, "esperado": esperado, "fisica": fisica,
            "desglose": info,
        }), 400

    c.execute("""UPDATE animus_conteos_asignados
                 SET cantidad_fisica=?, cantidad_esperada=?,
                     diferencia=?, motivo_diferencia=?,
                     estado='contado', contado_en=datetime('now', '-5 hours')
                 WHERE id=?""",
              (fisica, esperado, diferencia, motivo, asig_id))

    # Registrar movimiento CONTEO
    c.execute("""INSERT INTO animus_inventario_movimientos
                 (sku, tipo, cantidad, fecha, origen, motivo, usuario)
                 VALUES (?, 'CONTEO', ?, date('now', '-5 hours'), ?, ?, ?)""",
              (asig['sku'], fisica, 'conteo_ciclico', motivo, u))

    # Si aplicar_ajuste, agregar AJUSTE para que esperado matchee con fisica
    if aplicar_ajuste and diferencia != 0:
        c.execute("""INSERT INTO animus_inventario_movimientos
                     (sku, tipo, cantidad, fecha, origen, motivo, usuario)
                     VALUES (?, 'AJUSTE', ?, date('now', '-5 hours'), 'conteo_ajuste', ?, ?)""",
                  (asig['sku'], diferencia, motivo or 'Ajuste por conteo ciclico', u))

    audit_log(c, usuario=u, accion='ANIMUS_CONTEO_REGISTRAR',
              tabla='animus_conteos_asignados', registro_id=asig_id,
              despues={'sku': asig['sku'], 'fisica': fisica, 'esperado': esperado,
                        'diferencia': diferencia, 'motivo': motivo[:200],
                        'aplicado_ajuste': aplicar_ajuste},
              detalle=f"Conteo {asig['sku']}: fisica={fisica} esperado={esperado} dif={diferencia}" +
                       (f" · ajustado" if aplicar_ajuste else ""))
    conn.commit()
    return jsonify({
        "ok": True,
        "sku": asig['sku'],
        "esperado": esperado,
        "fisica": fisica,
        "diferencia": diferencia,
        "desglose": info,
        "aplicado_ajuste": aplicar_ajuste,
        "alerta": "Diferencia detectada · revisar" if diferencia != 0 else None,
    })


@bp.route("/api/animus/inv-fisico/conteo/historial", methods=["GET"])
def animus_inv_fisico_conteo_historial():
    """Historial de conteos contados (para dashboard)."""
    u, err, code = _auth()
    if err: return err, code
    sku = (request.args.get("sku") or "").strip().upper()
    conn = _db(); c = conn.cursor()
    sql = """SELECT id, sku, fecha_asignado, asignado_a, cantidad_fisica,
                    cantidad_esperada, diferencia, motivo_diferencia,
                    contado_en
               FROM animus_conteos_asignados
              WHERE estado = 'contado'"""
    params = []
    if sku:
        sql += " AND sku = ?"; params.append(sku)
    sql += " ORDER BY contado_en DESC LIMIT 200"
    rows = [dict(r) for r in c.execute(sql, params).fetchall()]
    # KPIs
    kpis_row = c.execute("""SELECT
          COUNT(*) as total,
          COALESCE(SUM(CASE WHEN diferencia != 0 THEN 1 ELSE 0 END),0) as con_diferencia,
          COALESCE(SUM(CASE WHEN diferencia < 0 THEN -diferencia ELSE 0 END),0) as faltantes,
          COALESCE(SUM(CASE WHEN diferencia > 0 THEN diferencia ELSE 0 END),0) as sobrantes
        FROM animus_conteos_asignados
        WHERE estado = 'contado' AND contado_en >= date('now', '-5 hours', '-30 day')
    """).fetchone()
    return jsonify({
        "historial": rows,
        "kpis_30d": dict(kpis_row) if kpis_row else {},
    })


@bp.route("/api/animus/inv-fisico/baseline/sembrar-desde-shopify", methods=["POST"])
def animus_inv_fisico_sembrar_baselines():
    """Crea baseline=0 para cada SKU vendido en Shopify ultimos 30d que
    aun no tenga baseline. Daniela solo edita la cantidad real despues.

    Body opcional: {dias: int default 30}

    Devuelve: {creados: N, ya_tenian: M, skus_creados: [...]}
    """
    u, err, code = _auth()
    if err: return err, code
    d = request.get_json(silent=True) or {}
    try:
        dias = int(d.get("dias", 30))
    except (TypeError, ValueError):
        dias = 30
    dias = max(1, min(dias, 365))
    conn = _db(); c = conn.cursor()

    # SKUs vendidos en Shopify
    skus_shopify = set()
    rows = c.execute(f"""SELECT sku_items FROM animus_shopify_orders
                         WHERE creado_en >= date('now', '-5 hours', '-{dias} day')
                           AND sku_items IS NOT NULL AND sku_items != ''""").fetchall()
    for r in rows:
        try:
            for it in (json.loads(r['sku_items']) or []):
                s = (it.get('sku') or '').strip().upper()
                if s: skus_shopify.add(s)
        except Exception:
            continue

    if not skus_shopify:
        return jsonify({"ok": True, "creados": 0, "ya_tenian": 0,
                        "skus_creados": [], "skus_existentes": [],
                        "mensaje": "Sin SKUs en Shopify ultimos " + str(dias) + " dias. Sincroniza Shopify primero."})

    # SKUs ya con baseline
    ya_existentes = set()
    for r in c.execute("SELECT sku FROM animus_inventario_baseline").fetchall():
        ya_existentes.add((r['sku'] or '').upper())

    skus_a_crear = sorted(skus_shopify - ya_existentes)
    fecha = _hoy_col().isoformat()   # M24
    creados = []
    for sku in skus_a_crear:
        try:
            c.execute("""INSERT OR IGNORE INTO animus_inventario_baseline
                         (sku, descripcion, unidades_baseline, fecha_baseline,
                          creado_por, observaciones)
                         VALUES (?, '', 0, ?, ?, 'Sembrado automatico desde Shopify · editar con cantidad real')""",
                      (sku, fecha, u))
            creados.append(sku)
        except Exception:
            continue

    if creados:
        audit_log(c, usuario=u, accion='ANIMUS_BASELINE_SEMBRAR',
                  tabla='animus_inventario_baseline', registro_id=None,
                  despues={'sembrados': len(creados), 'dias': dias},
                  detalle=f"Sembrados {len(creados)} baselines=0 desde Shopify ({dias}d): " +
                           ', '.join(creados[:8]) + ("..." if len(creados)>8 else ""))
    conn.commit()

    return jsonify({
        "ok": True,
        "creados": len(creados),
        "ya_tenian": len(ya_existentes & skus_shopify),
        "skus_creados": creados,
        "skus_existentes": sorted(ya_existentes & skus_shopify),
        "mensaje": f"Sembrados {len(creados)} SKUs en baseline=0. Editar cada uno con la cantidad real."
    })


@bp.route("/api/animus/inv-fisico/diagnostico", methods=["GET"])
def animus_inv_fisico_diagnostico():
    """Dashboard de discrepancias y deteccion de patrones.

    Devuelve:
      - kpis: discrepancia_total_30d, skus_con_dif, faltantes, sobrantes
      - top_problematicos: SKUs con mas diferencias acumuladas
      - patrones_detectados: lista de alertas tipo
        · "SKU X siempre desfasa negativo · revisar mapeo Shopify"
        · "SKU Y desfasa positivo siempre · entradas no anotadas"
        · "Patron general: faltantes >> sobrantes · posible robo/dano"
      - sin_baseline: SKUs vendidos en Shopify sin baseline registrado
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()

    # KPIs 30d
    kpis_row = c.execute("""SELECT
          COUNT(*) as total_conteos,
          COALESCE(SUM(CASE WHEN diferencia != 0 THEN 1 ELSE 0 END),0) as con_dif,
          COALESCE(SUM(CASE WHEN diferencia < 0 THEN -diferencia ELSE 0 END),0) as faltantes,
          COALESCE(SUM(CASE WHEN diferencia > 0 THEN diferencia ELSE 0 END),0) as sobrantes
        FROM animus_conteos_asignados
        WHERE estado = 'contado' AND contado_en >= date('now', '-5 hours', '-30 day')
    """).fetchone()
    kpis = dict(kpis_row) if kpis_row else {
        'total_conteos': 0, 'con_dif': 0, 'faltantes': 0, 'sobrantes': 0
    }

    # Top SKUs problemáticos (mas diferencia acumulada absoluta)
    top_rows = c.execute("""
        SELECT sku,
               COUNT(*) as veces_contado,
               COALESCE(SUM(CASE WHEN diferencia != 0 THEN 1 ELSE 0 END),0) as veces_con_dif,
               COALESCE(SUM(diferencia),0) as suma_dif,
               COALESCE(SUM(CASE WHEN diferencia<0 THEN -diferencia ELSE diferencia END),0) as abs_dif
          FROM animus_conteos_asignados
         WHERE estado = 'contado' AND contado_en >= date('now', '-5 hours', '-90 day')
         GROUP BY sku
         HAVING abs_dif > 0
         ORDER BY abs_dif DESC
         LIMIT 10
    """).fetchall()
    top_problematicos = [dict(r) for r in top_rows]

    # Detección de patrones
    patrones = []
    for row in top_rows:
        sku = row['sku']
        veces = row['veces_contado']
        veces_dif = row['veces_con_dif']
        suma = row['suma_dif']
        # SKU que siempre desfasa
        if veces >= 3 and veces_dif == veces:
            if suma < 0:
                patrones.append({
                    'severidad': 'alta',
                    'sku': sku,
                    'tipo': 'siempre_falta',
                    'mensaje': f'{sku} desfasa SIEMPRE negativo ({veces}/{veces} veces, total -{abs(suma)} uds). Posible: mapeo Shopify roto / robo / dano sistemico.',
                })
            else:
                patrones.append({
                    'severidad': 'media',
                    'sku': sku,
                    'tipo': 'siempre_sobra',
                    'mensaje': f'{sku} desfasa SIEMPRE positivo ({veces}/{veces} veces, total +{suma} uds). Posible: entradas no registradas.',
                })

    # Patron global: faltantes vs sobrantes
    if kpis['faltantes'] > 0 or kpis['sobrantes'] > 0:
        ratio = kpis['faltantes'] / max(kpis['sobrantes'], 1) if kpis['sobrantes'] > 0 else float('inf')
        if ratio > 3 and kpis['faltantes'] > 5:
            patrones.append({
                'severidad': 'alta',
                'sku': None,
                'tipo': 'patron_faltantes',
                'mensaje': f'Patron general: faltantes ({kpis["faltantes"]}) >> sobrantes ({kpis["sobrantes"]}). Investigar robo/dano/regalos no registrados.',
            })
        elif ratio < 0.33 and kpis['sobrantes'] > 5:
            patrones.append({
                'severidad': 'media',
                'sku': None,
                'tipo': 'patron_sobrantes',
                'mensaje': f'Patron general: sobrantes ({kpis["sobrantes"]}) >> faltantes ({kpis["faltantes"]}). La asistente olvida anotar entradas.',
            })

    # SKUs vendidos en Shopify sin baseline
    skus_shopify = set()
    for r in c.execute("""SELECT sku_items FROM animus_shopify_orders
                          WHERE creado_en >= date('now', '-5 hours', '-30 day')
                            AND sku_items IS NOT NULL""").fetchall():
        try:
            for it in (json.loads(r['sku_items']) or []):
                s = (it.get('sku') or '').strip().upper()
                if s: skus_shopify.add(s)
        except Exception:
            pass
    skus_con_baseline = set()
    for r in c.execute("SELECT sku FROM animus_inventario_baseline").fetchall():
        skus_con_baseline.add((r['sku'] or '').upper())
    sin_baseline = sorted(skus_shopify - skus_con_baseline)

    return jsonify({
        'kpis': kpis,
        'top_problematicos': top_problematicos,
        'patrones_detectados': patrones,
        'sin_baseline': sin_baseline,
        'total_skus_baseline': len(skus_con_baseline),
        'total_skus_shopify_30d': len(skus_shopify),
    })


@bp.route("/api/animus/inv-fisico/sync-shopify", methods=["POST"])
def animus_inv_fisico_sync_shopify():
    """Sincroniza ventas Shopify ya descargadas hacia movimientos de
    inventario fisico (sin volver a llamar API Shopify · idempotente)."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    try:
        creados = _sync_shopify_a_movimientos(conn)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500
    if creados:
        from audit_helpers import audit_log
        c = conn.cursor()
        audit_log(c, usuario=u, accion='ANIMUS_SYNC_SHOPIFY_INV',
                  tabla='animus_inventario_movimientos', registro_id=None,
                  despues={'movimientos_creados': creados},
                  detalle=f"Sync Shopify · {creados} ventas reflejadas en inv fisico")
        conn.commit()
    return jsonify({"ok": True, "ventas_creadas": creados})


@bp.route("/api/animus/inv-fisico/movimientos", methods=["GET"])
def animus_inv_fisico_movimientos():
    """Lista movimientos con filtros (sku, tipo, desde)."""
    u, err, code = _auth()
    if err: return err, code
    sku   = (request.args.get("sku") or "").strip().upper()
    tipo  = (request.args.get("tipo") or "").strip().upper()
    desde = (request.args.get("desde") or "").strip()
    conn = _db(); c = conn.cursor()
    sql = "SELECT * FROM animus_inventario_movimientos WHERE 1=1"
    params = []
    if sku: sql += " AND sku=?"; params.append(sku)
    if tipo: sql += " AND tipo=?"; params.append(tipo)
    if desde: sql += " AND fecha>=?"; params.append(desde)
    sql += " ORDER BY fecha DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    return jsonify({"movimientos": [dict(r) for r in rows]})


# ── REDIRECT eliminado: /animus ahora sirve el panel de Caja Menor + ──
#    Inventario Cíclico (definido en core.py con ANIMUS_HTML).


# ════════════════════════════════════════════════════════════════════════
# PQR COMERCIAL de ÁNIMUS · envíos, producto equivocado, devoluciones, servicio.
# Los crea el enrutador de Aseguramiento (/api/pqr/inbound + triaje) o a mano.
# ════════════════════════════════════════════════════════════════════════
_PQR_A_ESTADOS = ('nuevo', 'en_proceso', 'resuelto', 'cerrado')
_PQR_A_TIPOS = ('envio', 'producto_equivocado', 'faltante', 'devolucion',
                'servicio', 'facturacion', 'comercial', 'otro')


@bp.route("/api/animus/pqr", methods=["GET", "POST"])
def animus_pqr_listar():
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db(); c = conn.cursor()
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        desc = (d.get("descripcion") or "").strip()
        if len(desc) < 5:
            return jsonify({"error": "descripcion requerida"}), 400
        tipo = (d.get("tipo") or "otro").strip().lower()
        if tipo not in _PQR_A_TIPOS:
            tipo = "otro"
        from audit_helpers import siguiente_codigo_secuencial as _seqc
        try:
            cod = _seqc(c, "PQR-A", "animus_pqr")
        except Exception:
            cod = "PQR-A-" + datetime.now().strftime("%y%m%d%H%M%S")
        c.execute(
            "INSERT INTO animus_pqr (codigo, canal, contacto_nombre, contacto_email, contacto_telefono, "
            "tipo, descripcion, prioridad, creado_por) VALUES (?,?,?,?,?,?,?,?,?)",
            (cod, (d.get("canal") or "otro"), (d.get("contacto_nombre") or "")[:200],
             (d.get("contacto_email") or "")[:200], (d.get("contacto_telefono") or "")[:80],
             tipo, desc[:3000], (d.get("prioridad") or "media"), u))
        aid = c.lastrowid
        try:
            audit_log(c, usuario=u, accion="CREAR_PQR_ANIMUS", tabla="animus_pqr",
                      registro_id=aid, despues={"codigo": cod, "tipo": tipo})
        except Exception:
            pass
        conn.commit()
        return jsonify({"ok": True, "id": aid, "codigo": cod}), 201
    estado = (request.args.get("estado") or "").strip()
    sql = ("SELECT id, codigo, canal, contacto_nombre, contacto_email, contacto_telefono, tipo, "
           "descripcion, prioridad, estado, asignado_a, respuesta, respondido_por, respondido_en, "
           "pedido_numero, creado_en FROM animus_pqr")
    params = []
    if estado in _PQR_A_ESTADOS:
        sql += " WHERE estado=?"; params.append(estado)
    sql += " ORDER BY CASE prioridad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, id DESC LIMIT 300"
    rows = c.execute(sql, params).fetchall()
    items = [dict(r) for r in rows]
    resumen = {}
    for e in _PQR_A_ESTADOS:
        resumen[e] = c.execute("SELECT COUNT(*) FROM animus_pqr WHERE estado=?", (e,)).fetchone()[0]
    return jsonify({"pqr": items, "resumen": resumen})


@bp.route("/api/animus/pqr/<int:pid>", methods=["PATCH"])
def animus_pqr_actualizar(pid):
    u, err, code = _auth()
    if err:
        return err, code
    d = request.get_json(silent=True) or {}
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM animus_pqr WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"error": "no encontrado"}), 404
    campos, vals = [], []
    if "estado" in d:
        est = (d.get("estado") or "").strip().lower()
        if est not in _PQR_A_ESTADOS:
            return jsonify({"error": "estado inválido"}), 400
        campos.append("estado=?"); vals.append(est)
    if "prioridad" in d:
        pr = (d.get("prioridad") or "").strip().lower()
        if pr not in ("alta", "media", "baja"):
            return jsonify({"error": "prioridad inválida"}), 400
        campos.append("prioridad=?"); vals.append(pr)
    if "asignado_a" in d:
        campos.append("asignado_a=?"); vals.append((d.get("asignado_a") or "")[:80] or None)
    if "respuesta" in d:
        campos.append("respuesta=?"); vals.append((d.get("respuesta") or "")[:3000])
        campos.append("respondido_por=?"); vals.append(u)
        campos.append("respondido_en=?"); vals.append(_hoy_col().isoformat())   # M24
    if not campos:
        return jsonify({"error": "nada que actualizar"}), 400
    campos.append("actualizado_en=?"); vals.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    vals.append(pid)
    c.execute("UPDATE animus_pqr SET " + ", ".join(campos) + " WHERE id=?", vals)
    try:
        audit_log(c, usuario=u, accion="ACTUALIZAR_PQR_ANIMUS", tabla="animus_pqr",
                  registro_id=pid, despues={k: d[k] for k in d if k in ("estado", "prioridad", "asignado_a")})
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True})

