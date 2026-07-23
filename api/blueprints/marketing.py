"""
marketing.py — Blueprint módulo Marketing
Campañas, Influencers, Contenido, Analytics, 5 Agentes IA internos
"""
import logging
import os
import sqlite3, urllib.request
import traceback
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session, Response

# Sebastián 25-may-2026 PM · audit P1 · log a nivel módulo · antes
# referenciado en daemon como `log.error(...)` sin definir → NameError
# silencioso en el except, daemon moría sin rastro.
log = logging.getLogger('marketing')

from config import DB_PATH, ADMIN_USERS, MARKETING_USERS, USER_EMAILS
try:
    from config import CONTADORA_USERS
except ImportError:
    CONTADORA_USERS = ()
from database import get_db
from audit_helpers import audit_log

bp = Blueprint("marketing", __name__)
# Fallback hardcoded · sembrado en mig 186 hacia marketing_eventos_calendario.
# Agentes leen via _get_calendario_cosmetico(conn) que prioriza DB · este array
# queda como safety net si la mig 186 no aplicó o la tabla está vacía.
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


def _get_calendario_cosmetico(conn):
    """Devuelve eventos del calendario · prioriza DB editable, fallback hardcoded.

    Agentes (estacionalidad, estrategia) usan esto. Si la tabla no existe
    o está vacía, devuelve CALENDARIO_COSMETICO sin romper.
    """
    try:
        rows = conn.execute(
            "SELECT evento, fecha, color, multiplicador FROM marketing_eventos_calendario "
            "WHERE COALESCE(activo,1)=1 ORDER BY fecha"
        ).fetchall()
        if rows:
            return [{"evento": r["evento"], "fecha": r["fecha"],
                      "color": r["color"] or "#94a3b8",
                      "multiplicador": float(r["multiplicador"] or 1.0)} for r in rows]
    except Exception:
        pass
    return CALENDARIO_COSMETICO

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
        """Sebastián 1-may-2026 audit: el Graph API acepta token en query
        string (legacy) Y en header Authorization. Movemos a Authorization
        para no exponer el token en logs de urllib si falla la request.
        El query string ?access_token=X queda como fallback compatible."""
        import urllib.request, urllib.parse, json, re
        try:
            # Extraer token del query string para usarlo en Authorization header.
            # NO eliminamos del URL — algunos endpoints requieren el query
            # param para subprocesos batch.
            req = urllib.request.Request(url)
            m = re.search(r'[?&]access_token=([^&]+)', url)
            if m:
                req.add_header('Authorization', f'Bearer {urllib.parse.unquote(m.group(1))}')
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read()), None
        except Exception as e:
            # Sanitizar error: NO incluir URL (puede contener token en query).
            # Solo el tipo de error y mensaje sin URL completa.
            err_msg = str(e)
            # Redactar token si aparece en mensaje
            err_msg = re.sub(r'access_token=[^&\s\'"]+', 'access_token=***REDACTED***', err_msg)
            return None, f'{type(e).__name__}: {err_msg[:200]}'

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
                    except Exception as _e:
                        __import__('logging').getLogger('marketing').warning(
                            'guardar IG token fallo: %s', _e
                        )
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

def _puede_capturar_banco(u):
    """Quién puede LEER/ESCRIBIR datos bancarios de influencers.

    CEO Sebastián 3-jun-2026 (LEY): marketing (Jeferson) es el responsable de
    CAPTURAR y MANTENER los datos bancarios del influencer (banco/cuenta/cédula/
    tipo) que viajan a la cuenta de cobro → Compras para que Sebastián pague.
    Por eso la ESCRITURA/EDICIÓN se permite a MARKETING_USERS, no solo a admin.

    Habeas Data Ley 1581 CO se preserva con: (a) audit_log enmascarado en toda
    mutación bancaria, y (b) enmascaramiento de la LECTURA masiva/agregada de
    terceros (listas, panel, scored, duplicados) que se mantiene intacto. Lo que
    se abre es la captura y la verificación del registro que se está editando.
    """
    ul = (u or '').lower()
    return ul in {x.lower() for x in (
        set(ADMIN_USERS) | set(CONTADORA_USERS) | set(MARKETING_USERS))}

def _send_push_alert(conn, tipo, clave_unica, asunto, cuerpo_resumen,
                     severidad="medio", destinatario=None):
    """Dispara alerta por email a Sebastian/marketing alerts y la registra en log.

    Idempotente por día: la combinación (tipo, clave_unica, destinatario, fecha)
    es UNIQUE — si la misma alerta ya se mandó hoy, no re-envía.

    Args:
      tipo:         'stock_critico', 'oc_pendiente_pago', 'evento_sin_campana', etc.
      clave_unica:  identificador del recurso (ej: 'SKU-LBHA-30')
      asunto:       subject del email
      cuerpo_resumen: cuerpo del email (HTML o texto)
      severidad:    'critico' | 'alto' | 'medio' | 'bajo'
      destinatario: email; default = MARKETING_ALERT_EMAIL o EMAIL_SEBASTIAN o
                    sebastianvargasisaza@gmail.com.
    """
    import os
    if not destinatario:
        destinatario = (
            os.environ.get("MARKETING_ALERT_EMAIL") or
            os.environ.get("EMAIL_SEBASTIAN") or
            "sebastianvargasisaza@gmail.com"
        )

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        # UNIQUE constraint maneja la deduplicación por día
        conn.execute("""INSERT OR IGNORE INTO marketing_push_alerts_log
            (tipo, clave_unica, destinatario, asunto, cuerpo_resumen, severidad, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tipo, clave_unica, destinatario, asunto[:200],
             cuerpo_resumen[:1000], severidad, today))
        # rowcount == 0 si ya estaba (UNIQUE → ignore) → no mandar email
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return False
        conn.commit()
    except Exception as _e:
        __import__('logging').getLogger('marketing').warning(
            'push_alert dedupe fallo (tipo=%s clave=%s): %s', tipo, clave_unica, _e
        )
        return False

    # Mandar email en background — no bloquea la respuesta del agente
    try:
        from notificaciones import SistemaNotificaciones
        sn = SistemaNotificaciones()
        if not sn.email_remitente or not sn.contraseña:
            return False
        # Email con plantilla simple — colorear severidad
        sev_colors = {
            "critico": "#dc2626", "alto": "#f59e0b",
            "medio":   "#3b82f6", "bajo":  "#71717a"
        }
        color = sev_colors.get(severidad, "#3b82f6")
        html = f"""<html><body style="font-family:Arial,sans-serif;max-width:600px;">
        <div style="background:#0f172a;color:#f1f5f9;padding:20px;border-radius:8px;border-left:4px solid {color};">
          <div style="font-size:11px;color:{color};font-weight:700;text-transform:uppercase;letter-spacing:.1em;">
            ÁNIMUS · alerta {severidad}
          </div>
          <h2 style="color:#fff;margin:8px 0 12px;">{asunto}</h2>
          <div style="color:#cbd5e1;line-height:1.6;font-size:14px;">{cuerpo_resumen}</div>
          <div style="margin-top:18px;padding-top:14px;border-top:1px solid #334155;font-size:11px;color:#64748b;">
            Tipo: <code>{tipo}</code> · Clave: <code>{clave_unica}</code><br>
            Generada {datetime.now().strftime('%Y-%m-%d %H:%M')} por el sistema de Marketing.
          </div>
        </div>
        </body></html>"""
        sn.enviar_en_background(
            sn._enviar_email_html if hasattr(sn, "_enviar_email_html") else sn.enviar_alerta_stock_bajo,
            destinatario, asunto, html
        ) if False else None  # deprecated path
        # Usar SMTP directamente vía la clase para máxima compatibilidad
        import smtplib, ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        def _send():
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[ÁNIMUS] {asunto}"
                msg["From"] = sn.email_remitente
                msg["To"] = destinatario
                msg.attach(MIMEText(html, "html", "utf-8"))
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(sn.smtp_server, sn.smtp_port, context=ctx) as s:
                    s.login(sn.email_remitente, sn.contraseña)
                    s.sendmail(sn.email_remitente, [destinatario], msg.as_string())
            except Exception as _e:
                import logging
                logging.getLogger("marketing").warning(
                    "push alert email falló: %s", _e
                )

        import threading
        threading.Thread(target=_send, daemon=True).start()
        return True
    except Exception as _e:
        import logging
        logging.getLogger("marketing").warning("push alert dispatch falló: %s", _e)
        return False


def _admin_only():
    """Auth + chequeo de admin (solo Sebastian / cuenta administrativa).

    Para endpoints sensibles de debug/troubleshooting que NO deben quedar
    expuestos a Jefferson u otros usuarios de Marketing en producción.
    """
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in ADMIN_USERS:
        return None, jsonify({"error": "Endpoint solo para administradores"}), 403
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


def _ig_check_refresh(conn, allow_network=True):
    """Auto-renueva el token de IG si vence en < 10 dias.
    Funciona con long-lived User Tokens (60 dias) y Page Access Tokens que
    heredan la duracion del User Token. Llama a fb_exchange_token para
    extender automaticamente antes de que expire.
    Retorna dict con estado del token para incluir en la respuesta del dashboard.

    FIX 7-jul (audit ultracode · M43/M59): `allow_network=False` (lo usa el LOAD del dashboard) SALTA el urlopen
    síncrono (hasta 10s → bloqueaba un worker en cada carga si el token estaba por vencer). El refresh real corre
    con `allow_network=True` desde el daemon de métricas de marketing (job_refresh_all_metrics · periódico).
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

    # Intentar refresh si esta cerca de expirar y tenemos las credenciales de la app.
    # allow_network=False (dashboard load) NO hace el urlopen → devuelve el estado sin bloquear el worker.
    if near_expiry and allow_network and raw_token and app_id and app_secret:
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
# ATRIBUCIÓN POR CUPONES — feature 26-may-2026 · "marketing decisional"
# ──────────────────────────────────────────────────────────────────────────────
# Cada campaña/influencer puede tener un código único (ej. ANIMUS_LAURA15) que
# el cliente usa al hacer checkout en Shopify. El webhook ya almacena
# discount_codes en animus_shopify_orders.discount_codes (JSON string).
# Estos endpoints calculan ventas atribuibles en SQL LIKE en tiempo real.

import re as _re_atrib

def _slug_cupon(nombre: str, max_len: int = 12) -> str:
    """Genera un slug SAFE para código de cupón a partir de un nombre.

    Mantiene solo alfanumérico ASCII (Shopify rechaza acentos/espacios en
    discount codes), uppercase, máximo 12 chars · suficiente para distinguir.
    'María Cámila Soto' → 'MARIACAMILA'
    'Día de la Madre 2026' → 'DIADELAMADR'
    """
    s = (nombre or '').strip()
    # Normalizar acentos comunes (sin importar locale)
    _acc = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n','ü':'u',
            'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ñ':'N','Ü':'U'}
    for k, v in _acc.items():
        s = s.replace(k, v)
    # Solo alfanumérico ASCII
    s = _re_atrib.sub(r'[^A-Za-z0-9]', '', s).upper()
    return (s[:max_len] or 'CUPON')


@bp.route('/api/marketing/atribucion')
def mkt_atribucion():
    """Calcula ventas atribuibles a un cupón (influencer/campaña/código libre).

    Query params (uno):
      - codigo:        código exacto a buscar en discount_codes
      - influencer_id: usa el discount_code del influencer
      - campana_id:    usa el discount_code de la campaña
      - desde/hasta:   YYYY-MM-DD (opcional) · filtro de creado_en

    Devuelve:
      - codigo (resuelto), ventas_count, revenue_total, descuento_total,
      - subtotal_pre_descuento, ordenes (sample top 20 con fecha/email/total),
      - roi_implicito si se pasa presupuesto_gastado por query.
    """
    u, err, code = _auth()
    if err: return err, code
    codigo = (request.args.get('codigo') or '').strip()
    inf_id = request.args.get('influencer_id')
    cmp_id = request.args.get('campana_id')
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    conn = _db(); c = conn.cursor()
    # Resolver código si vino por id
    fuente = None
    if inf_id and not codigo:
        row = c.execute(
            "SELECT discount_code, nombre FROM marketing_influencers WHERE id=?",
            (int(inf_id),)
        ).fetchone()
        if not row or not row['discount_code']:
            return jsonify({"error": "Influencer sin discount_code asignado",
                             "influencer_id": int(inf_id),
                             "nombre": row['nombre'] if row else None}), 404
        codigo = row['discount_code']; fuente = {'tipo':'influencer','id':int(inf_id),'nombre':row['nombre']}
    if cmp_id and not codigo:
        row = c.execute(
            "SELECT discount_code, nombre FROM marketing_campanas WHERE id=?",
            (int(cmp_id),)
        ).fetchone()
        if not row or not row['discount_code']:
            return jsonify({"error": "Campaña sin discount_code asignado",
                             "campana_id": int(cmp_id),
                             "nombre": row['nombre'] if row else None}), 404
        codigo = row['discount_code']; fuente = {'tipo':'campana','id':int(cmp_id),'nombre':row['nombre']}
    if not codigo:
        return jsonify({"error": "Pasa codigo, influencer_id o campana_id"}), 400

    # Búsqueda · LIKE %codigo% sobre discount_codes (JSON string).
    # FIX 27-may (P1) · escapar wildcards LIKE para evitar over-attribution.
    # Antes: si user pasaba codigo='%', matcheaba TODOS los cupones · inflaba
    # atribución arbitrariamente. Escape % y _ con char ESCAPE explícito.
    _codigo_safe = codigo.upper().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    where_parts = ["LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')",  # FIX 7-jul: excluir canceladas
                   "UPPER(COALESCE(discount_codes,'')) LIKE ? ESCAPE '\\'"]
    params = [f"%{_codigo_safe}%"]
    if desde:
        where_parts.append("date(creado_en) >= ?"); params.append(desde)
    if hasta:
        where_parts.append("date(creado_en) <= ?"); params.append(hasta)
    where_sql = " AND ".join(where_parts)
    stats = c.execute(f"""
        SELECT COUNT(*) AS n,
               COALESCE(SUM(total),0) AS rev,
               COALESCE(SUM(subtotal),0) AS sub,
               COALESCE(SUM(total_descuentos),0) AS dto
        FROM animus_shopify_orders WHERE {where_sql}
    """, params).fetchone()
    ordenes_top = _fmt_many(c.execute(f"""
        SELECT shopify_id, creado_en, email, total, subtotal, total_descuentos, discount_codes
        FROM animus_shopify_orders
        WHERE {where_sql}
        ORDER BY total DESC LIMIT 20
    """, params).fetchall())
    presupuesto = request.args.get('presupuesto_gastado', type=float) or 0
    revenue = float(stats['rev'] or 0)
    roi_pct = round(((revenue - presupuesto) / presupuesto) * 100, 1) if presupuesto > 0 else None
    return jsonify({
        "codigo": codigo,
        "fuente": fuente,
        "filtros": {"desde": desde or None, "hasta": hasta or None},
        "ventas_count": int(stats['n'] or 0),
        "revenue_total": revenue,
        "subtotal_pre_descuento": float(stats['sub'] or 0),
        "descuento_total": float(stats['dto'] or 0),
        "ordenes_top20": ordenes_top,
        "roi_implicito_pct": roi_pct,
        "presupuesto_gastado": presupuesto if presupuesto > 0 else None,
    })


@bp.route('/api/marketing/campanas/<int:cid>/generar-cupon', methods=['POST'])
def mkt_campana_generar_cupon(cid):
    """Genera o regenera el discount_code de una campaña.

    Body JSON (opcional): {pct: 15, prefijo: 'ANIMUS_', suffix: ''}
      - pct: número que se concatena al final (ej. 15 → ANIMUS_DIAMADRE15)
      - prefijo: default 'ANIMUS_'
      - suffix: si no querés pct, podés pasar suffix custom
      - force: si ya tiene un código, regenera (default false → 409)
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT nombre, discount_code FROM marketing_campanas WHERE id=?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Campaña no encontrada"}), 404
    d = request.get_json(silent=True) or {}
    if row['discount_code'] and not d.get('force'):
        return jsonify({"error": "Campaña ya tiene cupón · reenviar con force=true para regenerar",
                         "discount_code_actual": row['discount_code']}), 409
    prefijo = (d.get('prefijo') or 'ANIMUS_').upper()
    suffix = (d.get('suffix') or '').upper()
    pct = d.get('pct')
    slug = _slug_cupon(row['nombre'], max_len=12)
    if pct is not None:
        try:
            pct_n = int(pct)
            if not (1 <= pct_n <= 99):
                return jsonify({"error": "pct debe estar entre 1 y 99"}), 400
            suffix = str(pct_n)
        except (TypeError, ValueError):
            return jsonify({"error": "pct inválido"}), 400
    codigo = f"{prefijo}{slug}{suffix}"[:32]  # Shopify limit ~255 pero corto es mejor
    # Verificar unicidad cross-campaña/influencer
    existe_c = c.execute("SELECT id, nombre FROM marketing_campanas WHERE discount_code=? AND id!=?", (codigo, cid)).fetchone()
    existe_i = c.execute("SELECT id, nombre FROM marketing_influencers WHERE discount_code=?", (codigo,)).fetchone()
    if existe_c or existe_i:
        return jsonify({"error": "Código ya en uso · usa un suffix distinto",
                         "codigo_propuesto": codigo,
                         "conflicto": {'tipo':'campana','id':existe_c['id'],'nombre':existe_c['nombre']} if existe_c
                                       else {'tipo':'influencer','id':existe_i['id'],'nombre':existe_i['nombre']}}), 409
    antes = {'discount_code': row['discount_code'] or ''}
    c.execute("UPDATE marketing_campanas SET discount_code=? WHERE id=?", (codigo, cid))
    try:
        audit_log(c, usuario=u, accion='CAMPANA_GENERAR_CUPON', tabla='marketing_campanas',
                  registro_id=cid, antes=antes, despues={'discount_code': codigo},
                  detalle=f"Cupón {codigo} asignado a campaña '{row['nombre']}'")
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "discount_code": codigo,
                     "nota": "Crear este código manualmente en Shopify Admin → Descuentos · o vía Shopify API · este endpoint solo lo registra en EOS para atribución."})


@bp.route('/api/marketing/influencers/<int:iid>/generar-cupon', methods=['POST'])
def mkt_influencer_generar_cupon(iid):
    """Genera o regenera el discount_code de un influencer."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    row = c.execute("SELECT nombre, discount_code FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
    if not row:
        return jsonify({"error": "Influencer no encontrado"}), 404
    d = request.get_json(silent=True) or {}
    if row['discount_code'] and not d.get('force'):
        return jsonify({"error": "Influencer ya tiene cupón · reenviar con force=true para regenerar",
                         "discount_code_actual": row['discount_code']}), 409
    prefijo = (d.get('prefijo') or 'ANIMUS_').upper()
    suffix = (d.get('suffix') or '').upper()
    pct = d.get('pct')
    slug = _slug_cupon(row['nombre'], max_len=12)
    if pct is not None:
        try:
            pct_n = int(pct)
            if not (1 <= pct_n <= 99):
                return jsonify({"error": "pct debe estar entre 1 y 99"}), 400
            suffix = str(pct_n)
        except (TypeError, ValueError):
            return jsonify({"error": "pct inválido"}), 400
    codigo = f"{prefijo}{slug}{suffix}"[:32]
    existe_c = c.execute("SELECT id, nombre FROM marketing_campanas WHERE discount_code=?", (codigo,)).fetchone()
    existe_i = c.execute("SELECT id, nombre FROM marketing_influencers WHERE discount_code=? AND id!=?", (codigo, iid)).fetchone()
    if existe_c or existe_i:
        return jsonify({"error": "Código ya en uso · usa un suffix distinto",
                         "codigo_propuesto": codigo,
                         "conflicto": {'tipo':'campana','id':existe_c['id'],'nombre':existe_c['nombre']} if existe_c
                                       else {'tipo':'influencer','id':existe_i['id'],'nombre':existe_i['nombre']}}), 409
    antes = {'discount_code': row['discount_code'] or ''}
    c.execute("UPDATE marketing_influencers SET discount_code=? WHERE id=?", (codigo, iid))
    try:
        audit_log(c, usuario=u, accion='INFLUENCER_GENERAR_CUPON', tabla='marketing_influencers',
                  registro_id=iid, antes=antes, despues={'discount_code': codigo},
                  detalle=f"Cupón {codigo} asignado a influencer '{row['nombre']}'")
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "discount_code": codigo,
                     "nota": "Crear este código manualmente en Shopify Admin → Descuentos · o vía Shopify API · este endpoint solo lo registra en EOS para atribución."})


# ──────────────────────────────────────────────────────────────────────────────
# Flujo urgencia pagos influencers · "promesa 30 días desde contenido"
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/pagos-influencer/urgencias')
def mkt_pagos_influencer_urgencias():
    """Lista pagos Pendientes con flag de urgencia según vence_pago_at.

    Categorías:
      - vencido: vence_pago_at < hoy (incumplimiento promesa)
      - urgente: vence en próximos 7 días
      - proximo: vence en 8-15 días
      - normal: vence en >15 días o no tiene fecha_contenido
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    try:
        # FIX 13-jun (audit influencers · H2/M5): excluir los pagos cuya OC ligada
        # YA está Pagada. Antes filtraba solo pi.estado='Pendiente' crudo, así que
        # si el link pi↔OC quedaba desalineado (OC Pagada pero pi aún Pendiente)
        # el pago aparecía como VENCIDO/urgente acá mientras la lista lo mostraba
        # Pagado → KPI de urgencias divergente. Ahora consistente con la lista.
        rows = c.execute("""
            SELECT id, influencer_id, influencer_nombre, valor, fecha,
                   estado, concepto, numero_oc, fecha_contenido, vence_pago_at
            FROM pagos_influencers
            WHERE estado='Pendiente'
              AND COALESCE(numero_oc,'') NOT IN (
                    SELECT numero_oc FROM ordenes_compra
                    WHERE estado='Pagada' AND COALESCE(numero_oc,'')!='' )
            ORDER BY COALESCE(vence_pago_at, fecha) ASC
            LIMIT 200
        """).fetchall()
    except Exception:
        return jsonify({'pagos': [], 'kpis': {'vencidos': 0, 'urgentes': 0, 'proximos': 0, 'normal': 0},
                         'nota': 'Mig 195 pendiente · ejecutar en /admin/migraciones-pg'}), 200
    from datetime import datetime as _dt, timedelta as _td
    # FIX 13-jun (M24): HOY ancla en Colombia (UTC-5), no _dt.now() (UTC en Render)
    # que de noche CO clasificaba vencido/urgente con un día de corrimiento.
    hoy = _dt.utcnow() - _td(hours=5)
    pagos = []
    kpis = {'vencidos': 0, 'urgentes': 0, 'proximos': 0, 'normal': 0}
    for r in rows:
        d = dict(r)
        vence = (d.get('vence_pago_at') or '').strip()
        urgencia = 'normal'
        dias_para_vencer = None
        if vence and _re_atrib.match(r'^\d{4}-\d{2}-\d{2}$', vence):
            try:
                v = _dt.strptime(vence, '%Y-%m-%d')
                # Fix 28-may · comparar FECHAS (no datetime) · antes hoy=now()
                # con hora hacía que un pago que vence HOY diera days=-1→'vencido'.
                dias_para_vencer = (v.date() - hoy.date()).days
                if dias_para_vencer < 0:
                    urgencia = 'vencido'
                elif dias_para_vencer <= 7:
                    urgencia = 'urgente'
                elif dias_para_vencer <= 15:
                    urgencia = 'proximo'
            except ValueError:
                pass
        d['urgencia'] = urgencia
        d['dias_para_vencer'] = dias_para_vencer
        kpis[urgencia + 's' if urgencia in ('vencido','urgente','proximo') else 'normal'] = \
            kpis.get(urgencia + 's' if urgencia in ('vencido','urgente','proximo') else 'normal', 0) + 1
        pagos.append(d)
    # KPI totales
    kpis['total_pendientes'] = len(rows)
    kpis['valor_vencido_total'] = sum(int(p.get('valor') or 0) for p in pagos if p['urgencia'] == 'vencido')
    return jsonify({'pagos': pagos, 'kpis': kpis,
                     'mensaje_estado': (
                         f"🚨 {kpis['vencidos']} pago(s) ATRASADO(s) · "
                         f"${kpis['valor_vencido_total']:,} en mora"
                         if kpis['vencidos'] > 0
                         else f"✓ Sin pagos atrasados · {kpis['urgentes']} vencen esta semana"
                     )})


# ──────────────────────────────────────────────────────────────────────────────
# Sync Meta Ads · Marketing API · campañas pagadas Facebook/Instagram
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/ads/sync-meta', methods=['POST'])
def mkt_sync_meta_ads():
    """Sincroniza campañas Meta Ads (Facebook/Instagram) desde Marketing API.

    Requiere config en animus_config:
      - meta_ads_access_token: token con permiso ads_read
      - meta_ads_account_id: act_<id> (incluye 'act_' prefix)

    Body opcional: {dias: 30}
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    token = _cfg(conn, "meta_ads_access_token")
    account = _cfg(conn, "meta_ads_account_id")
    if not token or not account:
        return jsonify({
            'error': 'Config Meta Ads incompleta · setear meta_ads_access_token + meta_ads_account_id en animus_config',
            'docs': 'https://developers.facebook.com/docs/marketing-api/insights'
        }), 503
    body = request.get_json(silent=True) or {}
    dias = min(180, max(1, int(body.get('dias') or 30)))
    # Marketing API v19.0 · /campaigns + insights
    sincronizadas = 0
    errores = []
    try:
        # 1) Listar campañas
        url_camp = (f"https://graph.facebook.com/v19.0/{account}/campaigns"
                     f"?fields=id,name,status,objective,start_time,stop_time&limit=200")
        req = urllib.request.Request(url_camp,
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            camp_data = json.loads(r.read().decode("utf-8"))
        campaigns = camp_data.get('data', []) or []
        # 2) Por cada campaña, traer insights
        from datetime import datetime as _dt2, timedelta as _td2
        date_preset = 'last_30d'
        if dias <= 7: date_preset = 'last_7d'
        elif dias <= 14: date_preset = 'last_14d'
        elif dias <= 90: date_preset = 'last_90d'
        for cm in campaigns:
            cid = cm.get('id')
            if not cid: continue
            # FIX 27-may (P2) · skip ARCHIVED y DELETED · sus métricas viejas
            # contaminan el ROI agregado. PAUSED puede tener gasto reciente
            # legítimo de cuando estaba ACTIVE en la ventana · sí cuenta.
            _st = (cm.get('status') or '').upper()
            if _st in ('ARCHIVED', 'DELETED'):
                continue
            try:
                url_ins = (f"https://graph.facebook.com/v19.0/{cid}/insights"
                            f"?fields=spend,impressions,clicks,ctr,cpc,cpm,actions"
                            f"&date_preset={date_preset}")
                reqi = urllib.request.Request(url_ins,
                    headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(reqi, timeout=15) as r2:
                    ins_data = json.loads(r2.read().decode("utf-8"))
                ins_list = ins_data.get('data', []) or []
                ins = ins_list[0] if ins_list else {}
                spend = float(ins.get('spend') or 0)
                impressions = int(ins.get('impressions') or 0)
                clicks = int(ins.get('clicks') or 0)
                ctr = float(ins.get('ctr') or 0)
                cpc = float(ins.get('cpc') or 0)
                cpm = float(ins.get('cpm') or 0)
                # Conversiones: extraer del array 'actions'
                conv = 0
                for act in (ins.get('actions') or []):
                    at = act.get('action_type') or ''
                    if at in ('purchase', 'omni_purchase', 'offsite_conversion.fb_pixel_purchase'):
                        try:
                            conv += int(act.get('value') or 0)
                        except (TypeError, ValueError):
                            pass
                # Upsert
                c.execute("""
                    INSERT INTO marketing_ads_campaigns
                    (platform, external_id, nombre, estado, objetivo,
                     spend_total, impressions, clicks, conversiones,
                     ctr, cpc, cpm, fecha_inicio, fecha_fin, synced_at)
                    VALUES ('meta',?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','-5 hours'))
                    ON CONFLICT(platform, external_id) DO UPDATE SET
                        nombre=excluded.nombre,
                        estado=excluded.estado,
                        objetivo=excluded.objetivo,
                        spend_total=excluded.spend_total,
                        impressions=excluded.impressions,
                        clicks=excluded.clicks,
                        conversiones=excluded.conversiones,
                        ctr=excluded.ctr, cpc=excluded.cpc, cpm=excluded.cpm,
                        fecha_inicio=excluded.fecha_inicio,
                        fecha_fin=excluded.fecha_fin,
                        synced_at=datetime('now','-5 hours')
                """, (cid, cm.get('name','')[:120], cm.get('status',''),
                       cm.get('objective',''), spend, impressions, clicks, conv,
                       ctr, cpc, cpm,
                       (cm.get('start_time') or '')[:10],
                       (cm.get('stop_time') or '')[:10]))
                sincronizadas += 1
            except urllib.error.HTTPError as he:
                detail = he.read().decode('utf-8', errors='replace')[:200]
                errores.append({'campaign_id': cid, 'http': he.code, 'detail': detail})
                log.warning('meta_ads insights cid=%s HTTP %s: %s', cid, he.code, detail)
            except Exception as ce:
                errores.append({'campaign_id': cid, 'error': str(ce)[:200]})
                log.warning('meta_ads insights cid=%s fallo: %s', cid, ce)
        conn.commit()
    except urllib.error.HTTPError as he:
        body_e = he.read().decode('utf-8', errors='replace')[:400]
        return jsonify({'error': f'Meta API HTTP {he.code}', 'detail': body_e}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({
        'ok': True,
        'platform': 'meta',
        'sincronizadas': sincronizadas,
        'errores': errores[:5],
        'errores_total': len(errores),
        'ventana_dias': dias,
    })


@bp.route('/api/marketing/ads/resumen')
def mkt_ads_resumen():
    """KPIs agregados de Meta/Google/TikTok Ads sincronizados.

    Útil para Dashboard cross-paid: spend total · ROAS implícito si tenemos
    revenue Shopify por fecha · top 5 campañas por spend.
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    # Stats por plataforma
    stats = {}
    try:
        for r in c.execute("""
            SELECT platform,
                   COUNT(*) AS n,
                   COALESCE(SUM(spend_total),0) AS spend,
                   COALESCE(SUM(impressions),0) AS imp,
                   COALESCE(SUM(clicks),0) AS clicks,
                   COALESCE(SUM(conversiones),0) AS conv,
                   AVG(NULLIF(ctr,0)) AS ctr_avg,
                   AVG(NULLIF(cpc,0)) AS cpc_avg
            FROM marketing_ads_campaigns
            GROUP BY platform
        """).fetchall():
            stats[r['platform']] = {
                'campaigns_count': int(r['n'] or 0),
                'spend_total': float(r['spend'] or 0),
                'impressions': int(r['imp'] or 0),
                'clicks': int(r['clicks'] or 0),
                'conversiones': int(r['conv'] or 0),
                'ctr_avg': round(float(r['ctr_avg'] or 0), 2),
                'cpc_avg': round(float(r['cpc_avg'] or 0), 2),
            }
    except Exception:
        pass
    # Top 5 campañas por spend
    top_camp = []
    try:
        top_camp = [dict(r) for r in c.execute("""
            SELECT platform, nombre, spend_total, impressions, clicks,
                   conversiones, ctr, cpc, estado
            FROM marketing_ads_campaigns
            WHERE spend_total > 0
            ORDER BY spend_total DESC LIMIT 5
        """).fetchall()]
    except Exception:
        pass
    # Spend total agregado
    spend_total_all = sum(s['spend_total'] for s in stats.values())
    return jsonify({
        'spend_total_all_platforms': spend_total_all,
        'stats_por_plataforma': stats,
        'top_campanas': top_camp,
        'plataformas_configuradas': {
            'meta': bool(_cfg(conn, 'meta_ads_access_token') and _cfg(conn, 'meta_ads_account_id')),
            'google': bool(_cfg(conn, 'google_ads_developer_token') and _cfg(conn, 'google_ads_customer_id')),
            'tiktok': bool(_cfg(conn, 'tiktok_ads_access_token')),
        },
    })


# ──────────────────────────────────────────────────────────────────────────────
# A/B testing creatividades · compara 2 piezas IG con métricas reales
# ──────────────────────────────────────────────────────────────────────────────
def _engagement_score(c_row):
    """Calcula engagement de una pieza marketing_contenido cruzado con IG real.

    Si tiene url_publicacion que matchea con animus_instagram_posts (mig kanban
    auto-sync), usa likes/comentarios/alcance live. Si no, usa los manuales.
    Score = likes + comentarios*3 + alcance/10 (peso típico).
    """
    likes = int(c_row.get('likes') or c_row.get('likes_manual') or 0)
    com = int(c_row.get('comentarios') or c_row.get('comentarios_manual') or 0)
    alc = int(c_row.get('alcance') or c_row.get('alcance_manual') or 0)
    conv = int(c_row.get('conversiones') or 0)
    return {
        'likes': likes, 'comentarios': com, 'alcance': alc, 'conversiones': conv,
        'engagement': likes + com * 3 + alc // 10,
    }


@bp.route('/api/marketing/ab-tests', methods=['GET', 'POST'])
def mkt_ab_tests():
    """GET: lista tests · POST: crear nuevo (2 piezas Kanban).

    Body POST: {nombre, hipotesis, contenido_a_id, contenido_b_id, metrica_objetivo, notas}
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    if request.method == 'GET':
        estado = (request.args.get('estado') or '').strip()
        sql = """
            SELECT t.*,
                   ca.estado as a_estado, ca.url_publicacion as a_url,
                   ca.likes as a_likes, ca.comentarios as a_com, ca.alcance as a_alc,
                   ca.conversiones as a_conv,
                   cb.estado as b_estado, cb.url_publicacion as b_url,
                   cb.likes as b_likes, cb.comentarios as b_com, cb.alcance as b_alc,
                   cb.conversiones as b_conv
            FROM marketing_ab_tests t
            LEFT JOIN marketing_contenido ca ON ca.id = t.contenido_a_id
            LEFT JOIN marketing_contenido cb ON cb.id = t.contenido_b_id
        """
        params = []
        if estado:
            sql += " WHERE t.estado=?"
            params.append(estado)
        sql += " ORDER BY t.fecha_creacion DESC LIMIT 100"
        return jsonify({'tests': [dict(r) for r in c.execute(sql, params).fetchall()]})
    # POST
    d = request.get_json(silent=True) or {}
    nombre = (d.get('nombre') or '').strip()
    a_id = d.get('contenido_a_id')
    b_id = d.get('contenido_b_id')
    if not nombre or not a_id or not b_id:
        return jsonify({'error': 'nombre, contenido_a_id, contenido_b_id requeridos'}), 400
    if a_id == b_id:
        return jsonify({'error': 'a y b deben ser piezas distintas'}), 400
    # Validar que existan
    for cid in (a_id, b_id):
        if not c.execute("SELECT id FROM marketing_contenido WHERE id=?", (int(cid),)).fetchone():
            return jsonify({'error': f'contenido {cid} no existe'}), 404
    metrica = (d.get('metrica_objetivo') or 'engagement').strip()
    if metrica not in ('engagement','clicks','conversiones','alcance'):
        return jsonify({'error': f'metrica_objetivo inválida · debe ser engagement|clicks|conversiones|alcance'}), 400
    try:
        c.execute("""
            INSERT INTO marketing_ab_tests
            (nombre, hipotesis, contenido_a_id, contenido_b_id,
             metrica_objetivo, notas, creado_por)
            VALUES (?,?,?,?,?,?,?)
        """, (nombre[:120], (d.get('hipotesis') or '')[:500],
              int(a_id), int(b_id), metrica,
              (d.get('notas') or '')[:500], u))
        tid = c.lastrowid
        try:
            audit_log(c, usuario=u, accion='CREAR_AB_TEST',
                      tabla='marketing_ab_tests', registro_id=tid,
                      despues={'nombre': nombre[:80], 'a_id': a_id, 'b_id': b_id,
                                'metrica': metrica})
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True, 'id': tid}), 201


@bp.route('/api/marketing/ab-tests/<int:tid>/calcular-ganador', methods=['POST'])
def mkt_ab_test_calcular_ganador(tid):
    """Calcula ganador del test A/B basado en métricas reales (Kanban + IG live).

    Lógica:
      - Trae métricas de las 2 piezas (engagement por defecto)
      - Diferencia % vs base mínima
      - Si diff >20% → ganador claro
      - Si diff 5-20% → ganador con confianza menor
      - Si diff <5% → 'tie'
      - Si una pieza no tiene métricas → 'indeterminado'
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    test = c.execute(
        "SELECT * FROM marketing_ab_tests WHERE id=?", (tid,)).fetchone()
    if not test:
        return jsonify({'error': 'Test no encontrado'}), 404
    t = dict(test)
    # Métricas de cada pieza · usar fusión IG live + manual (igual que kanban)
    def _stats(cid):
        row = c.execute("""
            SELECT mc.id, mc.likes AS likes_manual, mc.comentarios AS comentarios_manual,
                   mc.alcance AS alcance_manual, mc.conversiones, mc.estado,
                   ig.likes AS ig_likes, ig.comentarios AS ig_comentarios, ig.alcance AS ig_alcance
            FROM marketing_contenido mc
            LEFT JOIN animus_instagram_posts ig
              ON COALESCE(mc.url_publicacion,'') != ''
             AND mc.url_publicacion = ig.url_permalink
            WHERE mc.id=?
        """, (cid,)).fetchone()
        if not row:
            return None
        r = dict(row)
        # IG live tiene prioridad sobre manual
        return {
            'likes': int(r.get('ig_likes') or r.get('likes_manual') or 0),
            'comentarios': int(r.get('ig_comentarios') or r.get('comentarios_manual') or 0),
            'alcance': int(r.get('ig_alcance') or r.get('alcance_manual') or 0),
            'conversiones': int(r.get('conversiones') or 0),
            'estado': r.get('estado'),
            'fuente_ig_live': bool(r.get('ig_likes') is not None),
        }
    a = _stats(t['contenido_a_id'])
    b = _stats(t['contenido_b_id'])
    if not a or not b:
        return jsonify({'error': 'Una de las piezas no existe'}), 404
    # Score según métrica objetivo
    metrica = t['metrica_objetivo'] or 'engagement'
    def _score(s):
        if metrica == 'clicks':
            return s['alcance']  # proxy clicks (IG no expone clicks reales)
        if metrica == 'conversiones':
            return s['conversiones']
        if metrica == 'alcance':
            return s['alcance']
        # engagement default
        return s['likes'] + s['comentarios'] * 3 + s['alcance'] // 10
    a_score = _score(a)
    b_score = _score(b)
    # Determinar ganador
    base = max(a_score, b_score, 1)
    diff_pct = round((abs(a_score - b_score) / base) * 100, 1)
    if a_score == 0 and b_score == 0:
        ganadora = 'indeterminado'
    elif diff_pct < 5:
        ganadora = 'tie'
    elif a_score > b_score:
        ganadora = 'a'
    else:
        ganadora = 'b'
    # Update DB
    c.execute("""
        UPDATE marketing_ab_tests
        SET ganadora=?, ganadora_diff_pct=?,
            ganadora_calculado_en=datetime('now','-5 hours'),
            estado=CASE WHEN ? IN ('a','b','tie') THEN 'cerrado' ELSE estado END
        WHERE id=?
    """, (ganadora, diff_pct, ganadora, tid))
    try:
        audit_log(c, usuario=u, accion='CALCULAR_GANADOR_AB_TEST',
                  tabla='marketing_ab_tests', registro_id=tid,
                  despues={'ganadora': ganadora, 'diff_pct': diff_pct,
                            'a_score': a_score, 'b_score': b_score})
    except Exception:
        pass
    conn.commit()
    # Interpretación human-friendly
    if ganadora == 'a':
        msg = f"🏆 Pieza A gana por {diff_pct}% (score {a_score} vs {b_score})"
    elif ganadora == 'b':
        msg = f"🏆 Pieza B gana por {diff_pct}% (score {b_score} vs {a_score})"
    elif ganadora == 'tie':
        msg = f"⚖ Empate técnico (diff {diff_pct}% < 5%) · ambas funcionan similar"
    else:
        msg = "❓ Indeterminado · ninguna pieza tiene métricas suficientes"
    confianza = 'alta' if diff_pct >= 20 else 'media' if diff_pct >= 5 else 'baja'
    return jsonify({
        'ok': True,
        'ganadora': ganadora,
        'diff_pct': diff_pct,
        'a_score': a_score,
        'b_score': b_score,
        'a_stats': a,
        'b_stats': b,
        'metrica_usada': metrica,
        'confianza': confianza,
        'mensaje': msg,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Sentiment analysis · comentarios IG · detección crisis temprana
# ──────────────────────────────────────────────────────────────────────────────
_SENTIMENT_CATS = ('positivo', 'neutro', 'negativo', 'queja', 'pregunta', 'spam')


def _ig_fetch_comments(post_id, token, ig_user_id, limit=50):
    """Trae comentarios de un post IG via Graph API.

    Endpoint: /<post-id>/comments?fields=text,username,timestamp
    Retorna lista de dicts o None si falla.
    """
    try:
        url = (f"https://graph.facebook.com/v18.0/{post_id}/comments"
                f"?fields=id,text,username,timestamp&limit={limit}")
        req = urllib.request.Request(url,
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", []) or []
    except Exception as e:
        log.warning("ig_fetch_comments post=%s fallo: %s", post_id, e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Reportes ejecutivos semanales · email lunes 8am Bogotá
# ──────────────────────────────────────────────────────────────────────────────
def _build_reporte_ejecutivo_data(conn):
    """Recolecta los datos del reporte ejecutivo semanal. Reusable para
    cron + endpoint manual. Retorna dict con todas las secciones."""
    from datetime import datetime as _dt, timedelta as _td
    hoy = _dt.now()
    h7 = (hoy - _td(days=7)).strftime('%Y-%m-%d')
    h14 = (hoy - _td(days=14)).strftime('%Y-%m-%d')
    c = conn.cursor()
    # 1) Revenue Shopify semana actual vs anterior
    rev_7 = c.execute(
        "SELECT COALESCE(SUM(total),0) AS r, COUNT(*) AS n FROM animus_shopify_orders "
        "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?",
        (h7,)).fetchone()
    rev_7_ant = c.execute(
        "SELECT COALESCE(SUM(total),0) AS r, COUNT(*) AS n FROM animus_shopify_orders "
        "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ? AND creado_en < ?", (h14, h7)).fetchone()
    delta_rev = float(rev_7['r'] or 0) - float(rev_7_ant['r'] or 0)
    delta_pct = round((delta_rev / float(rev_7_ant['r'])) * 100, 1) if rev_7_ant['r'] else None
    # 2) Top 3 SKUs por revenue 7d
    top_skus = [dict(r) for r in c.execute("""
        SELECT sku_items AS sku, SUM(total) AS rev, SUM(unidades_total) AS uds
        FROM animus_shopify_orders
        WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?
        GROUP BY sku_items ORDER BY rev DESC LIMIT 3
    """, (h7,)).fetchall()]
    # 3) Top 3 influencers con cupón · revenue atribuible 7d
    influencers_top = []
    try:
        inf_rows = c.execute("""
            SELECT i.id, i.nombre, i.discount_code,
                   (SELECT COUNT(*) FROM animus_shopify_orders o
                    WHERE LOWER(COALESCE(o.estado,'')) NOT IN ('cancelled','cancelado','voided')
                      AND UPPER(COALESCE(o.discount_codes,'')) LIKE '%'||UPPER(i.discount_code)||'%'
                      AND o.creado_en >= ?) AS pedidos,
                   (SELECT COALESCE(SUM(o.total),0) FROM animus_shopify_orders o
                    WHERE LOWER(COALESCE(o.estado,'')) NOT IN ('cancelled','cancelado','voided')
                      AND UPPER(COALESCE(o.discount_codes,'')) LIKE '%'||UPPER(i.discount_code)||'%'
                      AND o.creado_en >= ?) AS revenue
            FROM marketing_influencers i
            WHERE COALESCE(i.discount_code,'') != ''
            ORDER BY revenue DESC LIMIT 3
        """, (h7, h7)).fetchall()
        influencers_top = [dict(r) for r in inf_rows if r['revenue'] and float(r['revenue']) > 0]
    except Exception:
        pass
    # 4) Alertas stock críticas (≤7d cobertura)
    alertas_stock = []
    try:
        h30 = (hoy - _td(days=30)).strftime('%Y-%m-%d')
        for r in c.execute("""
            SELECT sku, SUM(unidades_disponible) AS stock
            FROM stock_pt WHERE estado='Disponible' GROUP BY sku
        """).fetchall():
            sku, stock = r['sku'], r['stock'] or 0
            if not sku:
                continue
            dem = c.execute(
                "SELECT COALESCE(SUM(unidades),0) AS t FROM liberaciones WHERE sku=? AND creado_en>=?",
                (sku, h30)).fetchone()['t']
            shop = c.execute(
                "SELECT COALESCE(SUM(unidades_total),0) AS t FROM animus_shopify_orders "
                "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND sku_items LIKE ? AND creado_en>=?",
                (f'%{sku}%', h30)).fetchone()['t']
            demanda = (dem + shop) / 30.0
            if demanda > 0:
                dias_cob = stock / demanda
                if dias_cob <= 7:
                    alertas_stock.append({'sku': sku, 'stock': stock,
                                            'dias_cobertura': round(dias_cob, 1)})
        alertas_stock.sort(key=lambda x: x['dias_cobertura'])
        alertas_stock = alertas_stock[:5]
    except Exception:
        pass
    # 5) Eventos cosméticos próximos ≤30d
    eventos_prox = []
    for ev in _get_calendario_cosmetico(conn):
        try:
            d = (_dt.strptime(ev['fecha'], '%Y-%m-%d') - hoy).days
            if 0 <= d <= 30:
                eventos_prox.append({**ev, 'dias_restantes': d})
        except Exception:
            continue
    eventos_prox.sort(key=lambda x: x['dias_restantes'])
    # 6) Meta progreso mes actual
    mes = hoy.strftime('%Y-%m')
    meta_row = c.execute("SELECT * FROM marketing_metas WHERE mes=?", (mes,)).fetchone()
    meta_block = None
    if meta_row:
        sh_mes = c.execute(
            "SELECT COALESCE(SUM(total),0) AS rev, COUNT(*) AS ped "
            "FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND substr(creado_en,1,7)=?",
            (mes,)).fetchone()
        rev_meta = float(meta_row['revenue_meta'] or 0)
        meta_block = {
            'mes': mes,
            'revenue_meta': rev_meta,
            'revenue_real': float(sh_mes['rev'] or 0),
            'revenue_pct': round(float(sh_mes['rev']) / rev_meta * 100, 1) if rev_meta > 0 else None,
            'pedidos_meta': meta_row['pedidos_meta'],
            'pedidos_real': int(sh_mes['ped'] or 0),
        }
    # 7) Pedidos B2B próximos a despachar
    b2b_proximos = [dict(r) for r in c.execute("""
        SELECT cliente_nombre, producto_nombre, cantidad_uds, fecha_estimada, estado
        FROM pedidos_b2b
        WHERE COALESCE(estado,'') IN ('confirmado','en_produccion')
        ORDER BY fecha_estimada LIMIT 5
    """).fetchall()]
    return {
        'generado_en': hoy.strftime('%Y-%m-%d %H:%M'),
        'semana_actual': {
            'revenue': round(float(rev_7['r'] or 0), 0),
            'pedidos': int(rev_7['n'] or 0),
        },
        'semana_anterior': {
            'revenue': round(float(rev_7_ant['r'] or 0), 0),
            'pedidos': int(rev_7_ant['n'] or 0),
        },
        'delta_revenue': round(delta_rev, 0),
        'delta_pct': delta_pct,
        'top_skus': top_skus,
        'top_influencers': influencers_top,
        'alertas_stock': alertas_stock,
        'eventos_proximos': eventos_prox,
        'meta_mes': meta_block,
        'b2b_proximos': b2b_proximos,
    }


def _build_reporte_ejecutivo_html(data):
    """Construye el HTML del reporte ejecutivo desde el dict de datos."""
    fmt_cop = lambda v: f"${int(v):,}".replace(',', '.')
    sa = data['semana_actual']
    sant = data['semana_anterior']
    delta = data['delta_revenue']
    delta_pct = data['delta_pct']
    delta_col = '#10b981' if delta >= 0 else '#ef4444'
    delta_str = (f"<span style='color:{delta_col};font-weight:700'>"
                  f"{'+' if delta >= 0 else ''}{fmt_cop(delta)}"
                  f"{f' ({delta_pct:+}%)' if delta_pct is not None else ''}</span>")
    # SKUs
    skus_html = '<p style="color:#94a3b8">Sin ventas esta semana</p>' if not data['top_skus'] else (
        '<ol style="padding-left:18px">' +
        ''.join(f"<li><b>{s['sku']}</b> · {fmt_cop(s['rev'])} ({int(s['uds'] or 0)} uds)</li>"
                for s in data['top_skus']) +
        '</ol>'
    )
    # Influencers
    inf_html = '<p style="color:#94a3b8">Ningún influencer con cupón generó ventas esta semana</p>' if not data['top_influencers'] else (
        '<ol style="padding-left:18px">' +
        ''.join(f"<li><b>{i['nombre']}</b> ({i['discount_code']}) · {fmt_cop(i['revenue'])} en {int(i['pedidos'])} pedidos</li>"
                for i in data['top_influencers']) +
        '</ol>'
    )
    # Alertas stock
    if not data['alertas_stock']:
        stock_html = '<p style="color:#10b981">✅ Sin alertas críticas de stock</p>'
    else:
        stock_html = ('<ul style="padding-left:18px">' +
            ''.join(f"<li>⚠ <b>{a['sku']}</b>: {int(a['stock'])} uds · {a['dias_cobertura']}d cobertura</li>"
                    for a in data['alertas_stock']) + '</ul>')
    # Eventos
    if not data['eventos_proximos']:
        ev_html = '<p style="color:#94a3b8">Sin eventos cosméticos en próximos 30 días</p>'
    else:
        ev_html = '<ul style="padding-left:18px">' + ''.join(
            f"<li>📅 <b>{e['evento']}</b> · {e['fecha']} ({e['dias_restantes']}d) · ×{e['multiplicador']}</li>"
            for e in data['eventos_proximos']) + '</ul>'
    # Meta
    meta_html = ''
    if data.get('meta_mes'):
        m = data['meta_mes']
        meta_html = (
            f"<h3 style='color:#10b981;margin-top:20px'>🎯 Meta del mes ({m['mes']})</h3>"
            f"<p>Revenue: <b>{fmt_cop(m['revenue_real'])}</b> / "
            f"<span style='color:#94a3b8'>{fmt_cop(m['revenue_meta'])}</span>"
            f" ({m['revenue_pct'] or '—'}%) · Pedidos: <b>{m['pedidos_real']}</b> / {m['pedidos_meta']}</p>"
        )
    # B2B
    b2b_html = ''
    if data['b2b_proximos']:
        b2b_html = ("<h3 style='color:#a78bfa;margin-top:20px'>📦 Pedidos B2B próximos</h3>"
            "<ul style='padding-left:18px'>" +
            ''.join(f"<li><b>{p['cliente_nombre']}</b>: {int(p['cantidad_uds'])} uds {p['producto_nombre']} "
                    f"({p['fecha_estimada'] or 'sin fecha'} · {p['estado']})</li>"
                    for p in data['b2b_proximos']) + '</ul>')
    return f"""<html><body style="font-family:Arial,sans-serif;max-width:680px;margin:auto;background:#0f172a;color:#f1f5f9;padding:30px;border-radius:12px">
<div style="border-bottom:2px solid #d4af37;padding-bottom:16px;margin-bottom:24px">
  <div style="font-size:11px;color:#d4af37;font-weight:700;letter-spacing:.15em;text-transform:uppercase">ÁNIMUS LAB · HHA Group</div>
  <h1 style="color:#fff;margin:4px 0 0;font-size:24px">Reporte ejecutivo semanal</h1>
  <p style="color:#94a3b8;margin:4px 0 0;font-size:13px">Generado {data['generado_en']}</p>
</div>

<h2 style="color:#fff;font-size:18px">💰 Ventas Shopify (últimos 7 días)</h2>
<table style="width:100%;border-collapse:collapse;margin:12px 0">
  <tr>
    <td style="padding:10px;background:#1e293b;border-radius:8px 0 0 8px">
      <div style="font-size:10px;color:#94a3b8;text-transform:uppercase">Revenue</div>
      <div style="font-size:22px;font-weight:800">{fmt_cop(sa['revenue'])}</div>
      <div style="font-size:11px;color:#94a3b8">vs sem. anterior: {delta_str}</div>
    </td>
    <td style="padding:10px;background:#1e293b;border-left:1px solid #334155;border-radius:0 8px 8px 0">
      <div style="font-size:10px;color:#94a3b8;text-transform:uppercase">Pedidos</div>
      <div style="font-size:22px;font-weight:800">{sa['pedidos']}</div>
      <div style="font-size:11px;color:#94a3b8">anterior: {sant['pedidos']}</div>
    </td>
  </tr>
</table>

<h3 style="color:#d4af37;margin-top:24px">🏆 Top 3 SKUs por revenue</h3>
{skus_html}

<h3 style="color:#a78bfa;margin-top:20px">👥 Top 3 influencers · revenue atribuible</h3>
{inf_html}

<h3 style="color:#f59e0b;margin-top:20px">⚠ Alertas de stock crítico (≤7d cobertura)</h3>
{stock_html}

<h3 style="color:#34d399;margin-top:20px">📅 Eventos cosméticos próximos (≤30d)</h3>
{ev_html}

{meta_html}

{b2b_html}

<div style="margin-top:32px;padding-top:16px;border-top:1px solid #334155;font-size:11px;color:#64748b">
  Generado automáticamente por el módulo Marketing de EOS · HHA Group<br>
  Configurá metas mensuales y cupones en <a href="https://app.eossuite.com/marketing" style="color:#a78bfa">/marketing</a>
</div>
</body></html>"""


@bp.route('/api/marketing/reporte-ejecutivo-semanal', methods=['GET', 'POST'])
def mkt_reporte_ejecutivo_semanal():
    """GET: devuelve HTML del reporte para preview.
    POST: además lo envía por email (body: {destinatarios: ['x@y.com']}).
    Si no se pasan destinatarios, usa REPORTE_EJECUTIVO_EMAIL env var.
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    data = _build_reporte_ejecutivo_data(conn)
    html = _build_reporte_ejecutivo_html(data)
    if request.method == 'GET':
        # Preview · devolver HTML directo
        return Response(html, mimetype='text/html')
    # POST · enviar por email
    body = request.get_json(silent=True) or {}
    dests = body.get('destinatarios') or []
    if not dests:
        env_d = (os.environ.get('REPORTE_EJECUTIVO_EMAIL') or '').strip()
        if env_d:
            dests = [d.strip() for d in env_d.split(',') if d.strip()]
    if not dests:
        return jsonify({'error': 'Sin destinatarios · pasalos en body o configurá REPORTE_EJECUTIVO_EMAIL env var'}), 400
    try:
        from notificaciones import SistemaNotificaciones
        sn = SistemaNotificaciones()
        if not sn.email_remitente or not sn.contraseña:
            return jsonify({'error': 'SMTP no configurado en notificaciones'}), 503
        import smtplib, ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        enviados = 0
        for dest in dests:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"[ÁNIMUS] Reporte ejecutivo semanal · {data['generado_en'][:10]}"
                msg['From'] = sn.email_remitente
                msg['To'] = dest
                msg.attach(MIMEText(html, 'html', 'utf-8'))
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(sn.smtp_server, sn.smtp_port, context=ctx) as s:
                    s.login(sn.email_remitente, sn.contraseña)
                    s.sendmail(sn.email_remitente, [dest], msg.as_string())
                enviados += 1
            except Exception as e:
                log.warning('reporte ejecutivo email a %s fallo: %s', dest, e)
        return jsonify({'ok': True, 'enviados': enviados, 'destinatarios': dests,
                         'preview_data': data})
    except Exception as e:
        return jsonify({'error': f'Send email fallo: {e}'}), 500


# ──────────────────────────────────────────────────────────────────────────────
# LTV por cliente · agrupa Shopify orders por email · tier automático
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/ltv-clientes')
def mkt_ltv_clientes():
    """Ranking de clientes por LTV (Lifetime Value) desde Shopify orders.

    Params:
      - tier: VIP | Recurrente | One-shot | Dormido (filtro)
      - min_orders: solo clientes con ≥ N pedidos (default 1)
      - limit: max filas (default 50, max 500)
      - sort: ltv | frecuencia | ultimo_pedido (default ltv desc)

    Devuelve por cliente: email, pedidos_count, ltv (revenue total),
    ticket_promedio, primer_pedido, ultimo_pedido, dias_desde_ultimo,
    intervalo_promedio_dias, tier, riesgo_perdida (bool).
    """
    u, err, code = _auth()
    if err: return err, code
    tier_filtro = (request.args.get('tier') or '').strip()
    min_orders = max(1, int(request.args.get('min_orders') or 1))
    limit = min(500, max(1, int(request.args.get('limit') or 50)))
    sort = (request.args.get('sort') or 'ltv').lower()
    conn = _db(); c = conn.cursor()
    # Agrupado por email · stats agregadas
    rows = c.execute("""
        SELECT LOWER(email) AS email,
               COUNT(*) AS pedidos_count,
               COALESCE(SUM(total),0) AS ltv,
               COALESCE(AVG(total),0) AS ticket_promedio,
               MIN(creado_en) AS primer_pedido,
               MAX(creado_en) AS ultimo_pedido,
               COUNT(DISTINCT substr(creado_en,1,7)) AS meses_activos
        FROM animus_shopify_orders
        WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND COALESCE(email,'') != ''
        GROUP BY LOWER(email)
        HAVING pedidos_count >= ?
    """, (min_orders,)).fetchall()
    clientes = []
    from datetime import datetime as _dt
    hoy = _dt.now()
    for r in rows:
        ltv = float(r['ltv'] or 0)
        cnt = int(r['pedidos_count'] or 0)
        primer = r['primer_pedido'] or ''
        ultimo = r['ultimo_pedido'] or ''
        # Intervalo promedio entre pedidos
        try:
            if primer and ultimo and cnt > 1:
                d1 = _dt.strptime(primer[:10], '%Y-%m-%d')
                d2 = _dt.strptime(ultimo[:10], '%Y-%m-%d')
                intervalo = (d2 - d1).days / max(cnt - 1, 1)
            else:
                intervalo = 0
        except (ValueError, TypeError):
            intervalo = 0
        # Días desde último pedido
        try:
            dias_desde = (hoy - _dt.strptime(ultimo[:10], '%Y-%m-%d')).days if ultimo else 999
        except (ValueError, TypeError):
            dias_desde = 999
        # Tier automático por LTV + frecuencia
        if ltv >= 2_000_000:
            tier = 'VIP'
        elif ltv >= 500_000 or cnt >= 3:
            tier = 'Recurrente'
        elif cnt == 1:
            tier = 'One-shot'
        else:
            tier = 'Recurrente'
        # Detectar dormido: >90 días sin comprar + tenía recurrencia previa
        if dias_desde > 90 and cnt >= 2:
            tier = 'Dormido'
        # Riesgo perdida: cliente recurrente o VIP con días_desde > 2× intervalo
        riesgo = (tier in ('VIP', 'Recurrente') and intervalo > 0
                   and dias_desde > intervalo * 2)
        clientes.append({
            'email': r['email'],
            'pedidos_count': cnt,
            'ltv': round(ltv, 0),
            'ticket_promedio': round(float(r['ticket_promedio'] or 0), 0),
            'primer_pedido': primer[:10] if primer else None,
            'ultimo_pedido': ultimo[:10] if ultimo else None,
            'dias_desde_ultimo': dias_desde,
            'intervalo_promedio_dias': round(intervalo, 1),
            'meses_activos': int(r['meses_activos'] or 0),
            'tier': tier,
            'riesgo_perdida': riesgo,
        })
    # Filtro tier
    if tier_filtro:
        clientes = [c2 for c2 in clientes if c2['tier'] == tier_filtro]
    # Sort
    if sort == 'frecuencia':
        clientes.sort(key=lambda x: -x['pedidos_count'])
    elif sort == 'ultimo_pedido':
        clientes.sort(key=lambda x: x['dias_desde_ultimo'])
    else:  # ltv
        clientes.sort(key=lambda x: -x['ltv'])
    # KPIs agregados
    total = len(clientes)
    revenue_total = sum(c2['ltv'] for c2 in clientes)
    kpis = {
        'total_clientes': total,
        'revenue_total': round(revenue_total, 0),
        'ticket_promedio_global': round(revenue_total / total, 0) if total > 0 else 0,
        'distribucion_tier': {
            t: len([c2 for c2 in clientes if c2['tier'] == t])
            for t in ('VIP', 'Recurrente', 'One-shot', 'Dormido')
        },
        'en_riesgo_perdida': len([c2 for c2 in clientes if c2['riesgo_perdida']]),
    }
    return jsonify({
        'kpis': kpis,
        'clientes': clientes[:limit],
        'mostrando': min(limit, total),
        'filtros': {'tier': tier_filtro or None, 'min_orders': min_orders, 'sort': sort},
    })


# ──────────────────────────────────────────────────────────────────────────────
# Time-of-day optimization · mejor día/hora para publicar IG
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/optimo-publicacion')
def mkt_optimo_publicacion():
    """Analiza animus_instagram_posts y devuelve mejor día/hora por engagement.

    Engagement = likes + comentarios*3 (peso convencional · comments > likes).
    Devuelve heatmap data + top 5 horarios + tipo de post recomendado por slot.

    Query: ?dias=180 (default · ventana de análisis)
    """
    u, err, code = _auth()
    if err: return err, code
    dias = min(720, max(30, int(request.args.get('dias') or 180)))
    from datetime import datetime as _dt, timedelta as _td
    hace = (_dt.now() - _td(days=dias)).strftime('%Y-%m-%d')
    conn = _db(); c = conn.cursor()
    posts = c.execute("""
        SELECT tipo, descripcion, likes, comentarios, alcance,
               publicado_en
        FROM animus_instagram_posts
        WHERE COALESCE(publicado_en,'') != '' AND publicado_en >= ?
    """, (hace,)).fetchall()
    if not posts:
        return jsonify({
            'mensaje': 'Sin posts en ventana · sincroniza IG primero',
            'ventana_dias': dias,
            'posts_count': 0,
        })
    # Buckets: dia_semana (0=Lun, 6=Dom) × hora (0-23)
    DIAS_ES = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
    buckets = {}  # key (dia, hora) → [list of engagements]
    by_tipo = {}  # key tipo → [engagements]
    for p in posts:
        try:
            dt = _dt.strptime((p['publicado_en'] or '')[:19], '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                dt = _dt.strptime((p['publicado_en'] or '')[:10], '%Y-%m-%d')
            except (ValueError, TypeError):
                continue
        eng = int(p['likes'] or 0) + int(p['comentarios'] or 0) * 3
        key = (dt.weekday(), dt.hour)
        buckets.setdefault(key, []).append(eng)
        tipo = p['tipo'] or 'IMAGE'
        by_tipo.setdefault(tipo, []).append(eng)
    # Heatmap: lista de {dia, dia_nombre, hora, engagement_avg, posts_count}
    heatmap = []
    for (d, h), engs in buckets.items():
        heatmap.append({
            'dia': d,
            'dia_nombre': DIAS_ES[d],
            'hora': h,
            'engagement_avg': round(sum(engs) / len(engs), 1),
            'engagement_max': max(engs),
            'posts_count': len(engs),
        })
    # Top 5 horarios (min 2 posts para ser señal · evitar 1 outlier)
    top_horarios = sorted(
        [b for b in heatmap if b['posts_count'] >= 2],
        key=lambda x: -x['engagement_avg']
    )[:5]
    # Si no hay slots con ≥2 posts, tomar top 5 cualquier
    if not top_horarios:
        top_horarios = sorted(heatmap, key=lambda x: -x['engagement_avg'])[:5]
    # Mejor tipo de post
    tipo_stats = []
    for tipo, engs in by_tipo.items():
        if len(engs) >= 2:
            tipo_stats.append({
                'tipo': tipo,
                'engagement_avg': round(sum(engs) / len(engs), 1),
                'posts_count': len(engs),
            })
    tipo_stats.sort(key=lambda x: -x['engagement_avg'])
    # Recomendación texto
    if top_horarios:
        mejor = top_horarios[0]
        recomendacion = (
            f"Mejor publicar **{mejor['dia_nombre']} a las {mejor['hora']:02d}:00**: "
            f"engagement promedio {mejor['engagement_avg']:.0f} ({mejor['posts_count']} posts analizados). "
        )
        if tipo_stats:
            recomendacion += f"Formato con mejor desempeño: {tipo_stats[0]['tipo']} ({tipo_stats[0]['engagement_avg']:.0f} eng prom)."
    else:
        recomendacion = "Datos insuficientes para recomendación · publicá más para tener señal."
    return jsonify({
        'ventana_dias': dias,
        'posts_count': len(posts),
        'heatmap': heatmap,
        'top_horarios': top_horarios,
        'top_tipos': tipo_stats,
        'recomendacion': recomendacion,
    })


# ──────────────────────────────────────────────────────────────────────────────
# CONTACTO 360º · vista unificada GHL + Shopify + Pedidos B2B + Influencer
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/contacto-360')
def mkt_contacto_360():
    """Vista unificada de un contacto cruzando 4 fuentes:
       - GHL contact + opportunities + tags
       - Shopify orders (revenue, frecuencia, primer/último pedido)
       - Pedidos B2B (si es cliente mayorista)
       - Influencer record (si está en marketing_influencers)

    Query: ?email=cliente@example.com (obligatorio)
    """
    u, err, code = _auth()
    if err: return err, code
    email = (request.args.get('email') or '').strip().lower()
    if not email:
        return jsonify({"error": "email requerido (?email=)"}), 400
    conn = _db(); c = conn.cursor()
    # 1) GHL contact
    ghl_contact = None
    try:
        row = c.execute(
            "SELECT * FROM animus_ghl_contacts WHERE LOWER(email)=? LIMIT 1",
            (email,)).fetchone()
        if row:
            ghl_contact = dict(row)
    except Exception:
        pass
    # 2) GHL opportunities (asociadas al contact_id si existe)
    ghl_opps = []
    if ghl_contact and ghl_contact.get('ghl_id'):
        try:
            ghl_opps = [dict(r) for r in c.execute("""
                SELECT ghl_id, nombre, pipeline_nombre, stage_nombre, status,
                       monetary_value, ghl_updated_at
                FROM animus_ghl_opportunities WHERE ghl_contact_id=?
                ORDER BY ghl_updated_at DESC LIMIT 20
            """, (ghl_contact['ghl_id'],)).fetchall()]
        except Exception:
            pass
    # 3) Shopify · orders del email
    shopify = {"orders": [], "stats": {}}
    try:
        sh_orders = [dict(r) for r in c.execute("""
            SELECT shopify_id, creado_en, total, subtotal, total_descuentos,
                   discount_codes, sku_items, unidades_total
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND LOWER(email)=?
            ORDER BY creado_en DESC LIMIT 50
        """, (email,)).fetchall()]
        shopify["orders"] = sh_orders
        if sh_orders:
            tot = sum(float(o.get("total") or 0) for o in sh_orders)
            shopify["stats"] = {
                "orders_count": len(sh_orders),
                "revenue_total": round(tot, 0),
                "ticket_promedio": round(tot / len(sh_orders), 0),
                "primer_pedido": min((o.get("creado_en") or "") for o in sh_orders),
                "ultimo_pedido": max((o.get("creado_en") or "") for o in sh_orders),
            }
    except Exception:
        pass
    # 4) Pedidos B2B · si email está vinculado a cliente_b2b (notas/cliente_nombre LIKE)
    b2b = {"pedidos": [], "stats": {}}
    try:
        nombre_match = ghl_contact.get("nombre") if ghl_contact else None
        if nombre_match:
            ped_rows = c.execute("""
                SELECT id, cliente_id, cliente_nombre, producto_nombre,
                       cantidad_uds, ml_unidad, estado, fecha_estimada, creado_at_utc
                FROM pedidos_b2b WHERE LOWER(cliente_nombre) LIKE ?
                ORDER BY creado_at_utc DESC LIMIT 30
            """, (f"%{nombre_match.lower()}%",)).fetchall()
            b2b["pedidos"] = [dict(r) for r in ped_rows]
            if ped_rows:
                b2b["stats"] = {
                    "pedidos_count": len(ped_rows),
                    "uds_total": sum(int(r["cantidad_uds"] or 0) for r in ped_rows),
                    "ultimo_pedido": max((r["creado_at_utc"] or "") for r in ped_rows),
                }
    except Exception:
        pass
    # 5) ¿Es influencer?
    influencer = None
    try:
        ir = c.execute(
            "SELECT id, nombre, red_social, usuario_red, estado, discount_code, seguidores "
            "FROM marketing_influencers WHERE LOWER(email)=? LIMIT 1",
            (email,)).fetchone()
        if ir:
            influencer = dict(ir)
            # Revenue atribuible si tiene cupón
            dcode = (influencer.get("discount_code") or "").strip()
            if dcode:
                atr = c.execute("""
                    SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS rev
                    FROM animus_shopify_orders
                    WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                      AND UPPER(COALESCE(discount_codes,'')) LIKE ?
                """, (f"%{dcode.upper()}%",)).fetchone()
                influencer["revenue_atribuible"] = float(atr["rev"] or 0)
                influencer["pedidos_atribuibles"] = int(atr["n"] or 0)
    except Exception:
        pass
    # 6) Score relacional · simple LTV agregado
    revenue_dtc = float((shopify.get("stats") or {}).get("revenue_total") or 0)
    revenue_b2b_uds = int((b2b.get("stats") or {}).get("uds_total") or 0)
    # LTV crude · suma revenue DTC + estimación B2B (uds * 5000 ml * 0.5 USD avg)
    ltv_aprox = revenue_dtc + (revenue_b2b_uds * 25000)  # heurística colombiana
    return jsonify({
        "email": email,
        "ghl_contact": ghl_contact,
        "ghl_opportunities": ghl_opps,
        "shopify": shopify,
        "b2b": b2b,
        "es_influencer": bool(influencer),
        "influencer": influencer,
        "ltv_aproximado": round(ltv_aprox, 0),
        "tier_sugerido": (
            "VIP" if ltv_aprox >= 2_000_000 else
            "Recurrente" if ltv_aprox >= 500_000 else
            "One-shot" if ltv_aprox > 0 else
            "Lead"
        ),
        "nota": "LTV es heurística simple (DTC real + B2B uds × $25k) · refinar con costo real de producto",
    })


# ──────────────────────────────────────────────────────────────────────────────
# CALENDARIO COSMÉTICO · CRUD editable (mig 186)
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/eventos-calendario', methods=['GET', 'POST'])
def mkt_eventos_calendario():
    """GET: lista eventos activos. POST: crea evento nuevo."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    if request.method == 'GET':
        incl_inactivos = (request.args.get('incluir_inactivos') or '').lower() in ('1','true','yes')
        sql = "SELECT id, evento, fecha, color, multiplicador, activo, notas FROM marketing_eventos_calendario"
        if not incl_inactivos:
            sql += " WHERE COALESCE(activo,1)=1"
        sql += " ORDER BY fecha"
        rows = [dict(r) for r in c.execute(sql).fetchall()]
        return jsonify({"eventos": rows, "total": len(rows)})
    # POST
    d = request.get_json(silent=True) or {}
    evento = (d.get('evento') or '').strip()
    fecha = (d.get('fecha') or '').strip()
    color = (d.get('color') or '#94a3b8').strip()
    notas = (d.get('notas') or '').strip()[:300]
    if not evento or not fecha:
        return jsonify({"error": "evento y fecha (YYYY-MM-DD) requeridos"}), 400
    if not _re_atrib.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
        return jsonify({"error": "fecha debe ser YYYY-MM-DD"}), 400
    try:
        mult = float(d.get('multiplicador', 1.0))
        if not (0 < mult <= 10):
            return jsonify({"error": "multiplicador debe estar en (0, 10]"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "multiplicador inválido"}), 400
    try:
        c.execute("""INSERT INTO marketing_eventos_calendario
                     (evento, fecha, color, multiplicador, notas, creado_por)
                     VALUES (?,?,?,?,?,?)""",
                  (evento[:120], fecha, color[:20], mult, notas, u))
        eid = c.lastrowid
        try:
            audit_log(c, usuario=u, accion='CREAR_EVENTO_CALENDARIO',
                      tabla='marketing_eventos_calendario', registro_id=eid,
                      despues={'evento': evento[:80], 'fecha': fecha, 'multiplicador': mult})
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        msg = str(e)
        if 'UNIQUE' in msg.upper():
            return jsonify({"error": f"Ya existe '{evento}' en {fecha}"}), 409
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "id": eid}), 201


@bp.route('/api/marketing/eventos-calendario/<int:eid>', methods=['PUT', 'DELETE'])
def mkt_evento_calendario_detail(eid):
    """PUT: actualiza. DELETE: soft delete (activo=0)."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    ant_row = c.execute(
        "SELECT evento, fecha, color, multiplicador, activo FROM marketing_eventos_calendario WHERE id=?",
        (eid,)).fetchone()
    if not ant_row:
        return jsonify({"error": "Evento no encontrado"}), 404
    antes = dict(ant_row)
    if request.method == 'DELETE':
        c.execute("UPDATE marketing_eventos_calendario SET activo=0 WHERE id=?", (eid,))
        try:
            audit_log(c, usuario=u, accion='DESACTIVAR_EVENTO_CALENDARIO',
                      tabla='marketing_eventos_calendario', registro_id=eid,
                      antes=antes, despues={'activo': 0})
        except Exception:
            pass
        conn.commit()
        return jsonify({"ok": True, "id": eid, "activo": False})
    # PUT
    d = request.get_json(silent=True) or {}
    sets = []; params = []
    if 'evento' in d:
        ev = (d['evento'] or '').strip()
        if not ev:
            return jsonify({"error": "evento no puede ser vacío"}), 400
        sets.append("evento=?"); params.append(ev[:120])
    if 'fecha' in d:
        fc = (d['fecha'] or '').strip()
        if not _re_atrib.match(r'^\d{4}-\d{2}-\d{2}$', fc):
            return jsonify({"error": "fecha debe ser YYYY-MM-DD"}), 400
        sets.append("fecha=?"); params.append(fc)
    if 'color' in d:
        sets.append("color=?"); params.append((d['color'] or '#94a3b8')[:20])
    if 'multiplicador' in d:
        try:
            mult = float(d['multiplicador'])
            if not (0 < mult <= 10):
                return jsonify({"error": "multiplicador debe estar en (0, 10]"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "multiplicador inválido"}), 400
        sets.append("multiplicador=?"); params.append(mult)
    if 'activo' in d:
        sets.append("activo=?"); params.append(1 if d['activo'] else 0)
    if 'notas' in d:
        sets.append("notas=?"); params.append((d['notas'] or '')[:300])
    if not sets:
        return jsonify({"error": "Nada que actualizar"}), 400
    params.append(eid)
    c.execute(f"UPDATE marketing_eventos_calendario SET {', '.join(sets)} WHERE id=?", params)
    try:
        audit_log(c, usuario=u, accion='ACTUALIZAR_EVENTO_CALENDARIO',
                  tabla='marketing_eventos_calendario', registro_id=eid,
                  antes=antes, despues={k: d[k] for k in d if k in
                                          ('evento','fecha','color','multiplicador','activo','notas')})
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "id": eid})


# ──────────────────────────────────────────────────────────────────────────────
# METAS MENSUALES · CRUD + progreso vs Shopify (mig 187)
# ──────────────────────────────────────────────────────────────────────────────
@bp.route('/api/marketing/metas', methods=['GET', 'POST'])
def mkt_metas():
    """GET: lista metas (todas o mes específico ?mes=YYYY-MM).
    POST: upsert meta del mes."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    if request.method == 'GET':
        mes = (request.args.get('mes') or '').strip()
        if mes:
            row = c.execute("SELECT * FROM marketing_metas WHERE mes=?", (mes,)).fetchone()
            return jsonify({"meta": dict(row) if row else None})
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM marketing_metas ORDER BY mes DESC LIMIT 24"
        ).fetchall()]
        return jsonify({"metas": rows, "total": len(rows)})
    # POST upsert
    d = request.get_json(silent=True) or {}
    mes = (d.get('mes') or '').strip()
    if not _re_atrib.match(r'^\d{4}-\d{2}$', mes):
        return jsonify({"error": "mes debe ser YYYY-MM"}), 400
    from http_helpers import validate_money as _vm_meta
    rev, e1 = _vm_meta(d.get('revenue_meta', 0), allow_zero=True,
                       max_value=1e12, field_name='revenue_meta')
    if e1: return jsonify(e1), 400
    try:
        ped = int(d.get('pedidos_meta', 0) or 0)
        cln = int(d.get('clientes_nuevos_meta', 0) or 0)
        if ped < 0 or cln < 0:
            return jsonify({"error": "valores no pueden ser negativos"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "pedidos_meta/clientes_nuevos_meta inválidos"}), 400
    notas = (d.get('notas') or '')[:500]
    ant = c.execute("SELECT * FROM marketing_metas WHERE mes=?", (mes,)).fetchone()
    if ant:
        c.execute("""UPDATE marketing_metas
                     SET revenue_meta=?, pedidos_meta=?, clientes_nuevos_meta=?,
                         notas=?, fecha_actualizacion=datetime('now','-5 hours')
                     WHERE mes=?""",
                  (rev, ped, cln, notas, mes))
        accion = 'ACTUALIZAR_META_MENSUAL'
    else:
        c.execute("""INSERT INTO marketing_metas
                     (mes, revenue_meta, pedidos_meta, clientes_nuevos_meta, notas, creada_por)
                     VALUES (?,?,?,?,?,?)""",
                  (mes, rev, ped, cln, notas, u))
        accion = 'CREAR_META_MENSUAL'
    try:
        audit_log(c, usuario=u, accion=accion, tabla='marketing_metas',
                  registro_id=mes,
                  antes=dict(ant) if ant else None,
                  despues={'revenue_meta': rev, 'pedidos_meta': ped,
                           'clientes_nuevos_meta': cln, 'notas': notas[:120]})
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "mes": mes})


@bp.route('/api/marketing/meta-progreso')
def mkt_meta_progreso():
    """Devuelve meta del mes actual + progreso desde Shopify orders.

    Útil para mostrar "% vs meta" en Dashboard. Si no hay meta, retorna
    meta=null y advance=null para que la UI lo oculte.

    Query: ?mes=YYYY-MM (default: mes actual)
    """
    u, err, code = _auth()
    if err: return err, code
    from datetime import datetime as _dt
    mes = (request.args.get('mes') or _dt.now().strftime('%Y-%m')).strip()
    if not _re_atrib.match(r'^\d{4}-\d{2}$', mes):
        return jsonify({"error": "mes inválido (YYYY-MM)"}), 400
    conn = _db(); c = conn.cursor()
    meta_row = c.execute("SELECT * FROM marketing_metas WHERE mes=?", (mes,)).fetchone()
    if not meta_row:
        return jsonify({"mes": mes, "meta": None, "avance": None,
                         "hint": "Configurá la meta del mes vía POST /api/marketing/metas"})
    meta = dict(meta_row)
    # Avance real desde Shopify (mes calendario)
    sh = c.execute("""
        SELECT COALESCE(SUM(total),0) AS rev,
               COUNT(*) AS pedidos,
               COUNT(DISTINCT email) AS clientes
        FROM animus_shopify_orders
        WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND substr(creado_en,1,7)=?
    """, (mes,)).fetchone()
    nuevos = c.execute("""
        SELECT COUNT(DISTINCT o.email) AS n FROM animus_shopify_orders o
        WHERE LOWER(COALESCE(o.estado,'')) NOT IN ('cancelled','cancelado','voided') AND substr(o.creado_en,1,7)=?
          AND (SELECT COUNT(*) FROM animus_shopify_orders o2
                WHERE o2.email=o.email AND LOWER(COALESCE(o2.estado,'')) NOT IN ('cancelled','cancelado','voided') AND o2.creado_en < ?) = 0
    """, (mes, mes + '-01')).fetchone()
    revenue_real = float(sh['rev'] or 0)
    pedidos_real = int(sh['pedidos'] or 0)
    nuevos_real = int(nuevos['n'] or 0)
    def _pct(real, meta_val):
        if not meta_val or meta_val <= 0: return None
        return round(real / meta_val * 100, 1)
    # Días transcurridos del mes vs días totales · para proyección
    from datetime import date as _date
    hoy = _date.today()
    mes_year, mes_month = int(mes[:4]), int(mes[5:7])
    if hoy.year == mes_year and hoy.month == mes_month:
        dias_t = hoy.day
        # Días del mes actual
        import calendar as _cal
        dias_mes = _cal.monthrange(mes_year, mes_month)[1]
    else:
        # Mes pasado/futuro → cobertura completa o ninguna
        import calendar as _cal
        dias_mes = _cal.monthrange(mes_year, mes_month)[1]
        dias_t = dias_mes  # solo válido si ya pasó · si futuro lo dejamos así pero proyeccion es la real
    proy_revenue = revenue_real / max(dias_t,1) * dias_mes if dias_t > 0 else 0
    proy_pedidos = round(pedidos_real / max(dias_t,1) * dias_mes) if dias_t > 0 else 0
    return jsonify({
        "mes": mes,
        "meta": {
            "revenue": meta['revenue_meta'],
            "pedidos": meta['pedidos_meta'],
            "clientes_nuevos": meta['clientes_nuevos_meta'],
        },
        "avance": {
            "revenue": revenue_real,
            "revenue_pct": _pct(revenue_real, meta['revenue_meta']),
            "pedidos": pedidos_real,
            "pedidos_pct": _pct(pedidos_real, meta['pedidos_meta']),
            "clientes_nuevos": nuevos_real,
            "clientes_nuevos_pct": _pct(nuevos_real, meta['clientes_nuevos_meta']),
        },
        "proyeccion_fin_de_mes": {
            "revenue": round(proy_revenue, 0),
            "revenue_pct_meta": _pct(proy_revenue, meta['revenue_meta']),
            "pedidos": proy_pedidos,
        },
        "dias_transcurridos": dias_t,
        "dias_mes": dias_mes,
    })


# ──────────────────────────────────────────────────────────────────────────────
# KPIs HOY — endpoint rápido para la pestaña Hoy (4 KPIs reales, sin Claude)
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/kpis-hoy")
def mkt_kpis_hoy():
    """KPIs del día para la pestaña 🎯 Hoy.

    Devuelve 4 contadores reales que el frontend muestra como tarjetas:
      - influencers_pendientes_pago: pagos en estado Pendiente sin OC pagada
      - eventos_proximos: eventos cosméticos en los próximos 60 días
      - skus_en_riesgo: SKUs con días_cobertura ≤ 21 y demanda > 0
      - campanas_activas: marketing_campanas en estado 'Activa'

    Audit 25-may-2026 PM · P0 fix · el frontend leía estas 4 keys de
    /api/marketing/dashboard que NUNCA las devolvía → siempre 0.
    """
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    from datetime import datetime as _dt, timedelta as _td
    hoy = _dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hace30 = (hoy - _td(days=30)).strftime("%Y-%m-%d")

    # 1) Influencers pendientes de pago — DISTINCT por influencer_id
    try:
        pend = c.execute("""
            SELECT COUNT(DISTINCT influencer_id) AS n
            FROM pagos_influencers
            WHERE estado='Pendiente'
              AND (numero_oc IS NULL OR numero_oc='' OR numero_oc NOT IN (
                    SELECT numero_oc FROM ordenes_compra WHERE estado='Pagada'
                  ))
        """).fetchone()["n"]
    except Exception:
        pend = 0

    # 2) Eventos cosméticos próximos (≤ 60 días) · usa tabla editable (mig 186)
    eventos = 0
    for ev in _get_calendario_cosmetico(conn):
        try:
            d = (_dt.strptime(ev["fecha"], "%Y-%m-%d") - hoy).days
            if 0 <= d <= 60:
                eventos += 1
        except Exception:
            continue

    # 3) SKUs en riesgo — reusa lógica del agente estrategia (días cob ≤ 21)
    # PERF ronda2 29-may: precargar liberaciones (GROUP BY) y pedidos Shopify del
    # periodo en bloque · antes 2 queries por SKU (N+1). sku_items es compuesto,
    # así que el match LIKE %sku% se hace en Python sobre las filas precargadas.
    try:
        riesgo = 0
        _lib_map = {}
        for lr in c.execute(
            "SELECT sku, COALESCE(SUM(unidades),0) AS t FROM liberaciones WHERE creado_en>=? GROUP BY sku",
            (hace30,)
        ).fetchall():
            if lr["sku"]:
                _lib_map[lr["sku"]] = lr["t"]
        _shop_rows = c.execute(
            "SELECT sku_items, COALESCE(unidades_total,0) AS t FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en>=?",
            (hace30,)
        ).fetchall()
        for r in c.execute("""
            SELECT sku, SUM(unidades_disponible) AS stock
            FROM stock_pt WHERE estado='Disponible' GROUP BY sku
        """).fetchall():
            sku, stock = r["sku"], r["stock"]
            if not sku:
                continue
            lib = _lib_map.get(sku, 0)
            shop = sum(x["t"] for x in _shop_rows if x["sku_items"] and sku in x["sku_items"])
            demanda = (lib + shop) / 30.0
            if demanda > 0:
                dias_cob = (stock or 0) / demanda
                if dias_cob <= 21:
                    riesgo += 1
    except Exception:
        riesgo = 0

    # 4) Campañas activas (no incluye Planificadas — son "futuras")
    try:
        camp = c.execute(
            "SELECT COUNT(*) AS n FROM marketing_campanas WHERE estado='Activa'"
        ).fetchone()["n"]
    except Exception:
        camp = 0

    return jsonify({
        "ok": True,
        "kpis": {
            "influencers_pendientes_pago": int(pend or 0),
            "eventos_proximos":            int(eventos),
            "skus_en_riesgo":              int(riesgo),
            "campanas_activas":            int(camp or 0),
        },
    })


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
_MKT_DASH_CACHE = {}   # {'d': {ts, payload}} · cache per-worker · dashboard = overview


@bp.route("/api/marketing/dashboard")
def mkt_dashboard():
    u, err, code = _auth()
    if err:
        return err, code
    # PERF (Sebastián 13-jul · "marketing muy lento"): el dashboard agrega ~20 queries
    # sobre animus_shopify_orders (overview). Cache TTL 180s por-worker · ?force=1 salta.
    import time as _time_md
    _force_md = (request.args.get("force") or "") not in ("", "0", "false")
    _hit_md = _MKT_DASH_CACHE.get("d")
    if _hit_md and not _force_md and (_time_md.time() - _hit_md["ts"] < 600):
        return jsonify(_hit_md["payload"])
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

        # FIX 7-jul (audit ultracode · M5/M45): EXCLUIR órdenes CANCELADAS de los KPIs (el filtro canónico que
        # ya usan plan.py/auto_plan.py · la marca es estado='cancelled' vía cancelled_at). Sin esto los números
        # de marketing salían inflados y no cuadraban con Ánimus.
        sh_30 = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos,
                   COUNT(DISTINCT email) as clientes
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?
        """, (hace30,)).fetchone()

        sh_7 = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?
        """, (hace7,)).fetchone()

        sh_total = c.execute("""
            SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos,
                   COUNT(DISTINCT email) as clientes
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
        """).fetchone()

        sh_ticket = round(sh_30["rev"] / sh_30["pedidos"], 0) if sh_30["pedidos"] > 0 else 0

        # Clientes nuevos vs recurrentes (30d)
        sh_nuevos = c.execute("""
            SELECT COUNT(DISTINCT o.email) as n FROM animus_shopify_orders o
            WHERE LOWER(COALESCE(o.estado,'')) NOT IN ('cancelled','cancelado','voided') AND o.creado_en >= ?
            AND (SELECT COUNT(*) FROM animus_shopify_orders o2
                 WHERE o2.email=o.email AND LOWER(COALESCE(o2.estado,'')) NOT IN ('cancelled','cancelado','voided') AND o2.creado_en < ?) = 0
        """, (hace30, hace30)).fetchone()["n"]

        # FIX 7-jul (audit ultracode): quitada la query MUERTA sh_top_skus_raw (se computaba pero top_skus_combined
        # sale solo de erp_rev · era trabajo desperdiciado por cada carga del dashboard).

        # Agregar revenue ERP (liberaciones) · PERF 7-jul: pre-cargar el precio por SKU en 1 query (antes era
        # N+1 · un SELECT MAX(precio_base) por CADA sku vendido → ~50 queries en cada carga del dashboard).
        _precio_por_sku = {}
        for _pr in c.execute("SELECT sku, MAX(precio_base) AS p FROM stock_pt "
                             "WHERE sku IS NOT NULL GROUP BY sku").fetchall():
            _precio_por_sku[_pr["sku"]] = _pr["p"] or 0
        erp_rev = {}
        for row in c.execute("""
            SELECT sku, SUM(unidades) as uds FROM liberaciones
            WHERE creado_en >= ? AND sku IS NOT NULL GROUP BY sku
        """, (hace30,)).fetchall():
            p = _precio_por_sku.get(row["sku"], 0) or 0
            erp_rev[row["sku"]] = {"uds": row["uds"], "rev": round(row["uds"] * p, 0)}

        top_skus_combined = sorted(erp_rev.items(), key=lambda x: -x[1]["rev"])[:6]
        sh_top_skus = [{"sku": k, "total": v["rev"], "uds": v["uds"]} for k, v in top_skus_combined]

        # Ventas mensuales Shopify (últimos 6 meses)
        sh_mensual = _fmt_many(c.execute("""
            SELECT strftime('%Y-%m', creado_en) as mes,
                   COALESCE(SUM(total),0) as total,
                   COUNT(*) as pedidos
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
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
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND ciudad != ''
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
        ig_token_status = _ig_check_refresh(conn, allow_network=False) if ig_configured else {"expiry_date": None, "days_left": 0, "near_expiry": False, "refreshed": False, "expired": False}

        # AUDIT 26-may · KPIs pipeline GHL (mig 189 · si tabla vacía → 0)
        ghl_block = {
            "contactos_total": ghl_total,
            "contactos_nuevos_30d": ghl_nuevos,
            "opps_abiertas": 0,
            "opps_ganadas_30d": 0,
            "valor_pipeline_abierto": 0.0,
            "valor_ganado_30d": 0.0,
            "top_pipelines": [],
        }
        try:
            ghl_block["opps_abiertas"] = int(c.execute(
                "SELECT COUNT(*) AS n FROM animus_ghl_opportunities WHERE status='open'"
            ).fetchone()["n"] or 0)
            ghl_block["opps_ganadas_30d"] = int(c.execute(
                "SELECT COUNT(*) AS n FROM animus_ghl_opportunities "
                "WHERE status='won' AND date(ghl_updated_at)>=?",
                (hace30,)).fetchone()["n"] or 0)
            ghl_block["valor_pipeline_abierto"] = float(c.execute(
                "SELECT COALESCE(SUM(monetary_value),0) AS v "
                "FROM animus_ghl_opportunities WHERE status='open'"
            ).fetchone()["v"] or 0)
            ghl_block["valor_ganado_30d"] = float(c.execute(
                "SELECT COALESCE(SUM(monetary_value),0) AS v "
                "FROM animus_ghl_opportunities "
                "WHERE status='won' AND date(ghl_updated_at)>=?",
                (hace30,)).fetchone()["v"] or 0)
            ghl_block["top_pipelines"] = [dict(r) for r in c.execute("""
                SELECT pipeline_nombre, COUNT(*) AS opps,
                       COALESCE(SUM(monetary_value),0) AS valor
                FROM animus_ghl_opportunities
                WHERE status='open' AND COALESCE(pipeline_nombre,'') != ''
                GROUP BY pipeline_nombre ORDER BY valor DESC LIMIT 5
            """).fetchall()]
        except Exception as _ghl_e:
            # Si la mig 189 aún no aplicó (tabla no existe), KPIs quedan en 0
            log.warning("ghl KPIs dashboard fallback (mig 189 pending?): %s", _ghl_e)

        _dash_payload = {
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
            "ghl": ghl_block,
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
        }
        _MKT_DASH_CACHE["d"] = {"ts": _time_md.time(), "payload": _dash_payload}
        return jsonify(_dash_payload)
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ──────────────────────────────────────────────────────────────────────────────
# CAMPAÑAS
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/influencers/<int:iid>/dar-baja", methods=["POST"])
def mkt_dar_de_baja(iid):
    """Marca un influencer como Baja con motivo — no lo elimina.

    Sebastián 25-may-2026 PM · audit P2 · audit_log + snapshot.
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); d = request.get_json() or {}
    motivo = str(d.get("motivo") or "Sin especificar").strip()
    obs    = str(d.get("observacion") or "").strip()
    nota   = f"{motivo}" + (f" — {obs}" if obs else "")
    cur = conn.cursor()
    antes = {}
    try:
        snap = cur.execute(
            "SELECT estado, motivo_baja, nombre FROM marketing_influencers WHERE id=?",
            (iid,)).fetchone()
        if snap:
            antes = {'estado': snap[0], 'motivo_baja': snap[1] or '',
                      'nombre': snap[2] or ''}
    except Exception:
        pass
    cur.execute("""
        UPDATE marketing_influencers
        SET estado='Baja', motivo_baja=?, fecha_baja=date('now', '-5 hours'), notas=?
        WHERE id=?
    """, (nota, obs, iid))
    try:
        from audit_helpers import audit_log as _al
        _al(cur, usuario=u, accion='DAR_BAJA_INFLUENCER',
            tabla='marketing_influencers', registro_id=iid,
            antes=antes, despues={'estado': 'Baja', 'motivo': nota})
    except Exception: pass
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/marketing/analytics/influencers", methods=["GET"])
def mkt_analytics_influencers():
    """Analytics completos de influencers desde pagos_influencers."""
    u, err, code = _auth()
    if err: return err, code
    conn = _db(); c = conn.cursor()
    try:
        now_year = (datetime.now() - timedelta(hours=5)).year  # Colombia · M24 (evita saltar de año en la noche UTC)

        # Totales globales
        row = c.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN estado='Pagada' AND fecha LIKE ? THEN valor ELSE 0 END),0) as total_anio,
                COALESCE(SUM(CASE WHEN estado='Pendiente' THEN valor ELSE 0 END),0) as total_pendiente,
                COUNT(CASE WHEN estado='Pagada' AND fecha LIKE ? THEN 1 END) as total_colabs,
                COUNT(DISTINCT CASE WHEN estado='Pagada' AND fecha LIKE ? THEN LOWER(TRIM(influencer_nombre)) END) as creadores_unicos
            FROM pagos_influencers
        """, (f"{now_year}%", f"{now_year}%", f"{now_year}%")).fetchone()

        total_anio       = row[0] or 0
        total_pendiente  = row[1] or 0
        total_colabs     = row[2] or 0
        creadores_unicos = row[3] or 0
        promedio         = int(total_anio / total_colabs) if total_colabs else 0

        # Top creador
        # FIX 16-jun · drift PG: se agrupa por EXPRESION LOWER(TRIM(...)) pero se
        # proyecta influencer_nombre crudo → PG no deriva dependencia funcional →
        # "must appear in GROUP BY". Envolver en MIN() (SQLite lo toleraba).
        top = c.execute("""
            SELECT MIN(influencer_nombre), SUM(valor) as t FROM pagos_influencers
            WHERE estado='Pagada' AND fecha LIKE ?
            GROUP BY LOWER(TRIM(influencer_nombre)) ORDER BY t DESC LIMIT 1
        """, (f"{now_year}%",)).fetchone()
        top_creador = top[0] if top else "—"

        # Por mes
        meses_raw = c.execute("""
            SELECT
                strftime('%Y-%m', fecha) as mes,
                COUNT(CASE WHEN estado='Pagada' THEN 1 END) as colabs,
                COUNT(DISTINCT CASE WHEN estado='Pagada' THEN LOWER(TRIM(influencer_nombre)) END) as creadores_unicos_mes,
                COALESCE(SUM(CASE WHEN estado='Pagada' THEN valor ELSE 0 END),0) as total_pagado,
                COALESCE(SUM(CASE WHEN estado='Pendiente' THEN valor ELSE 0 END),0) as total_pendiente
            FROM pagos_influencers
            WHERE fecha IS NOT NULL AND fecha != ''
            GROUP BY mes ORDER BY mes
        """).fetchall()

        # Nuevos creadores por mes (primer pago de cada creador)
        primeros = c.execute("""
            SELECT LOWER(TRIM(influencer_nombre)), MIN(strftime('%Y-%m', fecha)) as primer_mes
            FROM pagos_influencers GROUP BY LOWER(TRIM(influencer_nombre))
        """).fetchall()
        nuevos_por_mes = {}
        for _, pm in primeros:
            if pm: nuevos_por_mes[pm] = nuevos_por_mes.get(pm, 0) + 1

        por_mes = []
        for r in meses_raw:
            por_mes.append({
                "mes": r[0], "colabs": r[1], "creadores_unicos_mes": r[2],
                "total_pagado": r[3], "total_pendiente": r[4],
                "nuevos_creadores": nuevos_por_mes.get(r[0], 0)
            })

        # Ranking por creador — ALL TIME
        # FIX 16-jun · drift PG: GROUP BY por EXPRESION; p.influencer_nombre y m.estado
        # (tabla unida) van crudos → envolver en MIN() para que PG no aborte.
        ranking_raw = c.execute("""
            SELECT MIN(p.influencer_nombre),
                   COUNT(CASE WHEN p.estado='Pagada' THEN 1 END) as colabs,
                   COALESCE(SUM(CASE WHEN p.estado='Pagada' THEN p.valor ELSE 0 END),0) as total,
                   COALESCE(SUM(CASE WHEN p.estado='Pendiente' THEN p.valor ELSE 0 END),0) as pendiente,
                   COALESCE(MIN(m.estado), 'Activo') as estado_inf,
                   MIN(p.fecha) as primer_pago,
                   MAX(p.fecha) as ultimo_pago
            FROM pagos_influencers p
            LEFT JOIN marketing_influencers m ON LOWER(TRIM(m.nombre))=LOWER(TRIM(p.influencer_nombre))
            GROUP BY LOWER(TRIM(p.influencer_nombre))
            ORDER BY total DESC LIMIT 50
        """).fetchall()

        ranking = [{"nombre": r[0], "colabs": r[1], "total": r[2],
                    "pendiente": r[3],
                    "promedio": int(r[2]/r[1]) if r[1] else 0,
                    "estado": r[4], "primer_pago": r[5], "ultimo_pago": r[6]}
                   for r in ranking_raw]

        # All-time historico totals
        hist = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN estado='Pagada' THEN valor ELSE 0 END),0),
                   COUNT(CASE WHEN estado='Pagada' THEN 1 END),
                   COUNT(DISTINCT CASE WHEN estado='Pagada' THEN LOWER(TRIM(influencer_nombre)) END)
            FROM pagos_influencers
        """).fetchone()
        total_historico = hist[0] or 0
        colabs_historico = hist[1] or 0
        creadores_historico = hist[2] or 0

        return jsonify({
            "total_pagado_anio":    total_anio,
            "total_pagado_historico": total_historico,
            "total_pendiente":      total_pendiente,
            "total_colabs":         total_colabs,
            "colabs_historico":     colabs_historico,
            "creadores_unicos":     creadores_unicos,
            "creadores_historico":  creadores_historico,
            "promedio_por_colab":   promedio,
            "top_creador":          top_creador,
            "por_mes":              por_mes,
            "ranking":              ranking,
            "anio_actual":          now_year,
        })
    except Exception as e:
        # FIX 7-jul (audit ultracode): NO devolver el stack trace al cliente (info disclosure). Loguear server-side.
        import traceback, logging as _lg
        _lg.getLogger('marketing').warning('mkt_analytics_influencers: %s', traceback.format_exc()[-600:])
        return jsonify({"_error": str(e)[:200]}), 200


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
            # PERF ronda2 29-may: contar influencers/contenido en bloque (2
            # GROUP BY) en vez de 2 queries por campaña (N+1).
            _inf_cnt = {x[0]: x[1] for x in c.execute(
                "SELECT campana_id, COUNT(*) FROM marketing_campana_influencer GROUP BY campana_id"
            ).fetchall()}
            _cont_cnt = {x[0]: x[1] for x in c.execute(
                "SELECT campana_id, COUNT(*) FROM marketing_contenido GROUP BY campana_id"
            ).fetchall()}
            result = []
            for row in rows:
                r = dict(row)
                r["num_influencers"] = _inf_cnt.get(r["id"], 0)
                r["num_contenido"] = _cont_cnt.get(r["id"], 0)
                result.append(r)
            return jsonify(result)

        # POST — crear campaña
        d = request.get_json() or {}
        if not d.get("nombre"):
            return jsonify({"error": "nombre requerido"}), 400
        # Money sanity validations · audit zero-error 2-may-2026
        from http_helpers import validate_money
        presupuesto, err_p = validate_money(d.get("presupuesto", 0), allow_zero=True,
                                              field_name='presupuesto')
        if err_p:
            return jsonify(err_p), 400
        gastado, err_g = validate_money(d.get("presupuesto_gastado", 0), allow_zero=True,
                                          field_name='presupuesto_gastado')
        if err_g:
            return jsonify(err_g), 400
        c.execute("""
            INSERT INTO marketing_campanas
            (nombre, tipo, estado, presupuesto, presupuesto_gastado,
             fecha_inicio, fecha_fin, sku_objetivo, objetivo_unidades,
             canal, notas, creada_por)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d["nombre"], d.get("tipo", "Digital"), d.get("estado", "Planificada"),
            presupuesto, gastado,
            d.get("fecha_inicio"), d.get("fecha_fin"),
            d.get("sku_objetivo", ""), d.get("objetivo_unidades", 0),
            d.get("canal", ""), d.get("notas", ""), u
        ))
        new_id = c.lastrowid
        audit_log(c, usuario=u, accion='CREAR_CAMPANA_MKT',
                  tabla='marketing_campanas', registro_id=new_id,
                  despues={'nombre': d["nombre"][:80], 'tipo': d.get("tipo","Digital"),
                           'presupuesto': presupuesto, 'canal': d.get("canal","")},
                  detalle=f"Campana '{d['nombre'][:60]}' · ${presupuesto:,.0f}")
        conn.commit()
        return jsonify({"ok": True, "id": new_id}), 201
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
            # Audit 25-may PM · validar campos sensibles igual que en POST
            from http_helpers import validate_money
            for money_field in ("presupuesto", "presupuesto_gastado", "resultado_ventas"):
                if money_field in updates:
                    v, errm = validate_money(updates[money_field], allow_zero=True, field_name=money_field)
                    if errm:
                        return jsonify(errm), 400
                    updates[money_field] = v
            # Whitelist de estado (frontend solo manda los 4 esperados, pero validar evita data fantasma)
            if "estado" in updates:
                _estados_ok = {"Planificada", "Activa", "Pausada", "Finalizada"}
                if updates["estado"] not in _estados_ok:
                    return jsonify({"error": f"estado inválido: {updates['estado']!r} (válidos: {sorted(_estados_ok)})"}), 400
            # Soft-validate fechas (warning en respuesta pero no rechazar)
            _warn = None
            if "fecha_inicio" in updates and "fecha_fin" in updates:
                fi, ff = updates.get("fecha_inicio"), updates.get("fecha_fin")
                if fi and ff and str(fi) > str(ff):
                    _warn = f"fecha_inicio ({fi}) es posterior a fecha_fin ({ff})"
            antes_row = c.execute(
                "SELECT nombre, estado, presupuesto, presupuesto_gastado FROM marketing_campanas WHERE id=?",
                (cid,)).fetchone()
            antes = {'nombre': antes_row[0], 'estado': antes_row[1],
                      'presupuesto': antes_row[2], 'presupuesto_gastado': antes_row[3]} if antes_row else None
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE marketing_campanas SET {set_clause} WHERE id=?",
                      list(updates.values()) + [cid])
            audit_log(c, usuario=u, accion='MODIFICAR_CAMPANA_MKT',
                      tabla='marketing_campanas', registro_id=cid,
                      antes=antes, despues=updates,
                      detalle=f"Campana id={cid} · {len(updates)} campos modificados")
            conn.commit()
            resp = {"ok": True}
            if _warn:
                resp["warning"] = _warn
            return jsonify(resp)

        if request.method == "DELETE":
            if u not in ADMIN_USERS:
                return jsonify({"error": "Sin permiso"}), 403
            # Audit 25-may · avisar si la campaña tiene gasto registrado (riesgo financiero)
            spent_row = c.execute(
                "SELECT nombre, COALESCE(presupuesto_gastado,0), COALESCE(resultado_ventas,0) FROM marketing_campanas WHERE id=?",
                (cid,)).fetchone()
            if spent_row and (spent_row[1] > 0 or spent_row[2] > 0):
                if not str(request.args.get("force") or "").lower() in ("1","true","yes"):
                    return jsonify({
                        "error": "Campaña tiene gasto/ventas registradas. Reenviar con ?force=1 para confirmar.",
                        "presupuesto_gastado": spent_row[1],
                        "resultado_ventas": spent_row[2],
                        "nombre": spent_row[0],
                    }), 409
            antes_row = c.execute(
                "SELECT nombre FROM marketing_campanas WHERE id=?", (cid,)).fetchone()
            antes = {'nombre': antes_row[0]} if antes_row else None
            c.execute("DELETE FROM marketing_campana_influencer WHERE campana_id=?", (cid,))
            c.execute("DELETE FROM marketing_contenido WHERE campana_id=?", (cid,))
            c.execute("DELETE FROM marketing_campanas WHERE id=?", (cid,))
            audit_log(c, usuario=u, accion='ELIMINAR_CAMPANA_MKT',
                      tabla='marketing_campanas', registro_id=cid,
                      antes=antes,
                      detalle=f"Eliminada campana id={cid}" + (f" · {antes['nombre']}" if antes else ""))
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
    # PRIVACY-FIX · 21-may-2026 · datos bancarios solo admin (Habeas Data L1581)
    # Antes: Jefferson/Felipe/Daniela veían banco+cuenta+cedula_nit
    # Ahora: campos sensibles solo admin · resto ve campos públicos
    _is_admin = (u or '').lower() in {x.lower() for x in ADMIN_USERS}
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            q = request.args.get("q", "")
            estado = request.args.get("estado", "")
            # SELECT explícito · oculta sensibles para no-admin
            if _is_admin:
                base = "SELECT * FROM marketing_influencers"
            else:
                base = ("SELECT id, nombre, usuario_red, red_social, nicho, "
                        "categoria, estado, ciudad, pais, fecha_creacion, notas "
                        "FROM marketing_influencers")
            conds, params = [], []
            if q:
                conds.append("(nombre LIKE ? OR usuario_red LIKE ? OR nicho LIKE ?)")
                params += [f"%{q}%", f"%{q}%", f"%{q}%"]
            if estado:
                conds.append("estado=?")
                params.append(estado)
            sql = base + (" WHERE " + " AND ".join(conds) if conds else "") + " ORDER BY nombre"
            rows = c.execute(sql, params).fetchall()
            # PERF ronda2 29-may: estadísticas agregadas en bloque (1 GROUP BY)
            # en vez de 1 query por influencer (N+1).
            _stats_map = {}
            for srow in c.execute("""
                SELECT influencer_id,
                       COUNT(DISTINCT campana_id) as campanas,
                       COALESCE(SUM(conversiones),0) as conversiones,
                       COALESCE(SUM(alcance_real),0) as alcance_total,
                       COALESCE(SUM(monto_pagado),0) as total_pagado
                FROM marketing_campana_influencer GROUP BY influencer_id
            """).fetchall():
                sd = dict(srow)
                _stats_map[sd.pop("influencer_id")] = sd
            result = []
            for row in rows:
                r = dict(row)
                r["stats"] = _stats_map.get(r["id"], {"campanas": 0, "conversiones": 0,
                                                       "alcance_total": 0, "total_pagado": 0})
                result.append(r)
            return jsonify(result)

        d = request.get_json() or {}
        if not d.get("nombre"):
            return jsonify({"error": "nombre requerido"}), 400
        # Normalizar discount_code: uppercase sin espacios
        dc = (d.get("discount_code") or "").strip().upper().replace(" ", "")
        # Bug fix: el INSERT viejo solo guardaba 11 campos básicos. Datos
        # bancarios (banco, cuenta, cédula, tipo cta, ciudad) y el discount
        # code para atribución Shopify NO se persistían — el frontend los
        # mandaba pero quedaban en NULL/default. Ahora se guardan todos.
        try:
            c.execute("""
                INSERT INTO marketing_influencers
                (nombre, red_social, usuario_red, seguidores, engagement_rate,
                 nicho, tarifa, estado, email, telefono, notas,
                 banco, cuenta_bancaria, tipo_cuenta, cedula_nit, ciudad,
                 discount_code, ciclo_pago)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                d["nombre"], d.get("red_social", "Instagram"), d.get("usuario_red", ""),
                d.get("seguidores", 0), d.get("engagement_rate", 0),
                d.get("nicho", ""), d.get("tarifa", 0), d.get("estado", "Activo"),
                d.get("email", ""), d.get("telefono", ""), d.get("notas", ""),
                d.get("banco", ""), d.get("cuenta_bancaria", ""),
                d.get("tipo_cuenta", ""), d.get("cedula_nit", ""),
                d.get("ciudad", ""), dc, d.get("ciclo_pago", "Mensual"),
            ))
        except sqlite3.OperationalError:
            # Fallback para instalaciones MUY viejas donde algun ALTER no
            # corrió: insertar con campos básicos primero, después update.
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

@bp.route("/api/marketing/influencers/duplicados", methods=["GET"])
def mkt_influencers_duplicados():
    """Detecta influencers que parecen duplicados (mismo nombre normalizado o
    misma cuenta/cedula). Sebastian (30-abr-2026): jefferson reporta dobles.

    PRIVACY-FIX 25-may-2026 · Habeas Data Ley 1581 CO · cuenta_bancaria +
    cedula_nit visibles SOLO a ADMIN. Para MARKETING_USERS no-admin, las
    columnas sensibles se sustituyen por '***'. La detección de duplicados
    por cuenta/cédula funciona igual (se compara internamente) pero los
    valores no se exponen al cliente no-autorizado.
    """
    u, err, code = _auth()
    if err:
        return err, code
    _is_admin = (u or '').lower() in {x.lower() for x in ADMIN_USERS}
    conn = _db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, nombre, red_social, usuario_red, estado, cuenta_bancaria,
               cedula_nit, email, tarifa,
               (SELECT COUNT(*) FROM pagos_influencers WHERE influencer_id=marketing_influencers.id) as n_pagos
        FROM marketing_influencers
        ORDER BY nombre
    """).fetchall()
    items = [dict(zip([d[0] for d in c.description], r)) for r in rows]
    # Backup de valores reales para detección · luego enmascaramos en el
    # dict expuesto al cliente si no es admin.
    real_cuenta = {it['id']: it.get('cuenta_bancaria') for it in items}
    real_cedula = {it['id']: it.get('cedula_nit') for it in items}
    if not _is_admin:
        for it in items:
            if it.get('cuenta_bancaria'):
                it['cuenta_bancaria'] = '***'
            if it.get('cedula_nit'):
                it['cedula_nit'] = '***'

    def _norm(s):
        if not s: return ''
        return ''.join(ch.lower() for ch in str(s).strip() if ch.isalnum())

    grupos = {}
    for it in items:
        key = _norm(it['nombre'])
        if not key or len(key) < 3:
            continue
        grupos.setdefault(key, []).append(it)

    duplicados = []
    for key, grp in grupos.items():
        if len(grp) > 1:
            # Marcar el "mejor" (con mas pagos) para que Jefferson sepa cuál conservar
            grp_sorted = sorted(grp, key=lambda x: (x['n_pagos'] or 0), reverse=True)
            duplicados.append({
                'nombre_normalizado': key,
                'count': len(grp),
                'sugerido_conservar': grp_sorted[0]['id'],
                'rows': grp_sorted,
            })

    # Detectar también por cuenta_bancaria + cedula · usar VALORES REALES
    # del backup (los items expuestos pueden estar enmascarados '***' para
    # no-admin · la detección sigue funcionando porque comparamos antes de
    # serializar).
    grupos_cuenta = {}
    for it in items:
        cta = _norm(real_cuenta.get(it['id']))
        ced = _norm(real_cedula.get(it['id']))
        if cta and len(cta) >= 6:
            grupos_cuenta.setdefault('cta:'+cta, []).append(it)
        if ced and len(ced) >= 6:
            grupos_cuenta.setdefault('ced:'+ced, []).append(it)
    duplicados_datos = []
    for key, grp in grupos_cuenta.items():
        if len(grp) > 1:
            tipo = 'cuenta bancaria' if key.startswith('cta:') else 'cedula/NIT'
            # PRIVACY · valor enmascarado para no-admin (solo muestra que hay
            # match · admin puede ver el dato completo para resolver duplicado)
            valor_raw = key.split(':',1)[1]
            valor_display = valor_raw if _is_admin else ('***' + valor_raw[-3:] if len(valor_raw) >= 4 else '***')
            duplicados_datos.append({
                'tipo': tipo, 'valor': valor_display,
                'count': len(grp), 'rows': grp,
            })

    return jsonify({
        'duplicados_por_nombre': duplicados,
        'duplicados_por_datos': duplicados_datos,
        'total_grupos_nombre': len(duplicados),
        'total_grupos_datos': len(duplicados_datos),
    })


def _score_inf_dedup(x):
    # x = (id, nombre, usuario_red, seguidores, tarifa, cuenta, cedula, n_pagos)
    return ((x[7] or 0) * 100 + (1 if x[2] else 0) + (1 if x[3] else 0)
            + (1 if x[4] else 0) + (1 if x[5] else 0) + (1 if x[6] else 0))


@bp.route("/api/marketing/influencers/dedup-merge", methods=["POST"])
def mkt_influencers_dedup_merge():
    """Fusiona influencers duplicados por nombre normalizado: conserva uno (más
    pagos / más completo), repunta pagos_influencers + solicitudes_compra al
    keeper, elimina los duplicados, y crea un UNIQUE index para que el panel deje
    de re-crearlos (el INSERT OR IGNORE no deduplicaba sin UNIQUE · 3 workers →
    race). Body: {apply: bool} · dry-run por default. Solo admin (destructivo).
    Sebastián 1-jun-2026 · reporte 'todos juanito rebel'."""
    u, err, code = _auth()
    if err:
        return err, code
    if (u or '').lower() not in {x.lower() for x in ADMIN_USERS}:
        return jsonify({'error': 'Solo admin puede fusionar duplicados'}), 403
    apply = bool((request.get_json(silent=True) or {}).get('apply'))
    conn = _db(); c = conn.cursor()
    rows = c.execute(
        "SELECT id, nombre, COALESCE(usuario_red,''), COALESCE(seguidores,0), "
        "COALESCE(tarifa,0), COALESCE(cuenta_bancaria,''), COALESCE(cedula_nit,''), "
        "(SELECT COUNT(*) FROM pagos_influencers WHERE influencer_id=marketing_influencers.id) "
        "FROM marketing_influencers ORDER BY id"
    ).fetchall()
    grupos = {}
    for r in rows:
        k = ' '.join((r[1] or '').strip().split()).lower()
        if not k:
            continue
        grupos.setdefault(k, []).append(r)
    plan = []
    for k, lst in grupos.items():
        if len(lst) < 2:
            continue
        ordered = sorted(lst, key=lambda x: (-_score_inf_dedup(x), x[0]))
        keeper = ordered[0]
        plan.append({'nombre': keeper[1], 'keeper_id': keeper[0],
                     'baja_ids': [x[0] for x in ordered[1:]],
                     'duplicados': len(ordered) - 1})
    total_dups = sum(p['duplicados'] for p in plan)
    if not apply:
        return jsonify({'ok': True, 'dry_run': True, 'grupos': plan,
                        'grupos_n': len(plan), 'duplicados_a_eliminar': total_dups,
                        'total_influencers': len(rows)})
    refs_pagos = 0; refs_sols = 0; eliminados = 0
    for p in plan:
        for bid in p['baja_ids']:
            try:
                cur1 = c.execute("UPDATE pagos_influencers SET influencer_id=? WHERE influencer_id=?",
                                 (p['keeper_id'], bid)); refs_pagos += (cur1.rowcount or 0)
            except Exception:
                pass
            try:
                cur2 = c.execute("UPDATE solicitudes_compra SET influencer_id=? WHERE influencer_id=?",
                                 (p['keeper_id'], bid)); refs_sols += (cur2.rowcount or 0)
            except Exception:
                pass
            c.execute("DELETE FROM marketing_influencers WHERE id=?", (bid,))
            eliminados += 1
    idx_ok = True
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mktinf_nombre_unq "
                  "ON marketing_influencers(LOWER(TRIM(nombre)))")
    except Exception as _eidx:
        idx_ok = False
        __import__('logging').getLogger('marketing').warning(
            'UNIQUE index influencers no creado (dups residuales?): %s', _eidx)
    try:
        audit_log(c, usuario=u, accion='DEDUP_INFLUENCERS',
                  tabla='marketing_influencers', registro_id='',
                  despues={'eliminados': eliminados, 'refs_pagos': refs_pagos,
                           'refs_sols': refs_sols, 'unique_index': idx_ok})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'aplicado': True, 'duplicados_eliminados': eliminados,
                    'pagos_repuntados': refs_pagos, 'sols_repuntadas': refs_sols,
                    'unique_index': idx_ok})


@bp.route("/api/marketing/influencers/<int:iid>", methods=["GET", "PUT", "DELETE"])
def mkt_influencer_detail(iid):
    u, err, code = _auth()
    if err:
        return err, code
    # PRIVACY-FIX · 21-may-2026 · GET datos bancarios solo admin
    _is_admin = (u or '').lower() in {x.lower() for x in ADMIN_USERS}
    conn = _db()
    c = conn.cursor()
    try:
        if request.method == "GET":
            # CEO 3-jun-2026 · marketing captura/mantiene datos bancarios →
            # el modal de edición DEBE poder ver el dato actual para corregirlo.
            # Quien no pueda capturar banco recibe la proyección sin lo bancario.
            if _puede_capturar_banco(u):
                row = c.execute("SELECT * FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
            else:
                row = c.execute(
                    "SELECT id, nombre, usuario_red, red_social, nicho, categoria, "
                    "estado, ciudad, pais, fecha_creacion, notas "
                    "FROM marketing_influencers WHERE id=?",
                    (iid,),
                ).fetchone()
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
                      "nicho", "tarifa", "estado", "email", "telefono", "notas",
                      "discount_code", "ciclo_pago",
                      "banco", "cuenta_bancaria", "tipo_cuenta", "cedula_nit"]
            # CEO 3-jun-2026 · marketing (Jeferson) CAPTURA/CORRIGE datos
            # bancarios (es su trabajo: van a la cuenta de cobro → Compras).
            # Quien no esté autorizado a banco edita el resto; los sensibles se
            # descartan PERO devolviendo aviso explícito (no falso "ok").
            campos_sensibles = {"banco", "cuenta_bancaria", "tipo_cuenta", "cedula_nit"}
            _bancarios_ignorados = False
            if not _puede_capturar_banco(u):
                if any(k in d for k in campos_sensibles):
                    _bancarios_ignorados = True
                d = {k: v for k, v in d.items() if k not in campos_sensibles}
            updates = {k: d[k] for k in campos if k in d}
            if "discount_code" in updates:
                dc = (updates["discount_code"] or "").strip().upper().replace(" ", "")
                updates["discount_code"] = dc
            if not updates:
                return jsonify({"error": "Nada que actualizar"}), 400
            # SEC-FIX · 21-may-2026 · audit_log obligatorio
            antes_row = c.execute("SELECT * FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
            antes_dict = dict(antes_row) if antes_row else {}
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE marketing_influencers SET {set_clause} WHERE id=?",
                      list(updates.values()) + [iid])
            _toca_banco = any(k in campos_sensibles for k in updates)
            try:
                from audit_helpers import audit_log
                # Habeas Data · enmascarar valores bancarios en el rastro (no plano)
                _a = {k: antes_dict.get(k) for k in updates}
                _d = dict(updates)
                for k in campos_sensibles:
                    if k in _a and _a[k]:
                        _a[k] = '***' + str(_a[k])[-3:]
                    if k in _d and _d[k]:
                        _d[k] = '***' + str(_d[k])[-3:]
                audit_log(c, usuario=u,
                          accion=('MODIFICAR_BANCO_INFLUENCER' if _toca_banco
                                  else 'MODIFICAR_INFLUENCER'),
                          tabla='marketing_influencers', registro_id=iid,
                          antes=_a, despues=_d)
            except Exception:
                pass
            conn.commit()
            if _bancarios_ignorados:
                return jsonify({"ok": True,
                                "aviso": "No tienes permiso para editar datos "
                                         "bancarios; los demás campos se guardaron."})
            return jsonify({"ok": True})

        if request.method == "DELETE":
            # Sebastian (30-abr-2026): "jeferson dice que hay creadores dobles
            # pero no le deja eliminarlos entonces pon una opcion de eliminar".
            # Antes solo admin. Ahora marketing users pueden eliminar SI el
            # influencer NO tiene pagos efectivos. Si tiene pagos → solo admin.
            es_admin = u in ADMIN_USERS
            try:
                n_pagados = c.execute(
                    "SELECT COUNT(*) FROM pagos_influencers WHERE influencer_id=? AND estado='Pagada'",
                    (iid,)
                ).fetchone()[0] or 0
            except Exception:
                n_pagados = 0
            try:
                n_sols = c.execute(
                    "SELECT COUNT(*) FROM solicitudes_compra WHERE influencer_id=? AND estado='Pagada'",
                    (iid,)
                ).fetchone()[0] or 0
            except Exception:
                n_sols = 0
            tiene_pagos = (n_pagados > 0) or (n_sols > 0)
            if tiene_pagos and not es_admin:
                return jsonify({
                    "error": (f"Este influencer tiene {n_pagados} pago(s) y "
                              f"{n_sols} solicitud(es) Pagadas vinculadas. "
                              "Solo admin (Sebastián/Alejandro) puede borrarlo. "
                              "Recomendacion: dale de baja en lugar de eliminar.")
                }), 403
            # Borrar TODO lo asociado al influencer
            try:
                c.execute("DELETE FROM marketing_campana_influencer WHERE influencer_id=?", (iid,))
            except Exception:
                pass
            try:
                # Pagos NO Pagados (Pendientes/Rechazados) → borrar
                c.execute("DELETE FROM pagos_influencers WHERE influencer_id=? AND estado != 'Pagada'", (iid,))
            except Exception:
                pass
            try:
                # Solicitudes NO Pagadas → desvincular (solicitudes son del usuario solicitante, no del influencer)
                c.execute("UPDATE solicitudes_compra SET influencer_id=NULL WHERE influencer_id=? AND estado != 'Pagada'", (iid,))
            except Exception:
                pass
            try:
                c.execute("DELETE FROM marketing_influencers_metrics WHERE influencer_id=?", (iid,))
            except Exception:
                pass
            # Sebastián 25-may-2026 PM · audit P1 · snapshot antes del DELETE
            # para audit_log (regulatorio · trazabilidad de pagos asociados)
            try:
                _snap = c.execute(
                    "SELECT nombre, usuario_red, red_social, email FROM marketing_influencers WHERE id=?",
                    (iid,)).fetchone()
                _snap_dict = dict(_snap) if _snap else {}
            except Exception:
                _snap_dict = {}
            c.execute("DELETE FROM marketing_influencers WHERE id=?", (iid,))
            try:
                from audit_helpers import audit_log as _al
                _al(c, usuario=u, accion='ELIMINAR_INFLUENCER',
                    tabla='marketing_influencers', registro_id=iid,
                    antes=_snap_dict,
                    despues={'n_pagados_pagados': n_pagados, 'n_sols_pagadas': n_sols})
            except Exception: pass
            conn.commit()
            return jsonify({"ok": True, "mensaje": "Influencer eliminado"})
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ──────────────────────────────────────────────────────────────────────────────
# ASIGNACIÓN CAMPAÑA ↔ INFLUENCER
# ──────────────────────────────────────────────────────────────────────────────
@bp.route("/api/marketing/campana-influencer", methods=["POST"])
def mkt_asignar_influencer():
    """Asigna influencer a campaña.

    Sebastián 25-may-2026 PM · audit P2 · validate_money + audit_log.
    """
    u, err, code = _auth()
    if err:
        return err, code
    d = request.get_json() or {}
    if not d.get("campana_id") or not d.get("influencer_id"):
        return jsonify({"error": "campana_id e influencer_id requeridos"}), 400
    # Validar monto_pactado (puede venir 0 si aún no se pactó)
    monto_pact = d.get("monto_pactado", 0)
    try:
        monto_pact = float(monto_pact or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "monto_pactado inválido"}), 400
    if monto_pact < 0 or monto_pact > 500_000_000:
        return jsonify({"error": "monto_pactado fuera de rango (0..500M)"}), 400
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
              monto_pact, d.get("estado", "Pendiente"), d.get("notas", "")))
        new_id = c.lastrowid
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=u, accion='ASIGNAR_INFLUENCER_A_CAMPANA',
                tabla='marketing_campana_influencer', registro_id=new_id,
                despues={'campana_id': d["campana_id"],
                          'influencer_id': d["influencer_id"],
                          'monto_pactado': monto_pact,
                          'estado': d.get("estado", "Pendiente")})
        except Exception: pass
        conn.commit()
        return jsonify({"ok": True, "id": new_id}), 201
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

@bp.route("/api/marketing/campana-influencer/<int:rid>", methods=["PUT"])
def mkt_update_asignacion(rid):
    """Actualiza asignación influencer-campaña.

    Sebastián 25-may-2026 PM · audit P2 · validate_money en monto_* +
    snapshot antes + audit_log.
    """
    u, err, code = _auth()
    if err:
        return err, code
    d = request.get_json() or {}
    campos = ["monto_pactado", "monto_pagado", "fecha_pago",
              "alcance_real", "impresiones", "clicks", "conversiones", "estado", "notas"]
    updates = {k: d[k] for k in campos if k in d}
    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400
    # Validar montos (si vienen)
    for _campo_money in ('monto_pactado', 'monto_pagado'):
        if _campo_money in updates:
            try:
                _v = float(updates[_campo_money] or 0)
            except (TypeError, ValueError):
                return jsonify({"error": f"{_campo_money} inválido"}), 400
            if _v < 0 or _v > 500_000_000:
                return jsonify({"error": f"{_campo_money} fuera de rango"}), 400
            updates[_campo_money] = _v
    conn = _db()
    c = conn.cursor()
    try:
        # Snapshot antes
        antes = {}
        try:
            cols_sel = ", ".join(sorted(updates.keys()))
            row = c.execute(
                f"SELECT {cols_sel} FROM marketing_campana_influencer WHERE id=?",
                (rid,)).fetchone()
            if row:
                antes = dict(zip(sorted(updates.keys()), row))
        except Exception:
            pass
        set_clause = ", ".join(f"{k}=?" for k in updates)
        c.execute(f"UPDATE marketing_campana_influencer SET {set_clause} WHERE id=?",
                  list(updates.values()) + [rid])
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=u, accion='ACTUALIZAR_ASIGNACION_INFLUENCER',
                tabla='marketing_campana_influencer', registro_id=rid,
                antes=antes, despues=updates)
        except Exception: pass
        conn.commit()
        return jsonify({"ok": True})
    finally:
        pass  # conexión cerrada automáticamente por teardown_appcontext

# ──────────────────────────────────────────────────────────────────────────────
# CONTENIDO
# ──────────────────────────────────────────────────────────────────────────────
# Estados del Kanban de Contenido — workflow completo de una pieza
KANBAN_ESTADOS = ["Brief", "Produccion", "Pendiente", "Publicado", "Performance"]

# Migración suave: estados antiguos ('Borrador', 'Programado') se mapean a
# Kanban al leer. Esto permite que data legacy aparezca en la columna correcta
# sin necesidad de UPDATE masivo (que destruiría histórico).
_LEGACY_ESTADO_MAP = {
    "Borrador":    "Brief",
    "Programado":  "Pendiente",
    # Publicado se mantiene
}


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
                SELECT mc.*, c.nombre as campana_nombre, i.nombre as influencer_nombre,
                       i.usuario_red as influencer_usuario, i.discount_code as influencer_code
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
                  " ORDER BY mc.fecha_programada DESC, mc.fecha_publicacion DESC, mc.fecha_creacion DESC LIMIT 200"
            rows = [dict(r) for r in c.execute(sql, params).fetchall()]
            # Normalizar estados legacy → Kanban
            for r in rows:
                est = r.get("estado") or "Brief"
                r["estado_kanban"] = _LEGACY_ESTADO_MAP.get(est, est)
            return jsonify(rows)

        d = request.get_json() or {}
        # Estado: si lo pasan se respeta, si no default 'Brief'
        estado_in = d.get("estado", "Brief")
        if estado_in in _LEGACY_ESTADO_MAP:
            estado_in = _LEGACY_ESTADO_MAP[estado_in]
        # FIX 7-jul (audit ultracode · M62/whitelist): validar el estado contra KANBAN_ESTADOS (no aceptar
        # cualquier string · evita datos basura y filas que no caen en ninguna columna del kanban).
        if estado_in not in KANBAN_ESTADOS:
            estado_in = "Brief"
        c.execute("""
            INSERT INTO marketing_contenido
            (campana_id, influencer_id, tipo, plataforma, fecha_publicacion,
             fecha_programada, estado, caption, url_publicacion,
             sku_objetivo, mensaje_principal,
             likes, comentarios, shares,
             guardados, alcance, impresiones, clicks, conversiones, notas, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d.get("campana_id"), d.get("influencer_id"),
            d.get("tipo", "Post"), d.get("plataforma", "Instagram"),
            d.get("fecha_publicacion"), d.get("fecha_programada", ""),
            estado_in,
            d.get("caption", ""), d.get("url_publicacion", ""),
            d.get("sku_objetivo", ""), d.get("mensaje_principal", ""),
            d.get("likes", 0), d.get("comentarios", 0), d.get("shares", 0),
            d.get("guardados", 0), d.get("alcance", 0), d.get("impresiones", 0),
            d.get("clicks", 0), d.get("conversiones", 0),
            d.get("notas", ""), u
        ))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201
    finally:
        pass


@bp.route("/api/marketing/contenido/kanban", methods=["GET"])
def mkt_contenido_kanban():
    """Kanban view: contenido agrupado por estado con stats por columna.

    Retorna {columnas: [{estado, count, items: [...]}]} con los 5 estados del
    Kanban. Optimizado para la UI — un solo fetch que pinta toda la tabla.
    """
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        # AUDIT 26-may · LEFT JOIN con animus_instagram_posts por url_publicacion
        # ↔ url_permalink · trae métricas REALES de IG en lugar de las manuales.
        # ig.likes/comentarios/alcance/impresiones/guardados son los del Graph
        # API en el último sync · si no hay match (pieza no publicada o URL
        # distinta), caemos a las columnas manuales de marketing_contenido.
        rows = [dict(r) for r in c.execute("""
            SELECT mc.id, mc.campana_id, mc.influencer_id, mc.tipo, mc.plataforma,
                   mc.fecha_publicacion, mc.fecha_programada, mc.estado,
                   mc.caption, mc.url_publicacion, mc.sku_objetivo,
                   mc.mensaje_principal,
                   mc.likes AS likes_manual,
                   mc.comentarios AS comentarios_manual,
                   mc.shares,
                   mc.alcance AS alcance_manual,
                   mc.conversiones,
                   mc.fecha_creacion,
                   c.nombre as campana_nombre,
                   i.nombre as influencer_nombre,
                   i.usuario_red as influencer_usuario,
                   i.discount_code as influencer_code,
                   ig.instagram_id AS ig_id,
                   ig.likes AS ig_likes,
                   ig.comentarios AS ig_comentarios,
                   ig.alcance AS ig_alcance,
                   ig.impresiones AS ig_impresiones,
                   ig.guardados AS ig_guardados,
                   ig.synced_at AS ig_synced_at
            FROM marketing_contenido mc
            LEFT JOIN marketing_campanas c ON c.id = mc.campana_id
            LEFT JOIN marketing_influencers i ON i.id = mc.influencer_id
            LEFT JOIN animus_instagram_posts ig
              ON COALESCE(mc.url_publicacion,'') != ''
             AND mc.url_publicacion = ig.url_permalink
            ORDER BY COALESCE(mc.fecha_programada, mc.fecha_publicacion, mc.fecha_creacion) DESC
            LIMIT 500
        """).fetchall()]

        # Bucket por estado_kanban (legacy → kanban)
        buckets = {est: [] for est in KANBAN_ESTADOS}
        for r in rows:
            est = r.get("estado") or "Brief"
            est_k = _LEGACY_ESTADO_MAP.get(est, est)
            if est_k not in buckets:
                # Estado raro → tirar a Brief para no perderlo
                est_k = "Brief"
            r["estado_kanban"] = est_k
            # Mezclar IG live > manual · `likes`/`comentarios`/`alcance` finales
            # son siempre los más altos disponibles entre ambas fuentes.
            ig_id = r.get('ig_id')
            r['fuente_metricas'] = 'instagram_live' if ig_id else 'manual'
            r['likes']        = r.get('ig_likes')        if ig_id else (r.get('likes_manual') or 0)
            r['comentarios']  = r.get('ig_comentarios')  if ig_id else (r.get('comentarios_manual') or 0)
            r['alcance']      = r.get('ig_alcance')      if ig_id else (r.get('alcance_manual') or 0)
            r['impresiones']  = r.get('ig_impresiones')  if ig_id else None
            r['guardados']    = r.get('ig_guardados')    if ig_id else None
            r['ig_match']     = bool(ig_id)
            buckets[est_k].append(r)

        columnas = []
        for est in KANBAN_ESTADOS:
            items = buckets[est]
            columnas.append({
                "estado": est,
                "count": len(items),
                "items": items,
            })
        total = sum(col["count"] for col in columnas)
        return jsonify({"ok": True, "total": total, "columnas": columnas})
    except Exception as e:
        log.error("marketing columnas fallo: %s", traceback.format_exc())
        return jsonify({"error": "Error interno"}), 500
    finally:
        pass


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
        campos = ["tipo", "plataforma", "fecha_publicacion", "fecha_programada",
                  "estado", "caption", "url_publicacion", "sku_objetivo",
                  "mensaje_principal", "likes", "comentarios", "shares",
                  "guardados", "alcance", "impresiones", "clicks", "conversiones",
                  "notas", "campana_id", "influencer_id"]
        updates = {k: d[k] for k in campos if k in d}
        # Normalizar estado legacy
        if "estado" in updates and updates["estado"] in _LEGACY_ESTADO_MAP:
            updates["estado"] = _LEGACY_ESTADO_MAP[updates["estado"]]
        if not updates:
            return jsonify({"error": "Nada que actualizar"}), 400
        set_clause = ", ".join(f"{k}=?" for k in updates)
        c.execute(f"UPDATE marketing_contenido SET {set_clause} WHERE id=?",
                  list(updates.values()) + [cid])
        conn.commit()
        return jsonify({"ok": True})
    finally:
        pass

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
            "SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?",
            (hace30,)
        ).fetchone()
        sh_60 = c.execute(
            "SELECT COALESCE(SUM(total),0) as rev FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en BETWEEN ? AND ?",
            (hace60, hace30)
        ).fetchone()
        # Revenue mes calendario actual
        sh_mes = c.execute(
            "SELECT COALESCE(SUM(total),0) as rev, COUNT(*) as pedidos FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?",
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
            "SELECT sku_items, total, unidades_total FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en BETWEEN ? AND ?",
            (hace90, hoy)
        ).fetchall()
        rows_ant = c.execute(
            "SELECT sku_items, total, unidades_total FROM animus_shopify_orders "
            "WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en BETWEEN ? AND ?",
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
            # FIX 7-jul (audit ultracode · M7): NO sumar unidades ERP (reciente_erp) a la REVENUE en pesos
            # (Shopify) — mezclaba magnitudes distintas → crecimiento basura. rev = solo pesos Shopify; las
            # unidades ERP siguen sumando a qty (ambas son unidades · consistente).
            rec_rev = reciente_sh.get(sku, {}).get("rev", 0)
            ant_rev = anterior_sh.get(sku, {}).get("rev", 0)
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
            FROM animus_shopify_orders
            WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') AND creado_en >= ?
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


# ── CONEXIONES / SYNC ─────────────────────────────────────────────────────────

@bp.route("/api/marketing/ghl-debug")
def ghl_debug():
    """Diagnóstico: key en BD + 3 variantes de llamada a GHL.

    ADMIN ONLY — expone configuración sensible de la integración GHL.
    """
    u, err, code = _admin_only()
    if err:
        return err, code
    import urllib.error as _ue
    conn = get_db()  # M82 · PgConnection no soporta `with` (sin __enter__) → 500 PG-only
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
                    # SHOPIFY-AUDIT 23-may-PM · fetch_with_retry para 429/5xx
                    from http_helpers import fetch_with_retry as _fwr
                    with _fwr(req, timeout=20, max_intentos=3) as r:
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
                    # Capturar discount codes usados en la orden — es lo que
                    # atribuye la venta al influencer correspondiente.
                    # Shopify retorna: discount_codes: [{code, amount, type}, ...]
                    dc_list = o.get("discount_codes", []) or []
                    dc_codes = ",".join(
                        (dc.get("code") or "").upper().strip()
                        for dc in dc_list if dc.get("code")
                    )
                    subtotal_o = float(o.get("subtotal_price") or 0)
                    total_desc = float(o.get("total_discounts") or 0)
                    # FIX 23-may-2026 · auditoría · Bug TZ Bogotá del 22-may
                    # NO se aplicó al sync de marketing/influencer · ventas
                    # tarde-noche desaparecían del cálculo ROI · ahora TZ-aware
                    try:
                        from blueprints.auto_plan_jobs import _shopify_created_at_bogota as _tz_h
                        _creado = _tz_h(o.get("created_at",""))
                    except Exception:
                        _creado = (o.get("created_at") or "")[:10]
                    conn.execute("""INSERT OR REPLACE INTO animus_shopify_orders
                        (shopify_id,nombre,email,total,moneda,estado,estado_pago,
                         sku_items,unidades_total,ciudad,pais,creado_en,synced_at,
                         discount_codes,subtotal,total_descuentos)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,datetime('now', '-5 hours'),?,?,?)""",
                        (str(o["id"]), o.get("name",""), o.get("email",""),
                         float(o.get("total_price") or 0),
                         o.get("currency","COP"),
                         # FIX 7-jul (audit ultracode · M45): la marca de cancelación es cancelled_at (Shopify NO
                         # la pone en fulfillment_status). Sin esto, re-sincronizar revertía 'cancelled'→'unfulfilled'
                         # (ON CONFLICT DO UPDATE) → las canceladas volvían a contar como venta en TODO el sistema
                         # (deshacía el fix del 27-jun). = writer canónico shopify_client.py:151.
                         ('cancelled' if (o.get('cancelled_at') or '').strip() else (o.get("fulfillment_status") or "unfulfilled")),
                         o.get("financial_status",""),
                         items_sku, total_uds, ciudad,
                         addr.get("country_code","CO"),
                         _creado,
                         dc_codes, subtotal_o, total_desc))
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
                # FIX 27-may (P2) · urlencode params · si loc_id/startAfter
                # tienen `&` o `=`, rompen el query string.
                from urllib.parse import quote as _q
                params = f"locationId={_q(str(loc_id), safe='')}&limit=100"
                if start_after:
                    params += f"&startAfter={_q(str(start_after), safe='')}&startAfterId={_q(str(start_after_id), safe='')}"
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
                        VALUES(?,?,?,?,?,?,?,datetime('now', '-5 hours'))""",
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
            # AUDIT 26-may · ADEMÁS sync opportunities (pipelines) GHL
            synced_opps = 0
            try:
                # Listar pipelines primero (necesitamos sus nombres)
                pl_url = f"https://services.leadconnectorhq.com/opportunities/pipelines?locationId={loc_id}"
                pl_req = urllib.request.Request(pl_url, headers=ghl_headers)
                pipelines_by_id = {}
                stages_by_id = {}
                try:
                    with urllib.request.urlopen(pl_req, timeout=20) as r:
                        pl_payload = json.loads(r.read())
                        for p in pl_payload.get("pipelines", []):
                            pipelines_by_id[p.get("id","")] = p.get("name","")
                            for st in p.get("stages", []):
                                stages_by_id[st.get("id","")] = st.get("name","")
                except Exception as _pl_e:
                    log.warning("ghl pipelines fetch fallo: %s", _pl_e)
                # Listar opportunities (paginado)
                opp_start_after = None
                opp_start_after_id = None
                while True:
                    op_params = f"location_id={loc_id}&limit=100"
                    if opp_start_after:
                        op_params += f"&startAfter={opp_start_after}&startAfterId={opp_start_after_id}"
                    op_url = f"https://services.leadconnectorhq.com/opportunities/search?{op_params}"
                    op_req = urllib.request.Request(op_url, headers=ghl_headers)
                    try:
                        with urllib.request.urlopen(op_req, timeout=20) as r:
                            op_payload = json.loads(r.read())
                    except urllib.error.HTTPError as _he:
                        # Si /opportunities/search no está habilitado en el plan GHL,
                        # log y seguir sin opportunities
                        log.warning("ghl opportunities HTTP %s: %s", _he.code,
                                     _he.read().decode('utf-8', errors='replace')[:200])
                        break
                    except Exception as _oe:
                        log.warning("ghl opportunities fetch fallo: %s", _oe)
                        break
                    opps = op_payload.get("opportunities", []) or []
                    if not opps:
                        break
                    for o in opps:
                        try:
                            conn.execute("""INSERT OR REPLACE INTO animus_ghl_opportunities
                                (ghl_id, ghl_contact_id, ghl_pipeline_id, ghl_stage_id,
                                 nombre, pipeline_nombre, stage_nombre, status,
                                 monetary_value, source, assigned_to,
                                 ghl_created_at, ghl_updated_at, synced_at)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','-5 hours'))""",
                                (o.get("id",""),
                                 (o.get("contact", {}) or {}).get("id") or o.get("contactId",""),
                                 o.get("pipelineId",""),
                                 o.get("pipelineStageId",""),
                                 o.get("name",""),
                                 pipelines_by_id.get(o.get("pipelineId",""), ""),
                                 stages_by_id.get(o.get("pipelineStageId",""), ""),
                                 (o.get("status","") or "").lower(),
                                 float(o.get("monetaryValue") or 0),
                                 o.get("source","") or "",
                                 o.get("assignedTo","") or "",
                                 o.get("createdAt","") or "",
                                 o.get("updatedAt","") or ""))
                            synced_opps += 1
                        except Exception as _ie:
                            log.warning("ghl opp insert fallo id=%s: %s", o.get("id"), _ie)
                    op_meta = op_payload.get("meta", {}) or {}
                    opp_start_after = op_meta.get("startAfter")
                    opp_start_after_id = op_meta.get("startAfterId")
                    if not opp_start_after or len(opps) < 100:
                        break
            except Exception as _oe:
                log.warning("ghl opportunities sync skipped: %s", _oe)
            conn.commit()
            return jsonify({"ok": True, "synced": synced, "synced_opportunities": synced_opps, "platform": "ghl"})

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
                    VALUES(?,?,?,?,?,?,?,?,datetime('now', '-5 hours'))""",
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
    """ADMIN ONLY — expone tokens y configuración Meta/Instagram."""
    u, err, code = _admin_only()
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

# ──────────────────────────────────────────────────────────────────────────────
# PANEL INFLUENCERS — vista unificada perfil + historial de pagos
# ──────────────────────────────────────────────────────────────────────────────

@bp.route("/api/marketing/debug-influencers", methods=["GET"])
def mkt_debug_influencers():
    """ADMIN ONLY — diagnóstico de tablas de influencers + solicitudes.
    Antes era público, ahora restringido (expone IDs y nombres internos).
    """
    u, err, code = _admin_only()
    if err:
        return err, code
    conn = _db()
    cur = conn.cursor()
    # Count marketing_influencers
    mi_count = cur.execute("SELECT COUNT(*) FROM marketing_influencers").fetchone()[0]
    try:
        mi_rows = [dict(r) for r in cur.execute("SELECT id,nombre,estado,banco,cuenta_bancaria FROM marketing_influencers LIMIT 20").fetchall()]
    except Exception:
        mi_rows = [dict(r) for r in cur.execute("SELECT id,nombre,estado FROM marketing_influencers LIMIT 20").fetchall()]
    # Count solicitudes influencer
    sol_count = cur.execute("SELECT COUNT(*) FROM solicitudes_compra WHERE categoria='Influencer/Marketing Digital'").fetchone()[0]
    sol_rows = [dict(r) for r in cur.execute(
        "SELECT numero,solicitante,estado,valor,influencer_id FROM solicitudes_compra WHERE categoria='Influencer/Marketing Digital' ORDER BY fecha DESC LIMIT 20"
    ).fetchall()]
    # Check if column exists
    try:
        cur.execute("SELECT influencer_id FROM solicitudes_compra LIMIT 1")
        has_inf_id = True
    except Exception as e:
        has_inf_id = str(e)
    return jsonify({
        "marketing_influencers_count": mi_count,
        "marketing_influencers": mi_rows,
        "solicitudes_influencer_count": sol_count,
        "solicitudes_influencer": sol_rows,
        "has_influencer_id_column": has_inf_id,
    })


@bp.route("/api/marketing/influencers-panel", methods=["GET"])
def mkt_influencers_panel():
    """Vista unificada: perfiles marketing_influencers + pagos desde pagos_influencers."""
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        q = request.args.get("q", "").strip()
        estado_fil = request.args.get("estado", "")

        # 1. Todos los influencers del catálogo
        conds, params = [], []
        if q:
            conds.append("(nombre LIKE ? OR usuario_red LIKE ? OR nicho LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if estado_fil:
            conds.append("estado=?")
            params.append(estado_fil)
        base_sql = "SELECT * FROM marketing_influencers"
        sql = base_sql + (" WHERE " + " AND ".join(conds) if conds else "") + " ORDER BY nombre"
        influencers = [dict(r) for r in c.execute(sql, params).fetchall()]

        # Sebastián 25-may-2026 PM · audit P0 · Habeas Data Ley 1581 CO
        # `/influencers-panel` fugaba banco/cuenta_bancaria/cedula_nit/
        # tipo_cuenta a usuarios marketing no-admin. El fix 7b8345e
        # solo cubrio /mkt_influencers GET (line 940) pero no este endpoint.
        # Ahora enmascara con '***' si el caller no es ADMIN+CONTADORA.
        try:
            _u_lower = (u or '').lower()
            _puede_ver_banco = _u_lower in {
                x.lower() for x in (set(ADMIN_USERS) | set(CONTADORA_USERS))}
        except Exception:
            _puede_ver_banco = False
        if not _puede_ver_banco:
            for _inf in influencers:
                for _campo_sensible in ('banco', 'cuenta_bancaria',
                                          'tipo_cuenta', 'cedula_nit'):
                    if _inf.get(_campo_sensible):
                        _inf[_campo_sensible] = '***'

        # AUTO-BACKFILL: corregir filas mal-marcadas como 'Pendiente'.
        # Reglas:
        #   1. OC asociada en estado 'Pagada'/'Recibida'/'Parcial' (>=80% pagado)
        #      → la fila debe estar 'Pagada' (sync con realidad).
        #   2. OC asociada 'Rechazada'/'Cancelada' → eliminar la fila para que el
        #      influencer no aparezca con badge naranja por solicitudes muertas.
        #   3. Fila historica con fecha_publicacion en el pasado y SIN OC valida
        #      → marcar 'Pagada' (es historico, ya ocurrio).
        try:
            # FIX 7-jul (audit ultracode · M4/Part 11): (a) acumular el rowcount de los 4 statements — antes se
            # commiteaba solo `if c.rowcount` (el del ÚLTIMO) → si el 1º cambiaba filas pero el último 0, esos
            # cambios se PERDÍAN al cerrar la conexión; (b) auditar (muta DINERO en un GET · antes sin rastro).
            _tot_bf = 0
            c.execute("""
                UPDATE pagos_influencers
                SET estado='Pagada'
                WHERE estado='Pendiente'
                  AND numero_oc IN (
                    SELECT numero_oc FROM ordenes_compra
                    WHERE estado IN ('Pagada','Recibida','Parcial')
                  )
            """)
            _tot_bf += c.rowcount or 0
            _del_ids_bf = [r[0] for r in c.execute(
                "SELECT id FROM pagos_influencers WHERE estado='Pendiente' AND numero_oc IN "
                "(SELECT numero_oc FROM ordenes_compra WHERE estado IN ('Rechazada','Cancelada'))").fetchall()]
            c.execute("""
                DELETE FROM pagos_influencers
                WHERE estado='Pendiente'
                  AND numero_oc IN (
                    SELECT numero_oc FROM ordenes_compra
                    WHERE estado IN ('Rechazada','Cancelada')
                  )
            """)
            _tot_bf += c.rowcount or 0
            # Historicos sin OC valida y con fecha_publicacion pasada -> Pagada
            c.execute("""
                UPDATE pagos_influencers
                SET estado='Pagada'
                WHERE estado='Pendiente'
                  AND COALESCE(fecha_publicacion,'') != ''
                  AND fecha_publicacion < date('now', '-5 hours', '-7 day')
                  AND (numero_oc IS NULL OR numero_oc='' OR numero_oc NOT IN (
                    SELECT numero_oc FROM ordenes_compra WHERE estado IN ('Aprobada','Autorizada','Revisada','Borrador')
                  ))
            """)
            _tot_bf += c.rowcount or 0
            if _tot_bf:
                try:
                    from audit_helpers import audit_log as _alog_bf
                    _alog_bf(c, usuario=u, accion='AUTO_BACKFILL_PAGOS_INFLUENCER',
                             tabla='pagos_influencers',
                             registro_id=(str(_del_ids_bf[0]) if _del_ids_bf else '0'),
                             despues={'tocados': _tot_bf, 'borrados_ids': _del_ids_bf})
                except Exception:
                    pass
                conn.commit()
        except Exception:
            pass

        # 2. Pagos desde pagos_influencers con estado calculado segun realidad
        # Logica clara y determinista (decision Sebastian 2026-04-28):
        #   - 'Pagada'    → OC efectivamente pagada (Pagada/Recibida/Parcial)
        #                   o historico explicito sin OC vinculada
        #   - 'Pendiente' → SOLO si hay solicitud activa reciente (<90 dias)
        #                   en estado Aprobada/Autorizada/Revisada/Borrador
        #   - NULL        → ignorar (no afecta badge ni totales)
        try:
            pago_rows = c.execute("""
                SELECT pi.id, pi.influencer_id, pi.influencer_nombre,
                       pi.valor, pi.fecha,
                       CASE
                         WHEN COALESCE(oc.estado,'') IN ('Pagada','Recibida','Parcial')
                           THEN 'Pagada'
                         WHEN COALESCE(oc.estado,'') IN ('Rechazada','Cancelada')
                           THEN NULL
                         WHEN COALESCE(oc.estado,'') = '' AND pi.estado = 'Pagada'
                              AND pi.fecha >= date('now', '-5 hours', '-180 day')
                           THEN 'Pagada'
                         WHEN COALESCE(oc.estado,'') = ''
                           THEN NULL
                         WHEN oc.estado IN ('Aprobada','Autorizada','Revisada','Borrador')
                              AND oc.fecha >= date('now', '-5 hours', '-90 day')
                           THEN 'Pendiente'
                         ELSE NULL
                       END as estado,
                       pi.concepto, pi.numero_oc
                FROM pagos_influencers pi
                LEFT JOIN ordenes_compra oc ON oc.numero_oc = pi.numero_oc
                ORDER BY pi.fecha DESC
            """).fetchall()
            # Filtrar filas con estado=None (no aplican)
            pago_list = [dict(r) for r in pago_rows if r['estado'] is not None]
        except Exception:
            pago_list = []

        # Index by influencer_id and by nombre (lower)
        pagos_by_id   = {}
        pagos_by_name = {}
        for p in pago_list:
            if p["influencer_id"]:
                pagos_by_id.setdefault(p["influencer_id"], []).append(p)
            key = (p["influencer_nombre"] or "").strip().lower()
            if key:
                pagos_by_name.setdefault(key, []).append(p)

        # 2b. Auto-crear influencers desde pagos_influencers (nombres sin perfil)
        known_lower = {inf["nombre"].strip().lower() for inf in influencers}
        nuevos = []
        for p in pago_list:
            nm = (p["influencer_nombre"] or "").strip()
            if nm and nm.lower() not in known_lower:
                known_lower.add(nm.lower())
                nuevos.append(nm)
        if nuevos:
            for nm in nuevos:
                # FIX 1-jun-2026: con UNIQUE index en LOWER(TRIM(nombre)) el OR IGNORE
                # por fin deduplica · el try evita 500 si el index rechaza un race
                # cross-worker (3 gunicorn workers creaban dups · 'todos juanito rebel').
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO marketing_influencers (nombre, red_social, estado) VALUES (?,?,?)",
                        (nm, "Instagram", "Activo")
                    )
                except Exception:
                    pass
            conn.commit()
            # Recargar lista completa
            sql2 = base_sql + (" WHERE " + " AND ".join(conds) if conds else "") + " ORDER BY nombre"
            influencers = [dict(r) for r in c.execute(sql2, params).fetchall()]
            # Re-indexar pagos por id
            pagos_by_id.clear()
            pagos_by_name.clear()
            for p in pago_list:
                if p["influencer_id"]:
                    pagos_by_id.setdefault(p["influencer_id"], []).append(p)
                key = (p["influencer_nombre"] or "").strip().lower()
                if key:
                    pagos_by_name.setdefault(key, []).append(p)

        # PERF-FIX 27-may-2026 PM v2 · Sebastián · "se demora mucho en cargar
        # los influencers". Antes (v1) iteraba TODA la lista de ~5000 orders por
        # CADA influencer con substring search · 50 inf × 5000 orders = 250K
        # operaciones por endpoint call · varios segundos en Python.
        # AHORA (v2): índice invertido CODE_UP → [(total, uds), ...] · pre-
        # parseamos discount_codes (split por coma/pipe/punto-coma) en 1 sola
        # pasada · luego lookup O(1) en el loop por influencer.
        import re as _re_pf
        _SEP_CUPON = _re_pf.compile(r'[,;|]')
        code_to_orders = {}  # CODE_UP → list[(total, uds)]
        try:
            for r in c.execute("""
                SELECT UPPER(COALESCE(discount_codes,'')) AS codes_up,
                       COALESCE(total,0) AS total,
                       COALESCE(unidades_total,0) AS uds
                FROM animus_shopify_orders
                WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                  AND COALESCE(discount_codes,'') != ''
            """).fetchall():
                codes_up = (r['codes_up'] or '').strip()
                if not codes_up: continue
                tot = float(r['total'] or 0)
                uds = int(r['uds'] or 0)
                # Split por separadores comunes + quitar comillas/brackets de JSON
                _cleaned = codes_up.replace('[','').replace(']','').replace('"','').replace("'",'')
                codes_set = {c.strip() for c in _SEP_CUPON.split(_cleaned) if c.strip()}
                for code in codes_set:
                    code_to_orders.setdefault(code, []).append((tot, uds))
        except Exception:
            code_to_orders = {}

        # 3. Merge
        now_month = (datetime.now() - timedelta(hours=5)).strftime("%Y-%m")  # Colombia · M24
        result = []
        for inf in influencers:
            iid = inf["id"]
            inombre_low = inf["nombre"].strip().lower()

            pagos = pagos_by_id.get(iid, [])
            # Avoid double-counting if already linked by id
            if not pagos:
                pagos = pagos_by_name.get(inombre_low, [])
            else:
                # merge name matches that lack influencer_id
                for p in pagos_by_name.get(inombre_low, []):
                    if p["influencer_id"] is None:
                        pagos.append(p)

            # dedup by id
            seen, pagos_uniq = set(), []
            for p in pagos:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    pagos_uniq.append(p)

            pagadas   = [p for p in pagos_uniq if p["estado"] == "Pagada"]
            pendientes = [p for p in pagos_uniq if p["estado"] == "Pendiente"]
            mes_pagos = [p for p in pagadas if (p["fecha"] or "").startswith(now_month)]

            inf["pagos"]             = pagos_uniq
            inf["total_pagado"]      = sum(p["valor"] or 0 for p in pagadas)
            inf["total_pendiente"]   = sum(p["valor"] or 0 for p in pendientes)
            inf["pagos_count"]       = len(pagadas)
            inf["pendiente_count"]   = len(pendientes)
            inf["pagado_mes_actual"] = sum(p["valor"] or 0 for p in mes_pagos)
            inf["ultimo_pago"]       = pagadas[0]["fecha"] if pagadas else None
            inf["tiene_pendiente"]   = len(pendientes) > 0

            # Calcular alerta "toca pagar" segun ciclo de pago configurado
            ciclo = (inf.get("ciclo_pago") or "Mensual").strip()
            ciclo_dias_map = {"Mensual": 30, "Bimensual": 60, "Trimestral": 90,
                              "Unico": 99999, "Único": 99999, "Sin ciclo": 99999}
            dias_ciclo = ciclo_dias_map.get(ciclo, 30)
            toca_pagar = False
            dias_desde = None
            proximo_pago = None
            if inf["ultimo_pago"] and not inf["tiene_pendiente"] and dias_ciclo < 99999:
                try:
                    from datetime import datetime as _dt, timedelta as _td
                    fecha_ult = _dt.strptime(inf["ultimo_pago"][:10], "%Y-%m-%d")
                    fecha_prox = fecha_ult + _td(days=dias_ciclo)
                    dias_desde = (_dt.now() - fecha_ult).days
                    proximo_pago = fecha_prox.strftime("%Y-%m-%d")
                    toca_pagar = dias_desde >= dias_ciclo
                except Exception:
                    pass
            inf["toca_pagar"]            = toca_pagar
            inf["dias_desde_ultimo_pago"] = dias_desde
            inf["proximo_pago_estimado"] = proximo_pago

            # AUDIT 26-may · revenue atribuible desde Shopify si tiene cupón
            # PERF-FIX 27-may PM v2 · lookup O(1) en dict invertido code_to_orders
            # · antes era O(N orders) por cada influencer · ahora O(1).
            dcode = (inf.get("discount_code") or '').strip()
            if dcode:
                try:
                    _matches = code_to_orders.get(dcode.upper(), [])
                    _rev = sum(m[0] for m in _matches)
                    _uds = sum(m[1] for m in _matches)
                    _n = len(_matches)
                    inf["revenue_atribuible"] = _rev
                    inf["pedidos_atribuibles"] = _n
                    inf["unidades_atribuibles"] = _uds
                    pagado = float(inf.get("total_pagado") or 0)
                    inf["roi_implicito_pct"] = round(
                        ((_rev - pagado) / pagado) * 100, 1
                    ) if pagado > 0 else None
                except Exception:
                    inf["revenue_atribuible"] = 0
                    inf["pedidos_atribuibles"] = 0
                    inf["unidades_atribuibles"] = 0
                    inf["roi_implicito_pct"] = None
            else:
                inf["revenue_atribuible"] = 0
                inf["pedidos_atribuibles"] = 0
                inf["unidades_atribuibles"] = 0
                inf["roi_implicito_pct"] = None

            result.append(inf)

        # 4. KPIs
        now_year = (datetime.now() - timedelta(hours=5)).year  # Colombia · M24 (evita saltar de año en la noche UTC)
        total_pagado_anio = sum(
            p["valor"] or 0
            for p in pago_list
            if p["estado"] == "Pagada" and (p["fecha"] or "").startswith(str(now_year))
        )
        total_pendiente_v = sum(p["valor"] or 0 for p in pago_list if p["estado"] == "Pendiente")
        total_activos     = len([i for i in result if i.get("estado") == "Activo"])
        con_pendiente     = len([i for i in result if i["tiene_pendiente"]])

        return jsonify({
            "influencers": result,
            "kpis": {
                "total_activos":   total_activos,
                "total":           len(result),
                "pagado_mes":      sum(inf["pagado_mes_actual"] for inf in result),
                "total_pendiente": total_pendiente_v,
                "con_pendiente":   con_pendiente,
                "pagado_anio":     total_pagado_anio,
            }
        })
    except Exception as _exc:
        import traceback as _tb
        return jsonify({
            "influencers": [],
            "kpis": {},
            "_error": str(_exc),
            "_trace": _tb.format_exc()[-800:]
        }), 200
    finally:
        pass


_ATRIB_CACHE = {}   # {desde: {ts, payload}} · cache per-worker · atribución = overview 90d


@bp.route("/api/marketing/atribucion-influencers", methods=["GET"])
def mkt_atribucion_influencers():
    """Atribución de ventas Shopify por influencer via discount_code.

    Para cada influencer con discount_code asignado, busca en
    animus_shopify_orders todas las órdenes que usaron ese código y agrega:
      - n_pedidos       : cantidad de órdenes
      - revenue_total   : suma de total (post-descuento)
      - subtotal_total  : suma pre-descuento (mide demanda real)
      - descuento_total : suma de descuentos otorgados
      - unidades        : suma de unidades vendidas
      - clientes_unicos : emails distintos
      - ultimo_pedido   : fecha más reciente
      - roi_estimado    : revenue_total / inversion_pagada (si hay pago)

    Query param `desde` (YYYY-MM-DD) limita el periodo. Default: últimos 90d.
    """
    u, err, code = _auth()
    if err:
        return err, code
    desde = (request.args.get("desde") or "").strip()
    if not desde:
        desde = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    # Cache TTL (PERF · Sebastián 13-jul: la carga tardaba ~1 min). Atribución = overview
    # 90d → staleness de minutos aceptable. `?force=1` (botón refrescar) salta el cache.
    import time as _time
    _force = (request.args.get("force") or "") not in ("", "0", "false")
    _hit = _ATRIB_CACHE.get(desde)
    if _hit and not _force and (_time.time() - _hit["ts"] < 600):
        return jsonify(_hit["payload"])

    conn = _db()
    c = conn.cursor()
    try:
        infs = c.execute("""
            SELECT id, nombre, usuario_red, red_social, discount_code, estado
            FROM marketing_influencers
            WHERE COALESCE(discount_code,'') != ''
            ORDER BY nombre
        """).fetchall()
        # PERF FIX (antes: N+1 · 1 escaneo de animus_shopify_orders POR influencer con
        # LIKE '%,code,%' sin índice = ~72 full-scans = 1 min). Ahora: UNA sola pasada por
        # las órdenes del período, agregando por discount_code en Python.
        code2id = {}
        infmap = {}
        agg = {}
        for r in infs:
            cv = (r["discount_code"] or "").upper().strip()
            if not cv:
                continue
            code2id[cv] = r["id"]
            infmap[r["id"]] = r
            agg[r["id"]] = {"n": 0, "rev": 0.0, "sub": 0.0, "desc": 0.0,
                            "uds": 0, "emails": set(), "ult": ""}
        if code2id:
            for o in c.execute("""
                SELECT COALESCE(discount_codes,'') dc, COALESCE(total,0) total,
                       COALESCE(subtotal,0) subtotal, COALESCE(total_descuentos,0) tdesc,
                       COALESCE(unidades_total,0) uds, COALESCE(email,'') email,
                       COALESCE(creado_en,'') creado_en
                FROM animus_shopify_orders
                WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                  AND creado_en >= ?
            """, (desde,)).fetchall():
                dc = (o["dc"] or "").upper()
                if not dc:
                    continue
                for cod in set(x.strip() for x in dc.split(',') if x.strip()):
                    iid = code2id.get(cod)
                    if iid is None:
                        continue
                    a = agg[iid]
                    a["n"] += 1
                    a["rev"] += float(o["total"] or 0)
                    a["sub"] += float(o["subtotal"] or 0)
                    a["desc"] += float(o["tdesc"] or 0)
                    a["uds"] += int(o["uds"] or 0)
                    if o["email"]:
                        a["emails"].add(o["email"])
                    if o["creado_en"] and o["creado_en"] > a["ult"]:
                        a["ult"] = o["creado_en"]
        # Inversión pagada por influencer · UNA query agrupada (antes: 1 por influencer)
        inv_map = {}
        for pr in c.execute("""
            SELECT influencer_id, COALESCE(SUM(valor),0) t
            FROM pagos_influencers
            WHERE estado = 'Pagada' AND fecha >= ?
            GROUP BY influencer_id
        """, (desde,)).fetchall():
            inv_map[pr["influencer_id"]] = pr["t"] or 0

        resultado = []
        for iid, r in infmap.items():
            a = agg[iid]
            revenue = a["rev"]
            invertido = inv_map.get(iid, 0) or 0
            roi_pct = round((revenue - invertido) / invertido * 100, 1) if invertido > 0 else None
            resultado.append({
                "influencer_id":   iid,
                "nombre":          r["nombre"],
                "usuario_red":     r["usuario_red"] or "",
                "red_social":      r["red_social"] or "",
                "discount_code":   (r["discount_code"] or "").upper().strip(),
                "estado":          r["estado"] or "",
                "n_pedidos":       a["n"],
                "revenue_total":   round(revenue, 0),
                "subtotal_total":  round(a["sub"], 0),
                "descuento_total": round(a["desc"], 0),
                "unidades":        a["uds"],
                "clientes_unicos": len(a["emails"]),
                "ultimo_pedido":   a["ult"],
                "invertido":       round(invertido, 0),
                "roi_pct":         roi_pct,
            })

        # Ordenar: revenue desc → ranking de influencers más rentables
        resultado.sort(key=lambda x: -x["revenue_total"])

        # KPIs globales del programa
        kpis = {
            "influencers_con_code": len(resultado),
            "revenue_atribuido":    sum(x["revenue_total"] for x in resultado),
            "pedidos_atribuidos":   sum(x["n_pedidos"]     for x in resultado),
            "inversion_total":      sum(x["invertido"]     for x in resultado),
            "descuento_total":      sum(x["descuento_total"] for x in resultado),
        }
        kpis["roi_global_pct"] = (
            round((kpis["revenue_atribuido"] - kpis["inversion_total"])
                  / kpis["inversion_total"] * 100, 1)
            if kpis["inversion_total"] > 0 else None
        )

        payload = {
            "ok": True,
            "desde": desde,
            "kpis": kpis,
            "influencers": resultado,
        }
        _ATRIB_CACHE[desde] = {"ts": _time.time(), "payload": payload}
        return jsonify(payload)
    except Exception as e:
        # Fix 28-may · no filtrar traceback del servidor al cliente.
        log.error("mkt_atribucion_influencers fallo: %s", traceback.format_exc())
        return jsonify({"error": "Error procesando atribución de influencers"}), 500
    finally:
        pass


@bp.route("/api/marketing/pagos-historico-cleanup", methods=["POST"])
def mkt_pagos_historico_cleanup():
    """Marca como Pagada los pagos_influencers con concepto 'Pago histórico
    importado' que están en estado Pendiente. Sebastian (30-abr-2026):
    "esos pendientes con histórico importado deberían organizarse" — eran
    pagos legacy que se importaron desde Excel cuando arrancó el sistema,
    pero quedaron en Pendiente artificialmente. Solo admin."""
    u, err, code = _admin_only()
    if err:
        return err, code
    body = request.get_json(silent=True) or {}
    confirm = body.get('confirm') is True
    conn = _db(); c = conn.cursor()
    try:
        cands = c.execute("""SELECT id, influencer_nombre, valor, fecha, concepto
                              FROM pagos_influencers
                              WHERE estado='Pendiente'
                                AND (LOWER(COALESCE(concepto,'')) LIKE '%histórico%'
                                  OR LOWER(COALESCE(concepto,'')) LIKE '%historico%'
                                  OR LOWER(COALESCE(concepto,'')) LIKE '%importado%')""").fetchall()
        cands = [dict(r) if hasattr(r, 'keys') else
                 {'id': r[0], 'influencer_nombre': r[1], 'valor': r[2],
                  'fecha': r[3], 'concepto': r[4]} for r in cands]
        if not confirm:
            return jsonify({
                'dry_run': True,
                'total': len(cands),
                'candidatos': cands,
                'mensaje': f'{len(cands)} pagos histórico importado en Pendiente. POST {{"confirm":true}} para marcar Pagada.'
            })
        ids = [int(x['id']) for x in cands]
        if ids:
            placeholders = ','.join('?'*len(ids))
            c.execute(f"UPDATE pagos_influencers SET estado='Pagada' WHERE id IN ({placeholders})", ids)
            # Sebastián 25-may-2026 PM · audit P2 · UPDATE masivo Pagada sin
            # audit antes. Acción admin · dinero · CRÍTICO trazabilidad.
            try:
                from audit_helpers import audit_log as _al
                _al(c, usuario=u, accion='PAGOS_HISTORICO_CLEANUP',
                    tabla='pagos_influencers', registro_id='_BULK_',
                    despues={'ids_marcados_pagada': ids,
                              'total': len(ids),
                              'snapshot_first_20': cands[:20]})
            except Exception: pass
            conn.commit()
        return jsonify({'ok': True, 'actualizados': len(ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route("/api/marketing/pagos-influencer/<int:pid>", methods=["PATCH", "DELETE"])
def mkt_pago_influencer_editar(pid):
    """Edita o elimina un pago a influencer (admin/contadora).

    Sebastián 27-may-2026 PM · Jefferson dice "salen pendientes a personas que
    ya se les pago, y otros pendientes que no estan · debe existir la opcion
    de que el lo modifique en caso tal de que este mal".

    PATCH body: {estado: 'Pagada'|'Pendiente'|'Anulada', valor?, concepto?,
                 fecha_contenido?, motivo: str≥10}
    DELETE: borra el registro · solo si NO está vinculado a OC con pago real.

    audit_log obligatorio. Solo admin o contadora.
    """
    u, err, code = _auth()
    if err: return err, code
    # Auth · admin o contadora (jeferson en CONTADORA_USERS o ADMIN_USERS)
    try:
        from config import ADMIN_USERS as _AU, CONTADORA_USERS as _CU
    except Exception:
        _AU = {'sebastian','alejandro'}; _CU = set()
    actor_lower = (u or '').lower()
    permitidos = {x.lower() for x in (set(_AU) | set(_CU) | {'jeferson','jefferson'})}
    if actor_lower not in permitidos:
        return jsonify({'error': 'Solo admin / contadora / marketing-jeferson'}), 403
    conn = _db(); c = conn.cursor()
    row = c.execute(
        "SELECT id, influencer_id, influencer_nombre, valor, estado, concepto, numero_oc, fecha, fecha_contenido FROM pagos_influencers WHERE id=?",
        (pid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'pago no encontrado'}), 404
    antes = dict(row)

    if request.method == 'DELETE':
        # Verificar que no esté vinculado a OC pagada (no permitir borrar pago real)
        numero_oc = (antes.get('numero_oc') or '').strip()
        if numero_oc:
            oc_row = c.execute(
                "SELECT estado FROM ordenes_compra WHERE numero_oc=?",
                (numero_oc,)
            ).fetchone()
            if oc_row and (oc_row[0] or '').strip() in ('Pagada', 'Recibida', 'Parcial'):
                return jsonify({
                    'error': f"No se puede borrar · pago vinculado a OC {numero_oc} estado={oc_row[0]} (pagada real). Use anular si necesita revertir.",
                    'codigo': 'PAGO_VINCULADO_A_OC_PAGADA',
                }), 409
        # Motivo obligatorio
        d = request.get_json(silent=True) or {}
        motivo = (d.get('motivo') or '').strip()
        if len(motivo) < 10:
            return jsonify({'error': 'motivo (≥10 chars) requerido para auditoría'}), 400
        try:
            c.execute("DELETE FROM pagos_influencers WHERE id=?", (pid,))
            try:
                from audit_helpers import audit_log as _alog
                _alog(c, usuario=u, accion='DELETE_PAGO_INFLUENCER',
                      tabla='pagos_influencers', registro_id=str(pid),
                      antes=antes,
                      despues={'motivo': motivo, 'borrado_por': u})
            except Exception:
                pass
            conn.commit()
            return jsonify({'ok': True, 'borrado': True, 'id': pid, 'motivo': motivo})
        except Exception as e:
            return jsonify({'error': str(e)[:200]}), 500

    # PATCH
    d = request.get_json(silent=True) or {}
    motivo = (d.get('motivo') or '').strip()
    if len(motivo) < 10:
        return jsonify({'error': 'motivo (≥10 chars) requerido para auditoría INVIMA'}), 400
    estados_validos = {'Pagada', 'Pendiente', 'Anulada'}
    nuevo_estado = (d.get('estado') or antes['estado'] or 'Pendiente').strip()
    if nuevo_estado not in estados_validos:
        return jsonify({'error': f'estado inválido · permitidos: {sorted(estados_validos)}'}), 400
    try:
        nuevo_valor = float(d.get('valor')) if d.get('valor') is not None else float(antes['valor'] or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'valor inválido'}), 400
    if nuevo_valor < 0:
        return jsonify({'error': 'valor no puede ser negativo'}), 400
    nuevo_concepto = (d.get('concepto') or antes['concepto'] or '').strip()[:300]
    nueva_fc = d.get('fecha_contenido') or antes['fecha_contenido'] or ''
    if nueva_fc:
        import re as _reFC
        if not _reFC.match(r'^\d{4}-\d{2}-\d{2}$', str(nueva_fc).strip()):
            return jsonify({'error': 'fecha_contenido formato YYYY-MM-DD'}), 400
    # Recalcular vence_pago_at si cambió fecha_contenido
    nuevo_vence = ''
    if nueva_fc:
        try:
            from datetime import datetime as _dtFC, timedelta as _tdFC
            _b = _dtFC.strptime(str(nueva_fc).strip(), '%Y-%m-%d')
            nuevo_vence = (_b + _tdFC(days=30)).strftime('%Y-%m-%d')
        except Exception:
            pass
    # FIX 7-jul (audit ultracode · money · espejo del guard del DELETE): si el pago está ligado a una OC pagada
    # REAL, no permitir cambiar el valor ni des-marcarlo de 'Pagada' desde acá (revertir va por el flujo de OC).
    _noc = (antes.get('numero_oc') or '').strip()
    if _noc:
        _ocr = c.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (_noc,)).fetchone()
        if _ocr and (_ocr[0] or '').strip() in ('Pagada', 'Recibida', 'Parcial'):
            if abs(round(nuevo_valor) - float(antes.get('valor') or 0)) > 0.5 or nuevo_estado != 'Pagada':
                return jsonify({
                    'error': f"Pago vinculado a la OC {_noc} ({_ocr[0]}, pago real) · no se puede cambiar el valor ni des-marcarlo acá. Revertí desde la OC.",
                    'codigo': 'PAGO_VINCULADO_A_OC_PAGADA',
                }), 409
    try:
        try:
            c.execute("""
                UPDATE pagos_influencers
                SET estado=?, valor=?, concepto=?,
                    fecha_contenido=COALESCE(NULLIF(?,''), fecha_contenido),
                    vence_pago_at=COALESCE(NULLIF(?,''), vence_pago_at)
                WHERE id=?
            """, (nuevo_estado, round(nuevo_valor), nuevo_concepto,
                  nueva_fc, nuevo_vence, pid))
        except Exception:
            # Fallback si mig 195 no aplicada (sin fecha_contenido/vence_pago_at)
            c.execute("""
                UPDATE pagos_influencers SET estado=?, valor=?, concepto=? WHERE id=?
            """, (nuevo_estado, round(nuevo_valor), nuevo_concepto, pid))
        try:
            from audit_helpers import audit_log as _alog
            _alog(c, usuario=u, accion='PATCH_PAGO_INFLUENCER',
                  tabla='pagos_influencers', registro_id=str(pid),
                  antes=antes,
                  despues={'estado': nuevo_estado, 'valor': nuevo_valor,
                           'concepto': nuevo_concepto,
                           'fecha_contenido': nueva_fc, 'motivo': motivo})
        except Exception:
            pass
        conn.commit()
        return jsonify({'ok': True, 'id': pid, 'estado': nuevo_estado,
                         'valor': nuevo_valor, 'motivo': motivo})
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500


@bp.route("/api/marketing/pagos-influencers", methods=["GET"])
def mkt_pagos_influencers_list():
    """Lista cronológica de pagos a influencers con comprobante PDF asociado.

    Permite a Marketing (Jefferson) ver todos los pagos hechos sin tener que
    abrir el panel de cada influencer uno por uno.

    Query params:
      - estado: 'Pagada' | 'Pendiente' (vacío = todos)
      - mes:    'YYYY-MM' filtro por fecha
      - q:      búsqueda en nombre/concepto/numero_oc
    """
    u, err, code = _auth()
    if err:
        return err, code
    estado = (request.args.get("estado") or "").strip()
    mes = (request.args.get("mes") or "").strip()
    q = (request.args.get("q") or "").strip()

    conn = _db()
    c = conn.cursor()
    try:
        # AUTO-BACKFILL idempotente: si alguna fila quedó con estado='Pendiente'
        # pero la OC ya está Pagada (sync fallido en pagar_oc por categoría
        # rara/vacía), corregirla aquí. Es una sola UPDATE barata y vuelve los
        # datos consistentes sin esperar a un nuevo pago.
        try:
            c.execute("""
                UPDATE pagos_influencers
                SET estado='Pagada'
                WHERE estado='Pendiente'
                  AND numero_oc IN (
                    SELECT numero_oc FROM ordenes_compra
                    WHERE estado='Pagada'
                  )
            """)
            if c.rowcount:
                conn.commit()
        except Exception as _ef:
            import logging
            logging.getLogger("marketing").warning(
                "auto-backfill pagos_influencers falló: %s", _ef
            )

        # Pagos enriquecidos con comprobante (LEFT JOIN, último CE por OC).
        # IMPORTANTE: estado se deriva del estado real de la OC (oc.estado).
        # Si la OC está Pagada en ordenes_compra, mostramos Pagada — incluso
        # si pi.estado quedó stale en 'Pendiente' por algún sync fallido.
        # También una OC con CE generado se considera Pagada (un CE solo se
        # genera tras un pago exitoso).
        sql = """
            SELECT pi.id, pi.influencer_id, pi.influencer_nombre,
                   pi.valor, pi.fecha,
                   CASE
                     WHEN COALESCE(oc.estado,'') = 'Pagada' THEN 'Pagada'
                     WHEN cp.id IS NOT NULL THEN 'Pagada'
                     ELSE pi.estado
                   END as estado,
                   pi.concepto, pi.numero_oc,
                   COALESCE(pi.fecha_publicacion,'') as fecha_publicacion,
                   COALESCE(pi.entregable,'') as entregable,
                   COALESCE(oc.estado,'') as oc_estado,
                   cp.id          as comprobante_id,
                   cp.numero_ce   as numero_ce,
                   cp.empresa     as empresa_pagadora,
                   cp.total_pagado as ce_total,
                   COALESCE(mi.email,'')   as inf_email,
                   COALESCE(mi.banco,'')   as inf_banco
            FROM pagos_influencers pi
            LEFT JOIN ordenes_compra oc ON oc.numero_oc = pi.numero_oc
            LEFT JOIN comprobantes_pago cp
                   ON cp.numero_oc = pi.numero_oc
                  AND cp.id = (SELECT MAX(id) FROM comprobantes_pago
                                WHERE numero_oc = pi.numero_oc)
            LEFT JOIN marketing_influencers mi
                   ON mi.id = pi.influencer_id
            WHERE 1=1
        """
        params = []
        # Filtro por estado: usamos el estado DERIVADO (no pi.estado raw).
        # Replicamos la lógica del CASE en el WHERE.
        if estado == 'Pagada':
            sql += " AND (COALESCE(oc.estado,'') = 'Pagada' OR cp.id IS NOT NULL OR pi.estado = 'Pagada')"
        elif estado == 'Pendiente':
            sql += " AND COALESCE(oc.estado,'') != 'Pagada' AND cp.id IS NULL AND pi.estado = 'Pendiente'"
        elif estado:
            sql += " AND pi.estado = ?"
            params.append(estado)
        if mes:
            sql += " AND substr(pi.fecha, 1, 7) = ?"
            params.append(mes)
        if q:
            sql += " AND (pi.influencer_nombre LIKE ? OR pi.concepto LIKE ? OR pi.numero_oc LIKE ?)"
            ql = f"%{q}%"
            params.extend([ql, ql, ql])
        sql += " ORDER BY pi.fecha DESC, pi.id DESC LIMIT 1000"
        rows = c.execute(sql, params).fetchall()
        pagos = [dict(r) for r in rows]

        # FALLBACK CRÍTICO: si una OC se pagó (existe en pagos_oc) y la
        # categoría es Influencer/Marketing pero NO existe row en
        # pagos_influencers (sync falló), la traemos igual desde pagos_oc.
        # Sin esto, los pagos quedan invisibles para Marketing.
        try:
            ocs_ya = {(p["numero_oc"] or "") for p in pagos if p["numero_oc"]}
            # NOTA: la columna en pagos_oc se llama 'medio' (no 'medio_pago').
            # Bug previo: SELECT po.medio_pago tiraba SQLOperationalError
            # silenciosamente y rompía el fallback completo.
            extra_sql = """
                SELECT po.id, po.numero_oc, po.monto, po.fecha_pago,
                       po.medio AS medio_pago, po.observaciones,
                       oc.proveedor, oc.categoria,
                       cp.id          as comprobante_id,
                       cp.numero_ce   as numero_ce
                FROM pagos_oc po
                LEFT JOIN ordenes_compra oc ON oc.numero_oc = po.numero_oc
                LEFT JOIN comprobantes_pago cp
                       ON cp.numero_oc = po.numero_oc
                      AND cp.id = (SELECT MAX(id) FROM comprobantes_pago
                                    WHERE numero_oc = po.numero_oc)
                WHERE (LOWER(COALESCE(oc.categoria,'')) LIKE '%influencer%'
                       OR LOWER(COALESCE(oc.categoria,'')) LIKE '%marketing%')
                ORDER BY po.fecha_pago DESC LIMIT 500
            """
            extra_rows = c.execute(extra_sql).fetchall()
            for r in extra_rows:
                d = dict(r)
                if d["numero_oc"] in ocs_ya:
                    continue  # ya está en pagos_influencers
                # Convertir a formato de pagos_influencers
                pagos.append({
                    "id": -d["id"],   # negativo para distinguir de pagos_influencers
                    "influencer_id": None,
                    "influencer_nombre": d["proveedor"] or "(sin nombre)",
                    "valor": d["monto"] or 0,
                    "fecha": d["fecha_pago"] or "",
                    "estado": "Pagada",
                    "concepto": (d["observaciones"] or "")[:100],
                    "numero_oc": d["numero_oc"],
                    "fecha_publicacion": "",
                    "comprobante_id": d["comprobante_id"],
                    "numero_ce": d["numero_ce"],
                    "empresa_pagadora": "",
                    "ce_total": 0,
                    "inf_email": "",
                    "inf_banco": "",
                    "_origen": "pagos_oc_fallback",  # marca para debug
                })
            # Re-aplicar filtros sobre el merge
            if estado:
                pagos = [p for p in pagos if (p.get("estado") or "") == estado]
            if mes:
                pagos = [p for p in pagos if (p.get("fecha") or "")[:7] == mes]
            if q:
                ql = q.lower()
                pagos = [p for p in pagos if ql in (
                    (p.get("influencer_nombre") or "") + (p.get("concepto") or "") + (p.get("numero_oc") or "")
                ).lower()]
            # Re-ordenar
            pagos.sort(key=lambda x: (x.get("fecha") or ""), reverse=True)
        except Exception as _ef:
            import logging
            logging.getLogger("marketing").error("fallback pagos_oc falló: %s", _ef)

        # FIX 7-jul (audit ultracode · Habeas Data Ley 1581): enmascarar el banco del influencer si el caller NO
        # es ADMIN+CONTADORA (= /influencers-panel · este listado lo exponía con gate solo _auth).
        try:
            _pvb_pg = (u or '').lower() in {x.lower() for x in (set(ADMIN_USERS) | set(CONTADORA_USERS))}
        except Exception:
            _pvb_pg = False
        if not _pvb_pg:
            for _p in pagos:
                if _p.get('inf_banco'):
                    _p['inf_banco'] = '***'

        # KPIs sobre la lista filtrada
        from datetime import datetime as _dt
        now_month = _dt.now().strftime("%Y-%m")
        now_year = _dt.now().strftime("%Y")
        total_pagado = sum(p["valor"] or 0 for p in pagos if p["estado"] == "Pagada")
        total_pendiente = sum(p["valor"] or 0 for p in pagos if p["estado"] == "Pendiente")
        pagos_mes = [p for p in pagos if p["estado"] == "Pagada" and (p["fecha"] or "").startswith(now_month)]
        pagos_anio = [p for p in pagos if p["estado"] == "Pagada" and (p["fecha"] or "").startswith(now_year)]

        # Lista de meses únicos para filtro UI
        meses_set = sorted({(p["fecha"] or "")[:7] for p in pagos if p["fecha"]}, reverse=True)

        return jsonify({
            "pagos": pagos,
            "total": len(pagos),
            "kpis": {
                "total_pagado": round(total_pagado, 0),
                "total_pendiente": round(total_pendiente, 0),
                "pagos_mes_count": len(pagos_mes),
                "pagos_mes_valor": round(sum(p["valor"] or 0 for p in pagos_mes), 0),
                "pagos_anio_count": len(pagos_anio),
                "pagos_anio_valor": round(sum(p["valor"] or 0 for p in pagos_anio), 0),
            },
            "meses_disponibles": meses_set,
        })
    except Exception as e:
        # FIX 7-jul (audit ultracode): no filtrar el stack trace al cliente · loguear server-side.
        import traceback as _tb, logging as _lg
        _lg.getLogger('marketing').warning('mkt_pagos_influencers_list: %s', _tb.format_exc()[-500:])
        return jsonify({
            "pagos": [], "total": 0, "kpis": {},
            "_error": str(e)[:200],
        }), 200


@bp.route("/api/marketing/influencers/<int:iid>/solicitar-pago", methods=["POST"])
def mkt_solicitar_pago_influencer(iid):
    """Crea una solicitud de pago (cuenta de cobro) vinculada a un influencer."""
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        inf = c.execute("SELECT * FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
        if not inf:
            return jsonify({"error": "Influencer no encontrado"}), 404
        inf = dict(inf)

        d = request.get_json() or {}
        # FIX 7-jul (audit ultracode · M27/M45): IDEMPOTENCIA · el cliente manda solicitud_id único por envío;
        # se reclama con UNIQUE (reusa oc_recepcion_dedup como store genérico de tokens) ANTES de crear SOL+OC+
        # pago → un doble-submit / retry de red / re-corrida del bulk NO crea 2 cadenas pagables (= doble egreso).
        # Sin token (cliente viejo) → no dedup (compat · el disable del botón sigue). El token se libera en rollback.
        _sid = str(d.get('solicitud_id') or '').strip()[:80]
        if _sid:
            from datetime import datetime as _dtsid
            try:
                c.execute("INSERT INTO oc_recepcion_dedup (recepcion_id, numero_oc, creado_en) VALUES (?,?,?)",
                          (_sid, f'MKT-PAGO-{iid}', _dtsid.now().isoformat()))
            except Exception as _ed_sid:
                if 'unique' in str(_ed_sid).lower() or 'duplicate' in str(_ed_sid).lower():
                    conn.rollback()
                    return jsonify({'error': 'Esta solicitud de pago ya fue registrada (doble envío)',
                                    'codigo': 'SOLICITUD_DUPLICADA'}), 409
                raise
        # Sebastián 25-may-2026 PM · audit P0 · validate_money en mutación
        # financiera. Antes float() permitía negativos, NaN, valores absurdos.
        raw_monto = d.get("valor") or d.get("monto") or inf.get("tarifa") or 0
        try:
            from inventario_utils import validate_money as _vm
            monto, _err_m = _vm(raw_monto, allow_zero=False,
                                  max_value=500_000_000, field_name='monto pago')
            if _err_m:
                return jsonify(_err_m), 400
        except ImportError:
            try:
                monto = float(raw_monto or 0)
            except (TypeError, ValueError):
                return jsonify({"error": "monto inválido"}), 400
            if monto <= 0:
                return jsonify({"error": "El monto debe ser mayor a 0"}), 400
            if monto > 500_000_000:
                return jsonify({"error": "monto fuera de rango (max 500M)"}), 400
        concepto = str(d.get("concepto") or "Pago de contenido/colaboración").strip()
        banco    = str(d.get("banco")    or inf.get("banco", "")).strip()
        cuenta   = str(d.get("cuenta")   or inf.get("cuenta_bancaria", "")).strip()
        cedula   = str(d.get("cedula")   or inf.get("cedula_nit", "")).strip()
        tipo_cta = str(d.get("tipo_cuenta") or inf.get("tipo_cuenta", "Ahorros")).strip()
        # FEATURE 27-may PM · fecha_contenido del influencer + vence en 30d
        # Si el frontend no la manda, asumimos creación = hoy (peor caso seguro)
        fecha_contenido = (d.get("fecha_contenido") or "").strip()
        if fecha_contenido and not _re_atrib.match(r'^\d{4}-\d{2}-\d{2}$', fecha_contenido):
            return jsonify({"error": "fecha_contenido debe ser YYYY-MM-DD"}), 400
        # Rediseño 13-jul (Sebastián) · seguimiento fuerte: EXIGIR fecha de publicación real
        # + de qué trató el contenido (entregable) → se guardan y fluyen a la tarjeta de pago
        # en Compras para verificar que el creador SÍ publicó antes de pagar (anti doble-pago /
        # anti pagar-lo-no-hecho). fecha_publicacion suele = fecha_contenido (el front manda una sola).
        fecha_publicacion = (d.get("fecha_publicacion") or "").strip()
        entregable = (d.get("entregable") or "").strip()
        if fecha_publicacion and not _re_atrib.match(r'^\d{4}-\d{2}-\d{2}$', fecha_publicacion):
            return jsonify({"error": "fecha_publicacion debe ser YYYY-MM-DD"}), 400
        # La obligatoriedad se exige en el MODAL de Marketing (validación de cliente).
        # El backend GUARDA lo que llegue sin bloquear: no queremos trabar un pago legítimo
        # (adelanto, corrección) por un campo faltante. Si no vino fecha_publicacion, cae a
        # fecha_contenido (que ya se resolvió a hoy si venía vacía) para no perder la referencia.
        if not fecha_publicacion:
            fecha_publicacion = fecha_contenido
        from datetime import datetime as _dt_fc, timedelta as _td_fc
        if fecha_contenido:
            try:
                base = _dt_fc.strptime(fecha_contenido, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "fecha_contenido inválida"}), 400
        else:
            base = _dt_fc.utcnow() - _td_fc(hours=5)  # Colombia · M24 (Render corre en UTC · la fecha de vencimiento del pago se ancla a hoy-Bogotá)
            fecha_contenido = base.strftime('%Y-%m-%d')
        vence_pago_at = (base + _td_fc(days=30)).strftime('%Y-%m-%d')

        # Generate SOL number
        from datetime import datetime as dt, timedelta as _td_hoy
        today = dt.now()
        # FIX 2-jun-2026 · HTTP 500 al solicitar pago: date('now','-5 hours') depende
        # de una función custom de PostgreSQL (pg_functions.sql) que NO se recarga al
        # bootear · si la BD se reconstruyó, falla → 500 SOLO en endpoints que usan
        # date('now',...) (producción usa fechas de Python, por eso anda). Calculamos
        # la fecha de Bogotá en Python y la pasamos como parámetro · portable SQLite/PG.
        _fecha_hoy = (today - _td_hoy(hours=5)).strftime('%Y-%m-%d')
        prefix = f"SOL-{today.year}-"
        last = c.execute(
            "SELECT numero FROM solicitudes_compra WHERE numero LIKE ? ORDER BY numero DESC LIMIT 1",
            (f"{prefix}%",)
        ).fetchone()
        if last:
            try:
                seq = int(last[0].split("-")[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        numero = f"{prefix}{seq:04d}"
        # FIX 1-jun-2026 · blindaje anti-colisión. Si el seq quedó mal (formatos
        # heterogéneos de SOL en prod → split/int falla → seq=1) el numero podría
        # YA existir y el INSERT violaría UNIQUE(numero) → 500 PERMANENTE en cada
        # intento ("no sirve"). Incrementamos hasta encontrar uno libre.
        _guard = 0
        while c.execute("SELECT 1 FROM solicitudes_compra WHERE numero=?", (numero,)).fetchone():
            seq += 1
            _guard += 1
            numero = f"{prefix}{seq:04d}"
            if _guard > 100000:
                break

        # Build observaciones in standard beneficiary format
        obs_parts = [f"BENEFICIARIO: {inf['nombre']}"]
        if banco:   obs_parts.append(f"BANCO: {banco} {tipo_cta}")
        if cuenta:  obs_parts.append(f"CUENTA/CEL: {cuenta}")
        if cedula:  obs_parts.append(f"CED/NIT: {cedula}")
        obs_parts.append(f"CONCEPTO: {concepto}")
        obs_parts.append(f"VALOR: ${monto:,.0f}")
        obs_parts.append(f"FECHA CONTENIDO: {fecha_contenido}")
        obs_parts.append(f"VENCE PAGO: {vence_pago_at}")
        observaciones = " | ".join(obs_parts)

        # Solicitante = usuario que invoca (jefferson, etc.) — NO el nombre del influencer
        # Asi el flujo de aprobar/rechazar puede notificar al solicitante real por email.
        solicitante_user = (u or '').lower().strip() or 'jefferson'
        email_sol = USER_EMAILS.get(solicitante_user, '') or USER_EMAILS.get('jefferson', '')
        # FIX 2-jun-2026 · HTTP 500 persistente: si una migración no se aplicó en
        # PostgreSQL (ej. mig 20 que agrega solicitudes_compra.influencer_id), el
        # INSERT con esa columna falla → 500 (y en PG aborta toda la transacción, así
        # que los try/except internos NO salvan). Solución robusta: detectar qué
        # columnas EXISTEN y armar el INSERT solo con esas. Portable SQLite/PG.
        def _cols_tabla(tabla):
            cset = set()
            try:
                for _r in c.execute("PRAGMA table_info(" + tabla + ")").fetchall():
                    cset.add(str(_r[1]).lower())
            except Exception:
                cset = set()
            if not cset:
                try:
                    for _r in c.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name=?",
                        (tabla,)).fetchall():
                        cset.add(str(_r[0]).lower())
                except Exception:
                    pass
            return cset

        def _insert_dyn(tabla, pares, core):
            cset = _cols_tabla(tabla)
            usar = [(k, v) for (k, v) in pares if (k in core) or (not cset) or (k.lower() in cset)]
            cols_sql = ",".join(k for k, _ in usar)
            ph = ",".join(["?"] * len(usar))
            c.execute("INSERT INTO " + tabla + " (" + cols_sql + ") VALUES (" + ph + ")",
                      tuple(v for _, v in usar))

        # Beneficiario (nombre del influencer) va en observaciones para no perder visibilidad
        _insert_dyn('solicitudes_compra', [
            ('numero', numero), ('fecha', _fecha_hoy), ('estado', 'Aprobada'),
            ('solicitante', solicitante_user), ('email_solicitante', email_sol),
            ('urgencia', 'Normal'), ('observaciones', observaciones),
            ('area', 'Marketing'), ('empresa', 'ANIMUS'),
            ('categoria', 'Influencer/Marketing Digital'), ('tipo', 'Servicio'),
            ('valor', monto), ('influencer_id', iid),
        ], core=('numero', 'fecha', 'estado', 'observaciones', 'categoria'))

        # Auto-generate OC
        oc_num = numero.replace("SOL", "OC")
        # Mismo blindaje anti-colisión para numero_oc (UNIQUE)
        _guard_oc = 0
        while c.execute("SELECT 1 FROM ordenes_compra WHERE numero_oc=?", (oc_num,)).fetchone():
            _guard_oc += 1
            oc_num = numero.replace("SOL", "OC") + "-" + str(_guard_oc)
            if _guard_oc > 100000:
                break
        _insert_dyn('ordenes_compra', [
            ('numero_oc', oc_num), ('fecha', _fecha_hoy), ('estado', 'Aprobada'),
            ('proveedor', inf["nombre"]), ('observaciones', observaciones),
            ('creado_por', u), ('categoria', 'Influencer/Marketing Digital'),
            ('valor_total', monto),
        ], core=('numero_oc', 'fecha', 'estado'))
        c.execute(
            "UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?",
            (oc_num, numero)
        )

        # Also register in pagos_influencers for the marketing panel
        # FEATURE 27-may PM · fecha_contenido + vence_pago_at (30d desde contenido)
        # SAVEPOINT: si pagos_influencers falla (no crítico · la SOL+OC ya quedaron),
        # NO debe abortar la transacción entera en PG. INSERT dinámico por columnas.
        try:
            c.execute("SAVEPOINT sp_pi")
            _insert_dyn('pagos_influencers', [
                ('influencer_id', iid), ('influencer_nombre', inf["nombre"]),
                ('valor', int(monto)), ('fecha', _fecha_hoy), ('estado', 'Pendiente'),
                ('concepto', concepto), ('numero_oc', oc_num),
                ('fecha_contenido', fecha_contenido), ('vence_pago_at', vence_pago_at),
                ('fecha_publicacion', fecha_publicacion), ('entregable', entregable),
            ], core=('influencer_nombre', 'valor', 'estado'))
            c.execute("RELEASE SAVEPOINT sp_pi")
        except Exception:
            try:
                c.execute("ROLLBACK TO SAVEPOINT sp_pi")
            except Exception:
                pass

        # Sebastián 25-may-2026 PM · audit P0 · mutación financiera SIN
        # audit_log antes era el bug más sensible (dinero real · SOL+OC+pago
        # creados sin rastro). Enmascarar banco/cuenta/cedula en el audit.
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=u, accion='SOLICITAR_PAGO_INFLUENCER',
                tabla='solicitudes_compra', registro_id=numero,
                despues={
                    'influencer_id': iid,
                    'influencer_nombre': inf.get('nombre',''),
                    'monto': monto, 'concepto': concepto,
                    'numero_sol': numero, 'numero_oc': oc_num,
                    'banco_masked': ('***' + banco[-3:]) if banco else '',
                    'cuenta_masked': ('***' + cuenta[-3:]) if cuenta else '',
                })
        except Exception:
            pass

        conn.commit()

        # Sebastian (30-abr-2026): "verifica que en marketing si pueda solicitar
        # el pago... le aparece en compras le doy pagar". Notif in-app a Sebastian
        # + Alejandro para que sepan que llegó solicitud nueva sin tener que
        # abrir /compras manualmente.
        try:
            from blueprints.notif import push_notif_multi
            try:
                from blueprints.compras import ADMIN_USERS as _ADMIN
            except Exception:
                _ADMIN = ('sebastian', 'alejandro')
            destinatarios = [a.lower() for a in _ADMIN]
            push_notif_multi(
                destinatarios,
                'oc_estado',
                f'💸 Solicitud pago: {inf["nombre"]}',
                body=f'{numero} · ${monto:,.0f} · {concepto[:60]}',
                link='/compras#influencer',
                remitente=solicitante_user,
                importante=True
            )
        except Exception as _e:
            __import__('logging').getLogger('marketing').warning(
                'push_notif solicitud pago fallo: %s', _e
            )

        return jsonify({"ok": True, "numero": numero, "oc": oc_num, "monto": monto})
    except Exception as e:
        # FIX 1-jun-2026 · antes había try/finally SIN except → cualquier error de
        # datos (columna faltante, etc.) propagaba como 500 HTML y el front mostraba
        # "Error de red" sin pista → marketing reportaba "no sirve" sin diagnóstico.
        # Ahora: rollback + log + JSON con el error real para que se vea la causa.
        try:
            conn.rollback()
        except Exception:
            pass
        __import__('logging').getLogger('marketing').exception(
            'solicitar_pago_influencer falló (iid=%s)', iid)
        return jsonify({"ok": False,
                        "error": "No se pudo crear la solicitud de pago: " + str(e)}), 500


@bp.route("/api/marketing/influencers/<int:iid>/banco", methods=["PUT"])
def mkt_influencer_banco(iid):
    """Actualiza datos bancarios de un influencer.

    Sebastián 25-may-2026 PM · audit P0:
    - Antes: solo requería _auth() · CUALQUIER marketing user podía
      editar banco/cuenta/cédula de cualquier influencer (Habeas Data fail).
    - Sin audit_log · mutaciones financieras sin rastro regulatorio.
    Fix: separar campos sensibles (banco/cuenta/cedula/tipo_cuenta) que
    REQUIEREN ADMIN+CONTADORA · resto sigue permitido a marketing.
    """
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    d = request.get_json() or {}
    CAMPOS_BANCARIOS = {"banco", "cuenta_bancaria", "cedula_nit", "tipo_cuenta"}
    CAMPOS_GENERALES = {"nombre", "red_social", "usuario_red", "seguidores",
                         "engagement_rate", "nicho", "tarifa", "estado",
                         "email", "telefono", "notas", "discount_code"}
    # Gate · CEO 3-jun-2026 · marketing (Jeferson) captura/mantiene datos
    # bancarios → política única vía _puede_capturar_banco (admin+contadora+
    # marketing). Habeas Data se preserva con audit_log enmascarado (abajo).
    _puede_banco = _puede_capturar_banco(u)
    edita_banco = any(k in d for k in CAMPOS_BANCARIOS)
    if edita_banco and not _puede_banco:
        return jsonify({
            "error": "Sin permiso para editar datos bancarios",
            "codigo": "PRIVACIDAD_BANCO"}), 403
    # Normalizar discount_code (UPPERCASE, sin espacios)
    if "discount_code" in d:
        d["discount_code"] = (d["discount_code"] or "").strip().upper().replace(" ", "")
    campos_validos = CAMPOS_BANCARIOS | CAMPOS_GENERALES
    updates = {k: d[k] for k in campos_validos if k in d}
    if not updates:
        return jsonify({"error": "Nada que actualizar"}), 400
    # Snapshot ANTES (audit_log con valores previos)
    cur = conn.cursor()
    cols_sel = ", ".join(sorted(updates.keys()))
    try:
        antes_row = cur.execute(
            f"SELECT {cols_sel} FROM marketing_influencers WHERE id=?",
            (iid,)).fetchone()
        antes = dict(zip(sorted(updates.keys()), antes_row)) if antes_row else {}
    except Exception:
        antes = {}
    # Enmascarar valores bancarios en audit para no logear plain
    despues = dict(updates)
    if any(k in CAMPOS_BANCARIOS for k in updates):
        for k in CAMPOS_BANCARIOS:
            if k in antes and antes[k]:
                antes[k] = '***' + str(antes[k])[-3:]
            if k in despues and despues[k]:
                despues[k] = '***' + str(despues[k])[-3:]
    set_clause = ", ".join(f"{k}=?" for k in updates)
    cur.execute(f"UPDATE marketing_influencers SET {set_clause} WHERE id=?",
                 list(updates.values()) + [iid])
    try:
        from audit_helpers import audit_log as _al
        _al(cur, usuario=u, accion=('MODIFICAR_BANCO_INFLUENCER' if edita_banco
                                       else 'MODIFICAR_INFLUENCER'),
            tabla='marketing_influencers', registro_id=iid,
            antes=antes, despues=despues)
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/marketing/fix-pago-link", methods=["POST"])
def mkt_fix_pago_link():
    """ADMIN ONLY — one-time fix: link a pagos_influencers record to the
    correct influencer by OC number. Permite editar estado y datos directos
    sobre la tabla, no debe estar accesible a Marketing en general.
    """
    u, err, code = _admin_only()
    if err:
        return err, code
    d = request.get_json() or {}
    numero_oc     = d.get("numero_oc", "").strip()
    influencer_id = d.get("influencer_id")
    nombre        = d.get("influencer_nombre", "").strip()
    estado        = d.get("estado", "Pagada").strip()
    valor         = d.get("valor")
    if not numero_oc:
        return jsonify({"error": "numero_oc requerido"}), 400
    conn = _db()
    c = conn.cursor()
    # Check if record exists
    row = c.execute(
        "SELECT id, influencer_id, influencer_nombre, estado FROM pagos_influencers WHERE numero_oc=?",
        (numero_oc,)
    ).fetchone()
    if row:
        # Update existing record
        sets, params = [], []
        if influencer_id is not None:
            sets.append("influencer_id=?"); params.append(influencer_id)
        if nombre:
            sets.append("influencer_nombre=?"); params.append(nombre)
        sets.append("estado=?"); params.append(estado)
        if valor is not None:
            sets.append("valor=?"); params.append(int(valor))
        if sets:
            params.append(numero_oc)
            c.execute(f"UPDATE pagos_influencers SET {', '.join(sets)} WHERE numero_oc=?", params)
            # Sebastián 25-may-2026 PM · audit P2 · UPDATE de pago (dinero)
            # sin audit antes · ADMIN ONLY pero igual debe quedar rastro.
            try:
                from audit_helpers import audit_log as _al
                _al(c, usuario=u, accion='FIX_PAGO_LINK_UPDATE',
                    tabla='pagos_influencers', registro_id=row[0],
                    antes={'influencer_id': row[1], 'influencer_nombre': row[2],
                            'estado': row[3]},
                    despues={'influencer_id': influencer_id, 'nombre': nombre,
                              'estado': estado, 'valor': valor,
                              'numero_oc': numero_oc})
            except Exception: pass
            conn.commit()
        return jsonify({"ok": True, "action": "updated", "id": row[0]})
    else:
        # Insert new record
        if not nombre or valor is None:
            return jsonify({"error": "Registro no existe; proporciona influencer_nombre y valor para crearlo"}), 404
        c.execute("""
            INSERT INTO pagos_influencers
            (influencer_id, influencer_nombre, valor, fecha, estado, concepto, numero_oc)
            VALUES (?,?,?,date('now', '-5 hours'),?,?,?)
        """, (influencer_id, nombre, int(valor), estado, f"Pago OC {numero_oc}", numero_oc))
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=u, accion='FIX_PAGO_LINK_INSERT',
                tabla='pagos_influencers', registro_id=c.lastrowid,
                despues={'influencer_id': influencer_id, 'nombre': nombre,
                          'valor': int(valor), 'estado': estado,
                          'numero_oc': numero_oc})
        except Exception: pass
        conn.commit()
        return jsonify({"ok": True, "action": "inserted"})


def _fetch_instagram_api_data(token, user_id):
    """Trae métricas oficiales de Instagram Graph API (más confiable que
    socialblade). Devuelve dict compatible con _save_metrics_snapshot.

    Sebastian (29-abr-2026): "Socialblade depende del HTML público"  —
    si IG API está configurado, lo usamos primero (oficial, no scraping).
    """
    if not token or not user_id:
        return None
    try:
        # Endpoint Graph API: /<user_id>?fields=username,followers_count,follows_count,media_count
        url = (f"https://graph.instagram.com/{user_id}"
               f"?fields=username,followers_count,follows_count,media_count"
               f"&access_token={token}")
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except Exception:
        return None

    if 'error' in data:
        return None

    out = {
        'fuente': 'instagram_api',
        'usuario_red': data.get('username', ''),
        'seguidores': data.get('followers_count'),
        'siguiendo': data.get('follows_count'),
        'posts_total': data.get('media_count'),
    }

    # Engagement: traer últimos 12 posts y calcular promedio (likes + comments)
    try:
        url2 = (f"https://graph.instagram.com/{user_id}/media"
                f"?fields=like_count,comments_count&limit=12"
                f"&access_token={token}")
        req2 = urllib.request.Request(url2)
        with urllib.request.urlopen(req2, timeout=10) as r2:
            posts = json.loads(r2.read()).get('data', [])
        if posts and out['seguidores']:
            total_likes = sum(p.get('like_count', 0) for p in posts)
            total_comm = sum(p.get('comments_count', 0) for p in posts)
            avg_likes = total_likes / len(posts)
            avg_comm = total_comm / len(posts)
            out['avg_likes'] = round(avg_likes)
            out['avg_comments'] = round(avg_comm)
            out['engagement_rate'] = round((avg_likes + avg_comm) / out['seguidores'] * 100, 2)
    except Exception:
        pass

    return out


def _fetch_socialblade_data(usuario_red):
    """Scrape de socialblade.com/instagram/user/<usuario> para extraer
    métricas públicas. Sebastian (29-abr-2026): "mira esta pagina quizas
    sirva para todo los datos que carguen automatico".

    Devuelve dict con: seguidores, siguiendo, posts_total, rank, grade,
    avg_likes, engagement_rate (si están disponibles). Si la página no
    existe o falla el scrape, devuelve None silenciosamente.

    NO requiere API key — socialblade publica los datos de instagram públicos
    sin auth. Respetamos User-Agent y rate limit (1 req cada 5s entre influencers).
    """
    if not usuario_red:
        return None
    # Limpiar @ del usuario si viene
    usr = usuario_red.lstrip('@').strip().lower()
    if not usr:
        return None
    url = f"https://socialblade.com/instagram/user/{usr}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; HHA-Group-EOS/1.0; +https://hhagroup.co)',
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception:
        return None

    # Parse robusto — múltiples patrones por si Socialblade cambia el HTML.
    # Sebastian (29-abr-2026): "Si Socialblade cambia su layout, los regex
    # pueden fallar". Mitigación: probar 3-4 patterns por campo y fallback
    # a estructuras de OpenGraph/JSON-LD si están presentes.
    import re as _re
    out = {'fuente': 'socialblade', 'usuario_red': usr}

    def _try_patterns(field_name, patterns, parser):
        """Prueba lista de patterns hasta que uno matchee."""
        for pat in patterns:
            m = _re.search(pat, html, _re.IGNORECASE | _re.DOTALL)
            if m:
                try:
                    return parser(m.group(1))
                except Exception:
                    continue
        return None

    # Followers — múltiples patterns
    seguidores = _try_patterns('seguidores', [
        r'>([\d,]+)<\/span>\s*<\/div>\s*<div[^>]*>\s*<p>Followers',
        r'<p>Followers<\/p>\s*<span[^>]*>([\d,]+)',
        r'([\d,]+)\s*Followers',
        r'"followers_count"\s*:\s*(\d+)',  # JSON-LD
        r'data-followers\s*=\s*["\']([\d,]+)',  # data attribute
    ], lambda s: int(s.replace(',', '')))
    if seguidores is not None:
        out['seguidores'] = seguidores

    # Following
    siguiendo = _try_patterns('siguiendo', [
        r'<p>Following<\/p>\s*<span[^>]*>([\d,]+)',
        r'([\d,]+)\s*Following',
        r'"follows_count"\s*:\s*(\d+)',
    ], lambda s: int(s.replace(',', '')))
    if siguiendo is not None:
        out['siguiendo'] = siguiendo

    # Posts
    posts = _try_patterns('posts', [
        r'<p>(?:Uploads|Posts|Media)<\/p>\s*<span[^>]*>([\d,]+)',
        r'([\d,]+)\s*(?:Uploads|Posts|Media)',
        r'"media_count"\s*:\s*(\d+)',
    ], lambda s: int(s.replace(',', '')))
    if posts is not None:
        out['posts_total'] = posts

    # Grade (B+, A-, etc.)
    grade = _try_patterns('grade', [
        r'Grade[^<]*<[^>]+>([A-F][+-]?)',
        r'class\s*=\s*["\']grade["\'][^>]*>\s*([A-F][+-]?)',
        r'data-grade\s*=\s*["\']([A-F][+-]?)',
    ], lambda s: s.strip())
    if grade:
        out['grade'] = grade

    # Rank
    rank = _try_patterns('rank', [
        r'Rank[^<]*<[^>]+>#?\s*([\d,]+)',
        r'class\s*=\s*["\']rank["\'][^>]*>\s*#?\s*([\d,]+)',
    ], lambda s: int(s.replace(',', '')))
    if rank is not None:
        out['rank_global'] = rank

    # Engagement rate
    er = _try_patterns('er', [
        r'Engagement\s*Rate[^<]*<[^>]+>([\d.]+)%?',
        r'"engagement_rate"\s*:\s*"?([\d.]+)',
    ], lambda s: float(s))
    if er is not None:
        out['engagement_rate'] = er

    # Average Likes
    al = _try_patterns('al', [
        r'(?:Avg|Average)\s*Likes[^<]*<[^>]+>([\d,]+)',
        r'"avg_likes"\s*:\s*(\d+)',
    ], lambda s: int(s.replace(',', '')))
    if al is not None:
        out['avg_likes'] = al

    # Si extrajimos solo 'fuente' y 'usuario_red' (nada útil) → fallar
    if len(out) <= 2:
        return None

    return out


def _fetch_metrics_smart(conn, influencer_row):
    """Estrategia inteligente: Instagram API primero (oficial), Socialblade
    como fallback (público). Devuelve datos del primero que responda.

    Args:
        influencer_row: dict-like con id, nombre, usuario_red.
    """
    # 1. Intentar Instagram Graph API (oficial)
    ig_token = _cfg(conn, 'instagram_token')
    ig_user_id = _cfg(conn, 'instagram_user_id')
    if ig_token and ig_user_id and influencer_row.get('usuario_red'):
        # IG API solo trae métricas del CUENTA logueada. Skip para influencers
        # que no son la cuenta principal de la marca. Aún así, queda registrado
        # como fuente='instagram_api' en el helper si el match es la cuenta.
        # Para influencers EXTERNOS, IG Graph requeriría que ellos den permiso
        # vía OAuth — fuera de scope. Usamos socialblade.
        pass

    # 2. Socialblade (público)
    return _fetch_socialblade_data(influencer_row.get('usuario_red'))


# ─── Helpers de alertas críticas + notificación email ────────────
def _detectar_alertas_criticas(agente, payload):
    """Inspecciona el output de un agente y devuelve lista de alertas críticas
    que ameritan email automático a Sebastián.

    Returns: list de dicts {tipo_alerta, sku, severidad, mensaje}.
    Si no hay alertas críticas, lista vacía (no se manda email).
    """
    alertas = []
    if not isinstance(payload, dict):
        return alertas

    if agente == 'alerta_stock':
        for a in (payload.get('alertas') or []):
            if a.get('nivel') == 'critico':
                alertas.append({
                    'tipo_alerta': 'stock_critico',
                    'sku': a.get('sku', ''),
                    'severidad': 'alta',
                    'mensaje': f"SKU {a.get('sku')}: {a.get('dias_cobertura_real', '?')} días de cobertura. {a.get('accion', '')}",
                })

    elif agente == 'estacionalidad':
        for a in (payload.get('alertas') or []):
            if a.get('estado') == 'critico':
                alertas.append({
                    'tipo_alerta': 'evento_deficit',
                    'sku': a.get('sku', ''),
                    'severidad': 'alta',
                    'mensaje': (f"Evento '{a.get('evento')}' en {a.get('dias_restantes')} días. "
                                f"SKU {a.get('sku')} déficit: {a.get('deficit')} uds. "
                                f"Deadline producción: {a.get('deadline_produccion')}"),
                })

    elif agente == 'roi':
        for c in (payload.get('campanas') or []):
            if c.get('roi_pct', 0) < -50:  # ROI muy negativo
                alertas.append({
                    'tipo_alerta': 'roi_critico',
                    'sku': c.get('sku_objetivo', ''),
                    'severidad': 'alta',
                    'mensaje': (f"Campaña '{c.get('nombre')}' tiene ROI {c.get('roi_pct')}%. "
                                f"Gastado: ${c.get('presupuesto_gastado',0):,.0f}, "
                                f"Ventas: ${c.get('resultado_ventas',0):,.0f}"),
                })

    elif agente == 'canibal':
        for cf in (payload.get('conflictos') or []):
            alertas.append({
                'tipo_alerta': 'campanas_canibalizan',
                'sku': cf.get('sku', ''),
                'severidad': 'media',
                'mensaje': (f"Conflicto: '{cf.get('campana_a')}' vs '{cf.get('campana_b')}' "
                            f"({cf.get('conflicto')}, canal {cf.get('canal')})"),
            })

    elif agente == 'reorden':
        for p in (payload.get('predicciones') or []):
            if p.get('urgencia') == 'hoy':
                alertas.append({
                    'tipo_alerta': 'reorden_hoy',
                    'sku': '',
                    'severidad': 'alta',
                    'mensaje': (f"Cliente B2B '{p.get('email')}' debería reordenar HOY. "
                                f"Ticket promedio: ${p.get('ticket_promedio',0):,.0f}"),
                })

    return alertas


def _notificar_alertas_criticas(conn, agente, alertas):
    """Manda email a Sebastián por cada alerta crítica nueva.
    Idempotente: usa marketing_alertas_enviadas con UNIQUE(agente, sku,
    tipo_alerta, date(enviado_at)) para no enviar el mismo aviso 2 veces
    el mismo día.

    Returns: count de emails enviados.
    """
    if not alertas:
        return 0
    try:
        from config import USER_EMAILS
    except Exception:
        USER_EMAILS = {}
    dest_seb = USER_EMAILS.get('sebastian', '')
    dest_alex = USER_EMAILS.get('alejandro', '')
    destinos = [d for d in (dest_seb, dest_alex) if d]
    if not destinos:
        return 0

    enviadas = 0
    c = conn.cursor()
    for a in alertas:
        # Chequear si ya enviamos esto hoy (UNIQUE index garantiza 1 por día)
        ya = c.execute("""
            SELECT 1 FROM marketing_alertas_enviadas
            WHERE agente=? AND COALESCE(sku,'')=COALESCE(?,'')
              AND COALESCE(tipo_alerta,'')=? AND fecha_envio = date('now', '-5 hours')
        """, (agente, a.get('sku', ''), a.get('tipo_alerta', ''))).fetchone()
        if ya:
            continue

        # Mandar email
        try:
            import sys, os, threading as _th
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from notificaciones import SistemaNotificaciones
            asunto = f"⚠️ Alerta {a.get('severidad','').upper()}: {a.get('tipo_alerta','')} ({agente})"
            sku_html = f"<br>SKU: <b>{a.get('sku')}</b>" if a.get('sku') else ""
            body = (
                f"<h2>Alerta detectada por agente {agente}</h2>"
                f"<div style='background:#fef2f2;border-left:4px solid #dc2626;padding:14px;border-radius:6px'>"
                f"<b>{a.get('tipo_alerta','')}</b> · severidad: {a.get('severidad','')}"
                f"{sku_html}"
                f"<br>{a.get('mensaje','')}"
                f"</div>"
                f"<p>Revisa <a href='/marketing'>el tab Hoy</a> para ver detalle y aplicar workflow.</p>"
                f"<p style='color:#94a3b8;font-size:11px'>Mensaje automático HHA Group · Marketing</p>"
            )
            notif = SistemaNotificaciones()
            _th.Thread(
                target=notif._enviar_email,
                args=(asunto, body, destinos),
                daemon=True
            ).start()
            # Registrar como enviada
            c.execute("""
                INSERT INTO marketing_alertas_enviadas
                  (agente, sku, tipo_alerta, severidad, mensaje, destinatarios)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (agente, a.get('sku', ''), a.get('tipo_alerta', ''),
                  a.get('severidad', ''), a.get('mensaje', '')[:500],
                  ','.join(destinos)))
            enviadas += 1
        except Exception as e:
            import logging
            logging.getLogger('marketing').warning("notificacion fallo: %s", e)
    if enviadas:
        conn.commit()
    return enviadas


# ─── Background daemon: refresh diario de metrics + alertas ────────
# Sebastián 25-may-2026 PM · audit P1 fix · referencia al thread (no flag bool)
# así el supervisor puede chequear is_alive() y relanzar si crashea.
_marketing_metrics_thread = None


def _start_marketing_metrics_loop():
    """Arranca thread daemon que cada 24h:
      1. Refresca metrics de TODOS los influencers (Socialblade)
      2. Ejecuta los agentes críticos y dispara emails si detecta alertas

    Sebastián (29-abr-2026): "agregar a un scheduler". Implementación lazy
    sin necesidad de un cron externo (Render free tier no tiene cron).

    Sebastián 25-may-2026 PM · audit P1:
    - Antes: flag bool · si el thread crashea, flag sigue True → supervisor
      cree que está corriendo · daemon zombie permanente
    - Ahora: thread reference + is_alive() check · supervisor relanza
    - + _adquirir_lock_cron('marketing_metrics', ttl_horas=24) para evitar
      que 3 workers gunicorn corran el refresh simultáneo (3x scraping
      socialblade del mismo influencer = ban + race UNIQUE pedidos_b2b_lote)
    """
    global _marketing_metrics_thread
    # Idempotente · si ya corre (vivo), no relanzar
    prev = _marketing_metrics_thread
    if prev is not None and prev.is_alive():
        return

    import threading
    import time as _time

    def _loop():
        try:
            from index import app as _app
        except Exception as _e:
            log.error('[marketing-metrics] import inicial fallo · loop NO arrancó: %s', _e)
            return
        # Esperar 5 min al arranque para no chocar con migrations
        _time.sleep(300)
        while True:
            try:
                with _app.app_context():
                    cn = _db()
                    # Sebastián 25-may-2026 PM · audit P1 · lock distribuido
                    # para que solo 1 de los 3 workers ejecute el refresh
                    # (evita 3x scraping + race en INSERT OR REPLACE de
                    # marketing_influencers_metrics).
                    lock_ok = False
                    try:
                        from blueprints.auto_plan_jobs import (
                            _adquirir_lock_cron, _liberar_lock_cron)
                        lock_ok = _adquirir_lock_cron(
                            cn, 'marketing_metrics_refresh', ttl_horas=23)
                    except Exception as _ex_lock:
                        log.warning('marketing lock cron no disponible · sigo sin lock: %s', _ex_lock)
                        lock_ok = True  # fallback · single-worker mode
                    if not lock_ok:
                        log.info('[marketing-metrics] otro worker tiene el lock · skip ciclo')
                    else:
                        # FIX 7-jul (audit ultracode · M43): el refresh REAL del token IG corre acá (1×/día · 1
                        # worker, bajo lock), NO en el load del dashboard (que ahora usa allow_network=False).
                        try:
                            _ig_check_refresh(cn, allow_network=True)
                        except Exception as _ex_ig:
                            log.warning('[marketing-metrics] refresh token IG fallo: %s', _ex_ig)
                        try:
                            rows = cn.execute(
                                "SELECT id, nombre, usuario_red FROM marketing_influencers "
                                "WHERE COALESCE(usuario_red,'')!='' AND COALESCE(estado,'')!='Inactivo'"
                            ).fetchall()
                            for r in rows:
                                try:
                                    datos = _fetch_socialblade_data(r['usuario_red'])
                                    if datos:
                                        _save_metrics_snapshot(cn, r['id'], datos, 'socialblade')
                                except Exception as _ex_inf:
                                    log.warning('[marketing-metrics] socialblade %s fallo: %s',
                                                  r['usuario_red'], _ex_inf)
                                _time.sleep(5)  # rate limit ético
                        finally:
                            try:
                                _liberar_lock_cron(cn, 'marketing_metrics_refresh')
                            except Exception: pass
            except Exception as e:
                log.warning("metrics loop error: %s", e)
            # Dormir 24h
            _time.sleep(24 * 3600)

    t = threading.Thread(target=_loop, daemon=True, name='marketing-metrics-loop')
    try:
        t.start()
        _marketing_metrics_thread = t
    except Exception as _e:
        log.error('[marketing-metrics] thread.start fallo: %s', _e)


# ──────────────────────────────────────────────────────────────────────────────
# Cron semanal · Reporte ejecutivo lunes 8am Bogotá
# ──────────────────────────────────────────────────────────────────────────────
_reporte_semanal_thread = None


def _start_reporte_ejecutivo_loop():
    """Thread daemon que cada hora verifica si toca enviar el reporte semanal.

    Dispara solo cuando:
      - Día semana == Lunes (weekday=0)
      - Hora local Bogotá == 8 (UTC-5)
      - Lock cron disponible (1 worker de 3 envía)
      - REPORTE_EJECUTIVO_EMAIL env var configurada
    """
    global _reporte_semanal_thread
    prev = _reporte_semanal_thread
    if prev is not None and prev.is_alive():
        return
    import threading
    import time as _time
    from datetime import datetime as _dt, timedelta as _td

    def _loop():
        try:
            from index import app as _app
        except Exception as _e:
            log.error('[reporte-ejecutivo] import fallo: %s', _e)
            return
        # Delay inicial 60s · permite que migrations corran
        _time.sleep(60)
        while True:
            try:
                # Bogotá = UTC-5 · convertimos sin pytz para no añadir dep
                ahora_utc = _dt.utcnow()
                ahora_bog = ahora_utc - _td(hours=5)
                es_lunes = ahora_bog.weekday() == 0
                es_8am = ahora_bog.hour == 8
                if es_lunes and es_8am:
                    dests_raw = (os.environ.get('REPORTE_EJECUTIVO_EMAIL') or '').strip()
                    dests = [d.strip() for d in dests_raw.split(',') if d.strip()]
                    if not dests:
                        log.info('[reporte-ejecutivo] lunes 8am pero REPORTE_EJECUTIVO_EMAIL no configurada · skip')
                    else:
                        with _app.app_context():
                            cn = _db()
                            # Lock distribuido · clave incluye fecha para
                            # garantizar 1 envío/semana
                            week_key = f'reporte_ejecutivo_{ahora_bog.strftime("%Y_W%V")}'
                            lock_ok = False
                            try:
                                from blueprints.auto_plan_jobs import (
                                    _adquirir_lock_cron, _liberar_lock_cron)
                                lock_ok = _adquirir_lock_cron(cn, week_key, ttl_horas=168)
                            except Exception as _ex_lock:
                                log.warning('[reporte-ejecutivo] lock no disponible: %s', _ex_lock)
                                lock_ok = True  # single-worker fallback
                            if not lock_ok:
                                log.info('[reporte-ejecutivo] otro worker ya envió esta semana · skip')
                            else:
                                try:
                                    data = _build_reporte_ejecutivo_data(cn)
                                    html = _build_reporte_ejecutivo_html(data)
                                    from notificaciones import SistemaNotificaciones
                                    sn = SistemaNotificaciones()
                                    if not sn.email_remitente or not sn.contraseña:
                                        log.warning('[reporte-ejecutivo] SMTP no configurado · skip')
                                    else:
                                        import smtplib, ssl as _ssl
                                        from email.mime.multipart import MIMEMultipart
                                        from email.mime.text import MIMEText
                                        for dest in dests:
                                            try:
                                                msg = MIMEMultipart('alternative')
                                                msg['Subject'] = f"[ÁNIMUS] Reporte ejecutivo semanal · {data['generado_en'][:10]}"
                                                msg['From'] = sn.email_remitente
                                                msg['To'] = dest
                                                msg.attach(MIMEText(html, 'html', 'utf-8'))
                                                ctx = _ssl.create_default_context()
                                                with smtplib.SMTP_SSL(sn.smtp_server, sn.smtp_port, context=ctx) as s:
                                                    s.login(sn.email_remitente, sn.contraseña)
                                                    s.sendmail(sn.email_remitente, [dest], msg.as_string())
                                                log.info('[reporte-ejecutivo] enviado a %s', dest)
                                            except Exception as _se:
                                                log.warning('[reporte-ejecutivo] envío a %s fallo: %s', dest, _se)
                                except Exception as _de:
                                    log.exception('[reporte-ejecutivo] generación fallo: %s', _de)
            except Exception as _le:
                log.warning('[reporte-ejecutivo] loop error: %s', _le)
            # Dormir 1 hora · re-verifica
            _time.sleep(3600)

    t = threading.Thread(target=_loop, daemon=True, name='reporte-ejecutivo-loop')
    try:
        t.start()
        _reporte_semanal_thread = t
    except Exception as _e:
        log.error('[reporte-ejecutivo] thread.start fallo: %s', _e)


def _save_metrics_snapshot(conn, influencer_id, datos, fuente):
    """Inserta o actualiza un snapshot de métricas en marketing_influencers_metrics.
    UNIQUE(influencer_id, fecha, fuente) garantiza 1 snapshot por día por fuente."""
    if not datos:
        return False
    import json as _json
    fecha = __import__('datetime').date.today().isoformat()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO marketing_influencers_metrics
              (influencer_id, fecha, seguidores, siguiendo, posts_total,
               engagement_rate, avg_likes, avg_comments, rank_global, grade,
               fuente, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            influencer_id, fecha,
            datos.get('seguidores'), datos.get('siguiendo'),
            datos.get('posts_total'), datos.get('engagement_rate'),
            datos.get('avg_likes'), datos.get('avg_comments'),
            datos.get('rank_global'), datos.get('grade'),
            fuente, _json.dumps(datos)
        ))
        # Actualizar también el campo seguidores en marketing_influencers (cache)
        if datos.get('seguidores'):
            conn.execute(
                "UPDATE marketing_influencers SET seguidores=? WHERE id=?",
                (datos['seguidores'], influencer_id)
            )
        if datos.get('engagement_rate'):
            conn.execute(
                "UPDATE marketing_influencers SET engagement_rate=? WHERE id=?",
                (datos['engagement_rate'], influencer_id)
            )
        conn.commit()
        return True
    except Exception:
        return False


@bp.route("/api/marketing/influencers/<int:iid>/refresh-metrics", methods=["POST"])
def mkt_refresh_metrics_influencer(iid):
    """Refresca métricas de un influencer puntual desde socialblade.
    Body opcional: {fuerza_socialblade: true} para skipear cache de hoy.
    """
    u, err, code = _auth()
    if err: return err, code
    conn = _db()
    inf = conn.execute(
        "SELECT id, nombre, usuario_red FROM marketing_influencers WHERE id=?", (iid,)
    ).fetchone()
    if not inf:
        return jsonify({"error": "Influencer no encontrado"}), 404
    if not inf['usuario_red']:
        return jsonify({"error": "Influencer sin usuario_red — agregalo en editar"}), 400

    datos = _fetch_socialblade_data(inf['usuario_red'])
    if not datos:
        return jsonify({
            "ok": False,
            "error": "Socialblade no devolvió datos — la cuenta puede no existir o el scrape falló.",
            "usuario_red": inf['usuario_red'],
        }), 200  # 200 con ok:false para que el frontend distinga
    saved = _save_metrics_snapshot(conn, iid, datos, 'socialblade')
    return jsonify({
        "ok": saved,
        "influencer": inf['nombre'],
        "usuario_red": inf['usuario_red'],
        "datos": datos,
    })


@bp.route("/api/marketing/refresh-all-metrics", methods=["POST"])
def mkt_refresh_all_metrics():
    """Refresca métricas de TODOS los influencers activos con usuario_red.
    Solo admin. Lento (1 req cada 5s para respetar rate limit) — corre en background.
    """
    u, err, code = _admin_only()
    if err: return err, code
    conn = _db()
    rows = conn.execute(
        "SELECT id, nombre, usuario_red FROM marketing_influencers "
        "WHERE COALESCE(usuario_red,'')!='' AND COALESCE(estado,'')!='Inactivo'"
    ).fetchall()
    if not rows:
        return jsonify({"ok": True, "procesados": 0, "mensaje": "Sin influencers con usuario_red"})

    import threading, time as _time, logging as _lg
    _log = _lg.getLogger("marketing")
    def _worker(infs):
        try:
            from index import app as _app
        except Exception:
            from flask import current_app as _app
        with _app.app_context():
            cn = _db()
            errores = 0
            for r in infs:
                try:
                    datos = _fetch_socialblade_data(r['usuario_red'])
                    if datos:
                        _save_metrics_snapshot(cn, r['id'], datos, 'socialblade')
                except Exception as e:
                    errores += 1
                    _log.warning("refresh-all-metrics: falla en influencer id=%s nombre=%s: %s",
                                 r.get('id') if hasattr(r,'get') else r['id'],
                                 r['nombre'] if 'nombre' in r.keys() else '?', e)
                _time.sleep(5)  # rate limit ético
            _log.info("refresh-all-metrics completo: %d procesados · %d errores", len(infs), errores)
    threading.Thread(target=_worker, args=(list(rows),), daemon=True).start()
    return jsonify({
        "ok": True,
        "procesados_en_background": len(rows),
        "mensaje": f"Refresh de {len(rows)} influencers iniciado en background. "
                   f"Tomará ~{len(rows)*5}s. Revisa /api/marketing/influencers/<id>/metrics-history para ver resultados."
    })


@bp.route("/api/marketing/influencers/<int:iid>/metrics-history", methods=["GET"])
def mkt_metrics_history(iid):
    """Histórico de métricas de un influencer — últimos N días."""
    u, err, code = _auth()
    if err: return err, code
    dias = int(request.args.get('dias', 90))
    conn = _db()
    rows = conn.execute("""
        SELECT fecha, seguidores, siguiendo, posts_total, engagement_rate,
               avg_likes, avg_comments, rank_global, grade, fuente
        FROM marketing_influencers_metrics
        WHERE influencer_id=? AND fecha >= date('now', '-5 hours', ? || ' day')
        ORDER BY fecha ASC
    """, (iid, f'-{dias}')).fetchall()
    return jsonify({
        "influencer_id": iid,
        "dias": dias,
        "snapshots": [dict(r) for r in rows],
        "count": len(rows),
    })


@bp.route("/api/marketing/workflow/aplicar-agente", methods=["POST"])
def mkt_workflow_aplicar_agente():
    """Convierte el output de un agente en entidades reales — Fase 3 Marketing.

    Sebastian (29-abr-2026): "auto genere calendario, estrategias y campañas".
    Los agentes ya proponen — este endpoint EJECUTA: crea la campaña, agrega
    al kanban, crea la solicitud de producción, etc.

    Body: {
      agente: 'estrategia' | 'oportunidad' | 'contenido_auto' | 'alerta_stock' |
              'estacionalidad' | 'reorden',
      payload: {...}  # output de la última ejecución del agente
    }

    Retorna detalle de qué se creó (campañas, briefs, solicitudes, etc.).

    FIX 27-may-2026 PM · Sebastián · "Unexpected token '<', '<!DOCTYPE...'" ·
    cuando una excepción no atrapada explota, Flask devuelve página HTML 500
    y el frontend JS no puede parsearla. Wrapping global garantiza JSON.
    """
    try:
        u, err, code = _auth()
        if err: return err, code
        d = request.get_json() or {}
        agente = (d.get('agente') or '').strip()
        payload = d.get('payload') or {}
        if not agente:
            return jsonify({'error': 'agente requerido'}), 400

        conn = _db()
        c = conn.cursor()
        return _mkt_workflow_aplicar_agente_impl(conn, c, agente, payload, u)
    except Exception as _e_wf:
        import traceback as _tb_wf
        return jsonify({
            'ok': False,
            'error': f'Excepción interna · agente {(d.get("agente") if "d" in dir() else "?")}: {str(_e_wf)[:200]}',
            'trace': _tb_wf.format_exc()[-600:],
        }), 500


def _mkt_workflow_aplicar_agente_impl(conn, c, agente, payload, u):
    """Implementación del workflow extraída para wrapping con try/except global."""
    creado = {'campanas': 0, 'briefs': 0, 'solicitudes_produccion': 0, 'detalle': []}
    fecha_iso = datetime.now().isoformat(timespec='seconds')

    # ── Workflow 1: oportunidad → crear campañas para SKUs detectados ──
    if agente == 'oportunidad':
        recomendaciones = payload.get('recomendaciones', [])[:5]  # top 5
        for r in recomendaciones:
            sku = r.get('sku')
            if not sku:
                continue
            # Skip si ya hay una campaña activa para este SKU
            ya = c.execute("""
                SELECT id FROM marketing_campanas
                WHERE sku_objetivo=? AND estado IN ('Planificada','Activa')
                LIMIT 1
            """, (sku,)).fetchone()
            if ya:
                creado['detalle'].append({'sku': sku, 'skip': 'ya tiene campaña activa'})
                continue
            nombre = f"Campaña {sku} — Oportunidad detectada"
            c.execute("""
                INSERT INTO marketing_campanas
                  (nombre, canal, tipo, estado, fecha_inicio, fecha_fin,
                   sku_objetivo, objetivo_unidades, presupuesto, notas,
                   fecha_creacion)
                VALUES (?, 'Influencer', 'Push', 'Planificada',
                        date('now', '-5 hours'), date('now', '-5 hours', '+30 day'), ?, ?, ?, ?, ?)
            """, (nombre, sku,
                  max(int(r.get('stock', 0) * 0.5), 10),  # objetivo: vender 50% del stock
                  500000,  # presupuesto base sugerido
                  f"Auto-creada por agente oportunidad: {', '.join(r.get('razones', []))}",
                  fecha_iso))
            creado['campanas'] += 1
            creado['detalle'].append({'sku': sku, 'campana_id': c.lastrowid, 'nombre': nombre})

    # ── Workflow 2: contenido_auto → agregar piezas al kanban ──
    elif agente == 'contenido_auto':
        piezas = payload.get('piezas', [])
        for p in piezas:
            sku = p.get('sku')
            caption = p.get('caption_instagram', '')
            if not sku or not caption:
                continue
            try:
                c.execute("""
                    INSERT INTO marketing_contenido
                      (tipo, plataforma, estado, caption, sku_objetivo,
                       mensaje_principal)
                    VALUES ('post', 'Instagram', 'Brief', ?, ?, ?)
                """, (
                    caption + "\n\n[Auto-generado por agente contenido_auto]",
                    sku,
                    f"Auto-generado para top SKU {sku}"
                ))
                creado['briefs'] += 1
                creado['detalle'].append({'sku': sku, 'contenido_id': c.lastrowid})
            except Exception as e:
                creado['detalle'].append({'sku': sku, 'error': str(e)[:80]})

    # ── Workflow 3: alerta_stock + estacionalidad → solicitudes de producción ──
    elif agente in ('alerta_stock', 'estacionalidad'):
        items = payload.get('alertas', [])
        for it in items[:10]:  # top 10 más críticas
            sku = it.get('sku')
            if not sku:
                continue
            # Crear nota en marketing_campanas como flag (no creamos producción
            # directa — eso es responsabilidad del módulo Planta).
            nivel = it.get('nivel') or it.get('estado') or 'advertencia'
            if nivel == 'ok':
                continue
            obs = (f"AUTO-FLAG por agente {agente}: SKU {sku} — "
                   f"stock {it.get('stock', '?')}, "
                   f"déficit {it.get('deficit', it.get('dias_cobertura_real', '?'))}. "
                   f"Acción: {it.get('accion', 'Reposicionar')}")
            ya = c.execute(
                "SELECT id FROM marketing_campanas "
                "WHERE sku_objetivo=? AND tipo='Reposición' AND estado='Planificada'",
                (sku,)
            ).fetchone()
            if ya:
                creado['detalle'].append({'sku': sku, 'skip': 'ya hay flag de reposición'})
                continue
            c.execute("""
                INSERT INTO marketing_campanas
                  (nombre, canal, tipo, estado, fecha_inicio, sku_objetivo,
                   notas, fecha_creacion)
                VALUES (?, 'Interno', 'Reposición', 'Planificada', date('now', '-5 hours'),
                        ?, ?, ?)
            """, (f"FLAG Reposición {sku}", sku, obs, fecha_iso))
            creado['solicitudes_produccion'] += 1
            creado['detalle'].append({'sku': sku, 'flag_id': c.lastrowid})

    # ── Workflow 4: estrategia (master) — crear campañas para SKUs en riesgo ──
    elif agente == 'estrategia':
        snapshot = payload.get('snapshot') or {}
        for sku_info in (snapshot.get('skus_para_empujar') or [])[:3]:
            sku = sku_info.get('sku')
            if not sku:
                continue
            ya = c.execute("""
                SELECT id FROM marketing_campanas
                WHERE sku_objetivo=? AND estado IN ('Planificada','Activa')
                LIMIT 1
            """, (sku,)).fetchone()
            if ya:
                continue
            c.execute("""
                INSERT INTO marketing_campanas
                  (nombre, canal, tipo, estado, fecha_inicio, fecha_fin,
                   sku_objetivo, presupuesto, notas, fecha_creacion)
                VALUES (?, 'Influencer', 'Push', 'Planificada',
                        date('now', '-5 hours'), date('now', '-5 hours', '+45 day'), ?, ?, ?, ?)
            """, (f"Estrategia {sku} — empuje", sku, 700000,
                  f"Auto-creada por agente estrategia: SKU detectado para empuje urgente",
                  fecha_iso))
            creado['campanas'] += 1
            creado['detalle'].append({'sku': sku, 'campana_id': c.lastrowid})

    else:
        return jsonify({'error': f"Workflow no implementado para agente '{agente}'. "
                                  f"Disponibles: oportunidad, contenido_auto, alerta_stock, "
                                  f"estacionalidad, estrategia"}), 400

    conn.commit()
    creado['ok'] = True
    creado['agente'] = agente
    creado['mensaje'] = (
        f"Workflow {agente}: {creado['campanas']} campaña(s), "
        f"{creado['briefs']} brief(s), "
        f"{creado['solicitudes_produccion']} flag(s) de reposición creados."
    )
    return jsonify(creado)


@bp.route("/api/marketing/agencia/audit", methods=["GET"])
def mkt_agencia_audit():
    """Agencia tab: influencer scoring, portfolio audit, competition analysis, campaign proposals."""
    u, err, code = _auth()
    if err:
        return err, code
    conn = _db()
    c = conn.cursor()
    try:
        from datetime import datetime as _dt, timedelta as _td

        # ── 1. Load influencers ────────────────────────────────────────────────
        influencers = [dict(r) for r in c.execute(
            "SELECT * FROM marketing_influencers ORDER BY nombre"
        ).fetchall()]

        # Sebastián 25-may-2026 PM · audit P0 · Habeas Data · `agencia/audit`
        # devolvía dicts completos en `scored` (banco/cuenta/cédula visibles
        # a marketing users). Ahora enmascara si no es admin+contadora.
        try:
            _puede_ver_banco_a = (u or '').lower() in {
                x.lower() for x in (set(ADMIN_USERS) | set(CONTADORA_USERS))}
        except Exception:
            _puede_ver_banco_a = False
        if not _puede_ver_banco_a:
            for _inf_a in influencers:
                for _cs in ('banco','cuenta_bancaria','tipo_cuenta','cedula_nit'):
                    if _inf_a.get(_cs):
                        _inf_a[_cs] = '***'

        # ── 2. Load pagos ──────────────────────────────────────────────────────
        try:
            pagos_rows = [dict(r) for r in c.execute(
                "SELECT influencer_id, influencer_nombre, valor, fecha, estado FROM pagos_influencers"
            ).fetchall()]
        except Exception:
            pagos_rows = []

        # ── 3. Load campanas per influencer ────────────────────────────────────
        try:
            camp_rows = [dict(r) for r in c.execute(
                "SELECT influencer_id, estado FROM marketing_campana_influencer"
            ).fetchall()]
        except Exception:
            camp_rows = []

        # ── 4. Load contenido per influencer ───────────────────────────────────
        try:
            cont_rows = [dict(r) for r in c.execute(
                "SELECT influencer_id, estado FROM marketing_contenido"
            ).fetchall()]
        except Exception:
            cont_rows = []

        # Index helpers
        pagos_by_id   = {}
        pagos_by_name = {}
        for p in pagos_rows:
            if p.get("influencer_id"):
                pagos_by_id.setdefault(p["influencer_id"], []).append(p)
            nm = (p.get("influencer_nombre") or "").strip().lower()
            if nm:
                pagos_by_name.setdefault(nm, []).append(p)

        camps_by_id  = {}
        for r in camp_rows:
            if r.get("influencer_id"):
                camps_by_id.setdefault(r["influencer_id"], []).append(r)

        cont_by_id  = {}
        for r in cont_rows:
            if r.get("influencer_id"):
                cont_by_id.setdefault(r["influencer_id"], []).append(r)

        today = _dt.today()

        # ── 5. Score each influencer ───────────────────────────────────────────
        def _score(inf, pagos, camps, conts):
            s = 0

            # Engagement (30 pts): engagement_rate stored as decimal (0.05 = 5%)
            eng = float(inf.get("engagement_rate") or 0)
            # If stored as percentage already (> 1.0), normalise
            if eng > 1.0:
                eng = eng / 100.0
            if eng >= 0.05:
                s += 30
            elif eng >= 0.03:
                s += 22
            elif eng >= 0.01:
                s += 12
            elif eng > 0:
                s += 5

            # Total investment in Pagada pagos (25 pts)
            pagadas = [p for p in pagos if p.get("estado") == "Pagada"]
            total_inv = sum(p.get("valor") or 0 for p in pagadas)
            if total_inv >= 5_000_000:
                s += 25
            elif total_inv >= 2_000_000:
                s += 18
            elif total_inv >= 500_000:
                s += 10
            elif total_inv > 0:
                s += 4

            # Seguidores (20 pts)
            seg = int(inf.get("seguidores") or 0)
            if seg >= 100_000:
                s += 20
            elif seg >= 50_000:
                s += 15
            elif seg >= 10_000:
                s += 8
            elif seg >= 1_000:
                s += 3

            # Recencia del ultimo pago (15 pts)
            fechas = [p.get("fecha") for p in pagadas if p.get("fecha")]
            if fechas:
                try:
                    ultima = max(_dt.strptime(f[:10], "%Y-%m-%d") for f in fechas)
                    days = (today - ultima).days
                    if days <= 30:
                        s += 15
                    elif days <= 90:
                        s += 10
                    elif days <= 180:
                        s += 5
                    else:
                        s += 1
                except Exception:
                    pass

            # Contenido publicado (10 pts)
            pub = [c2 for c2 in conts if c2.get("estado") == "Publicado"]
            if len(pub) >= 10:
                s += 10
            elif len(pub) >= 5:
                s += 7
            elif len(pub) >= 1:
                s += 3

            return min(s, 100)

        scored = []
        for inf in influencers:
            iid = inf["id"]
            pagos = pagos_by_id.get(iid, [])
            if not pagos:
                pagos = pagos_by_name.get(inf["nombre"].strip().lower(), [])
            pagadas_inf = [p for p in pagos if p.get("estado") == "Pagada"]
            camps = camps_by_id.get(iid, [])
            conts = cont_by_id.get(iid, [])
            score = _score(inf, pagos, camps, conts)

            inf["score"] = score
            inf["total_pagado"] = sum(p.get("valor") or 0 for p in pagadas_inf)
            inf["campanas_count"] = len(camps)
            scored.append(inf)

        # ── 6. Portfolio health ────────────────────────────────────────────────
        activos   = [i for i in scored if i.get("estado") == "Activo"]
        inactivos = [i for i in scored if i.get("estado") != "Activo"]
        # At-risk: active with score < 25 or no payment in 180+ days
        en_riesgo = []
        for i in activos:
            if i["score"] < 25:
                en_riesgo.append(i)
            else:
                pagos_i = pagos_by_id.get(i["id"], []) or pagos_by_name.get(i["nombre"].strip().lower(), [])
                pagadas_i = [p for p in pagos_i if p.get("estado") == "Pagada"]
                if pagadas_i:
                    try:
                        ultima = max(_dt.strptime(p["fecha"][:10], "%Y-%m-%d") for p in pagadas_i if p.get("fecha"))
                        if (today - ultima).days > 180:
                            en_riesgo.append(i)
                    except Exception:
                        pass

        portfolio = {
            "activos": len(activos),
            "inactivos": len(inactivos),
            "en_riesgo": len(en_riesgo),
            "total": len(scored),
        }

        # ── 7. Audit findings ─────────────────────────────────────────────────
        audit = []

        # Critical: influencers with pending payments > 60 days
        try:
            old_pending = [dict(r) for r in c.execute("""
                SELECT influencer_nombre, valor, fecha FROM pagos_influencers
                WHERE estado='Pendiente' AND fecha <= date('now', '-5 hours', '-60 days')
            """).fetchall()]
            for op in old_pending:
                audit.append({
                    "severity": "critical",
                    "finding": f"Pago pendiente de ${op.get('valor',0):,} para {op['influencer_nombre']} con +60 días sin resolver (desde {op.get('fecha','?')})",
                    "recommendation": "Revisar OC correspondiente y confirmar método de pago."
                })
        except Exception:
            pass

        # Critical: missing banking data for active influencers
        no_banco = [i for i in activos if not i.get("banco") and not i.get("cuenta_bancaria")]
        if no_banco:
            audit.append({
                "severity": "critical",
                "finding": f"{len(no_banco)} influencer(s) activos sin datos bancarios registrados: {', '.join(i['nombre'] for i in no_banco[:5])}{'...' if len(no_banco)>5 else ''}",
                "recommendation": "Completar información bancaria antes del próximo ciclo de pagos."
            })

        # High: active influencers with score < 30
        low_score = [i for i in activos if i["score"] < 30]
        if low_score:
            audit.append({
                "severity": "high",
                "finding": f"{len(low_score)} influencer(s) activo(s) con score bajo (<30): {', '.join(i['nombre'] for i in low_score[:4])}",
                "recommendation": "Evaluar renovar acuerdo o reemplazar por perfiles con mejor performance."
            })

        # High: no campaigns active
        try:
            active_camps = c.execute(
                "SELECT COUNT(*) FROM marketing_campanas WHERE estado IN ('Activa','En Ejecucion','Planificada')"
            ).fetchone()[0]
            if active_camps == 0:
                audit.append({
                    "severity": "high",
                    "finding": "Sin campañas activas o planificadas en el sistema.",
                    "recommendation": "Crear al menos una campaña para el siguiente período."
                })
        except Exception:
            pass

        # Medium: no engagement rate for active influencers
        no_eng = [i for i in activos if not i.get("engagement_rate")]
        if no_eng:
            audit.append({
                "severity": "medium",
                "finding": f"{len(no_eng)} influencer(s) sin tasa de engagement registrada.",
                "recommendation": "Actualizar perfil con datos de IG/TikTok para scoring preciso."
            })

        # Medium: no seguidores for active influencers
        no_seg = [i for i in activos if not i.get("seguidores")]
        if no_seg:
            audit.append({
                "severity": "medium",
                "finding": f"{len(no_seg)} influencer(s) sin número de seguidores registrado.",
                "recommendation": "Sincronizar Instagram o actualizar manualmente los perfiles."
            })

        # Low: concentration risk — if top 3 influencers > 70% of spend
        total_inv_all = sum(i.get("total_pagado", 0) for i in scored)
        if total_inv_all > 0:
            top3_inv = sum(i.get("total_pagado", 0) for i in sorted(scored, key=lambda x: x.get("total_pagado", 0), reverse=True)[:3])
            if top3_inv / total_inv_all > 0.70:
                audit.append({
                    "severity": "low",
                    "finding": f"Concentración de inversión: los 3 influencers con mayor pago acumulan el {round(top3_inv/total_inv_all*100)}% del presupuesto total.",
                    "recommendation": "Diversificar el portafolio para reducir dependencia en perfiles individuales."
                })

        # Low: at-risk influencers
        if en_riesgo:
            audit.append({
                "severity": "low",
                "finding": f"{len(en_riesgo)} influencer(s) en riesgo de inactividad (sin pago en 6+ meses o score muy bajo).",
                "recommendation": "Contactar proactivamente para reactivar relación o dar de baja."
            })

        # ── 8. Competition analysis ───────────────────────────────────────────
        niches = {}
        for i in activos:
            nicho = (i.get("nicho") or "Sin clasificar").strip()
            niches[nicho] = niches.get(nicho, 0) + 1

        # Detect gaps: key niches for skincare that are missing
        target_niches = {"Skincare", "Belleza", "Lifestyle", "Fitness", "Nutricion", "Maternidad"}
        present_niches_lower = {n.lower() for n in niches.keys()}
        gaps = []
        for tn in target_niches:
            if tn.lower() not in present_niches_lower:
                gaps.append(f"Nicho '{tn}' no representado en el portafolio actual — alta afinidad con ÁNIMUS Lab")

        competition = {
            "niches": niches,
            "gaps": gaps[:5],
        }

        # ── 9. Campaign proposals ─────────────────────────────────────────────
        proposals = []
        top_influencers = sorted(activos, key=lambda x: x.get("score", 0), reverse=True)[:5]
        top_names = [i["nombre"] for i in top_influencers]

        # Proposal 1: Re-activate top scorers
        if top_influencers:
            proposals.append({
                "title": "Campaña de Reactivación — Top Performers",
                "description": f"Activar los {len(top_influencers)} influencers con mayor score para una campaña coordenada de lanzamiento de producto. Enfoque en contenido tipo unboxing + review honesta.",
                "priority": "alta",
                "budget_est": f"${len(top_influencers) * 800_000:,}",
                "influencers_needed": len(top_influencers),
                "expected_reach": f"{len(top_influencers) * 15000:,} impresiones est."
            })

        # Proposal 2: Niche gap fill
        if gaps:
            proposals.append({
                "title": "Expansión de Nicho — Skincare Científico",
                "description": "Reclutar 3–5 influencers especializados en skincare con audiencia Latam (Colombia, México, Chile). Perfil ideal: dermatología divulgativa, rutinas AM/PM, piel latina.",
                "priority": "alta",
                "budget_est": "$2,500,000",
                "influencers_needed": 4,
                "expected_reach": "50K+ impresiones est."
            })

        # Proposal 3: Content series
        proposals.append({
            "title": "Serie de Contenido — 'Ciencia en tu Piel'",
            "description": "5 publicaciones semanales durante 4 semanas con 3 influencers rotatorios. Cada post explica un ingrediente activo de ÁNIMUS Lab. Ideal para construir autoridad de marca.",
            "priority": "media",
            "budget_est": "$3,600,000",
            "influencers_needed": 3,
            "expected_reach": "80K+ impresiones est."
        })

        # Proposal 4: If there are low-score actives, suggest cleanup
        if low_score:
            proposals.append({
                "title": "Revisión de Portafolio — Optimización Q2",
                "description": f"Evaluar la continuidad de {len(low_score)} influencer(s) con score bajo. Redirigir presupuesto hacia perfiles con mejor engagement y mayor afinidad de nicho con ÁNIMUS Lab.",
                "priority": "media",
                "budget_est": "Sin costo adicional",
                "influencers_needed": 0,
                "expected_reach": "Optimización de ROI"
            })

        # Proposal 5: Seasonality
        month = today.month
        if month in [11, 12]:
            proposals.append({
                "title": "Campaña Fin de Año — Kits de Regalo",
                "description": "Campaña de regalo navideño con kits ÁNIMUS Lab. Influencers con audiencia femenina 25–40 años, foco en productos de hidratación y antienvejecimiento.",
                "priority": "alta",
                "budget_est": "$5,000,000",
                "influencers_needed": 6,
                "expected_reach": "120K+ impresiones est."
            })
        elif month in [1, 2]:
            proposals.append({
                "title": "Campaña 'Nuevo Año, Nueva Rutina'",
                "description": "Aprovechar el peak de resolutions en enero/febrero. Influencers presentan rutina skincare AM/PM completa usando productos ÁNIMUS Lab como base científica.",
                "priority": "media",
                "budget_est": "$4,000,000",
                "influencers_needed": 5,
                "expected_reach": "100K+ impresiones est."
            })
        else:
            proposals.append({
                "title": "Campaña Awareness — 'Piel Latina Merece Ciencia'",
                "description": "Campaña de posicionamiento de marca con énfasis en diferenciación científica vs. cosmética genérica. Stories + Reels cortos mostrando resultados reales.",
                "priority": "baja",
                "budget_est": "$2,000,000",
                "influencers_needed": 4,
                "expected_reach": "60K+ impresiones est."
            })

        return jsonify({
            "influencers": scored,
            "portfolio": portfolio,
            "audit": audit,
            "competition": competition,
            "proposals": proposals,
        })

    except Exception as _exc:
        import traceback as _tb
        return jsonify({
            "error": str(_exc),
            "trace": _tb.format_exc()[-1000:]
        }), 500
    finally:
        conn.close()


