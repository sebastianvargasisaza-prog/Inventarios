"""
Blueprint: Centro de Programación
Endpoints:
  GET  /api/programacion/resumen        — dashboard principal (velocidad + stock + alertas + IA)
  GET  /api/programacion/velocidad      — velocidad Shopify por SKU (últimos 60 días)
  GET  /api/programacion/calendario     — eventos Google Calendar próximos 90 días
  GET  /api/programacion/stock-60d      — proyección consolidada 60 días por producto
  GET  /api/programacion/alertas        — alertas inteligentes (schedule + stock)
  POST /api/programacion/seed-formulas  — (dev) fuerza re-seed de fórmulas desde DB
  GET  /api/programacion/productos      — lista de productos con fórmulas

Dependencias de env:
  GOOGLE_API_KEY   — API key con acceso a Calendar API (calendar público o compartido)
  CALENDAR_ID      — Google Calendar ID de producción
  ANTHROPIC_API_KEY — para narrativa IA
"""

from flask import Blueprint, jsonify, request, session
import os, json, logging, sqlite3, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta, date
from database import get_db
from config import ADMIN_USERS, APP_BASE_URL

bp = Blueprint('programacion', __name__)

CALENDAR_ID      = os.environ.get('CALENDAR_ID', 'c_d3a06d5f8ace62d5566968a70aeb2f3bd1d0a5b6b2b2f8c6b4ad66ac0d03286c@group.calendar.google.com')
GOOGLE_API_KEY   = os.environ.get('GOOGLE_API_KEY', '')
GCAL_ICAL_URL    = os.environ.get('GCAL_ICAL_URL', '')   # iCal feed URL (no API key needed)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ─── Auth helper ────────────────────────────────────────────────────────────

def _auth():
    return bool(session.get('compras_user') or session.get('cont_user'))

# ─── Shopify velocity ────────────────────────────────────────────────────────

# ─── Shopify velocity ────────────────────────────────────────────────────────

def _sync_shopify_orders(conn, days=60):
    """Sync ordenes Shopify directo desde API, independiente de marketing.

    Pagina created_at_min=now-days hasta hoy. Guarda en animus_shopify_orders.
    Programacion no depende de que marketing haya sincronizado primero.
    """
    def _cfg(c):
        r = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (c,)).fetchone()
        return r[0] if r else None

    token = _cfg("shopify_token")
    shop  = _cfg("shopify_shop")
    if not token or not shop:
        return {"ok": False, "error": "Shopify no configurado"}

    since_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    url = ("https://" + shop +
           "/admin/api/2024-01/orders.json?status=any&limit=250&created_at_min=" + since_dt)
    synced = 0

    while url:
        req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read())
                link_hdr = r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            return {"ok": False, "error": "Shopify HTTP " + str(e.code) + ": " + body}
        except Exception as e:
            return {"ok": False, "error": "Red: " + str(e)}

        for o in data.get("orders", []):
            line_items = o.get("line_items", [])
            items_sku = json.dumps([
                {"sku": li.get("sku") or "", "qty": li.get("quantity", 0)}
                for li in line_items if li.get("sku")
            ])
            total_uds = sum(li.get("quantity", 0) for li in line_items)
            addr = o.get("shipping_address") or o.get("billing_address") or {}
            sql = (
                "INSERT OR REPLACE INTO animus_shopify_orders "
                "(shopify_id,nombre,email,total,moneda,estado,estado_pago,"
                "sku_items,unidades_total,ciudad,pais,creado_en,synced_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))"
            )
            conn.execute(sql, (
                str(o["id"]), o.get("name",""), o.get("email",""),
                float(o.get("total_price") or 0), o.get("currency","COP"),
                o.get("fulfillment_status") or "unfulfilled",
                o.get("financial_status",""),
                items_sku, total_uds,
                addr.get("city",""), addr.get("country_code","CO"),
                (o.get("created_at") or "")[:10]
            ))
            synced += 1

        next_url = None
        for part in link_hdr.split(","):
            if "rel=\"next\"" in part:
                s = part.find("<") + 1
                e2 = part.find(">")
                if s > 0 and e2 > s:
                    next_url = part[s:e2].strip()
        url = next_url

    conn.commit()
    return {"ok": True, "synced": synced, "days": days}


def _shopify_velocity(conn, days=60):
    """
    Lee animus_shopify_orders de los últimos `days` días.
    Retorna dict {sku_full: vel_mes} y dict {producto_nombre: vel_mes}.

    Lookup de producto: exacto primero, luego parte antes del primer guión
    (pero NUNCA trunca a 6 chars — eso rompía SVITC33 y RECN-2).
    """
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT sku_items, unidades_total, creado_en FROM animus_shopify_orders WHERE creado_en >= ? AND sku_items IS NOT NULL",
        (since,)
    ).fetchall()

    sku_units = {}  # full_sku -> total units in period

    for row in rows:
        try:
            items = json.loads(row[0]) if row[0] else []
        except Exception:
            items = []
        for item in items:
            raw_sku = str(item.get('sku', '') or '').strip().upper()
            qty = int(item.get('qty', 0) or 0)
            if not raw_sku or qty <= 0:
                continue
            # Store full SKU — no truncation
            sku_units[raw_sku] = sku_units.get(raw_sku, 0) + qty

    # Denominador inteligente: prefiere ventana real solicitada (`days`) si
    # hay cobertura suficiente; sino cae a `actual_days` PERO marca data
    # quality como baja para que la UI advierta al usuario.
    #
    # Antes (CRITICAL fix #6 auditoría): siempre dividía por (d_max - d_min)
    # → si solo había 4 días de datos, la velocidad salía 10× más alta de
    # lo real, sobreestimando ventas y subestimando días de cobertura.
    actual_days = days  # default conservador
    data_quality = 'ok'
    coverage_pct = 100
    if rows:
        all_dates = [r[2] for r in rows if r[2]]
        if len(all_dates) >= 2:
            from datetime import date as _dt
            d_min = _dt.fromisoformat(min(all_dates)[:10])
            d_max = _dt.fromisoformat(max(all_dates)[:10])
            real_span = max((d_max - d_min).days, 1)
            coverage_pct = int(min(100, (real_span / max(days, 1)) * 100))
            # Si cobertura >= 80%: el período pedido es representativo,
            # dividir por `days` evita inflar por gaps al inicio/final.
            # Si < 80%: dividimos por real_span pero marcamos baja calidad.
            if coverage_pct >= 80:
                actual_days = days
                data_quality = 'ok'
            else:
                actual_days = real_span
                data_quality = 'low'  # poca data → no confiable para decisiones
        else:
            # 1 sola fecha: extrapolar es engañoso. Usamos days completo.
            actual_days = days
            data_quality = 'very_low'
            coverage_pct = 0
    else:
        actual_days = days
        data_quality = 'no_data'
        coverage_pct = 0
    months = max(actual_days / 30.0, 1/30.0)
    sku_vel = {sku: round(units / months, 1) for sku, units in sku_units.items()}

    # Build lookup map: SKU -> producto_nombre
    sku_map = {}
    for row in conn.execute("SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1").fetchall():
        sku_map[row[0].upper()] = row[1]

    prod_vel = {}  # producto_nombre -> vel_mes
    for sku, vel in sku_vel.items():
        # 1) Exact match (handles RECN-2, SVITC33, SVITC3315, NPHA10, etc.)
        prod = sku_map.get(sku)
        # 2) Fallback: try the part before the first hyphen (e.g. LBHA-30 -> LBHA)
        if not prod and '-' in sku:
            prod = sku_map.get(sku.split('-')[0])
        if prod:
            prod_vel[prod] = round(prod_vel.get(prod, 0) + vel, 1)

    return {
        'sku_velocity': sku_vel,
        'prod_velocity': prod_vel,
        'total_orders': len(rows),
        'days_requested': days,
        'actual_days_data': actual_days,
        'months_analyzed': round(months, 2),
        'data_quality': data_quality,    # ok|low|very_low|no_data
        'coverage_pct': coverage_pct,
    }

# ─── Google Calendar ─────────────────────────────────────────────────────────

def _parse_ical(text, days_ahead=90):
    """Parse iCal text and return list of {titulo, fecha} dicts."""
    import re as _re
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    events = []
    # Split into VEVENT blocks
    for block in _re.split(r'BEGIN:VEVENT', text)[1:]:
        summary = ''
        dt_str  = ''
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('SUMMARY:'):
                summary = line[8:].replace('\n', ' ').replace(r'\,', ',').strip()
            elif line.startswith('DTSTART'):
                # DTSTART;VALUE=DATE:20260502 or DTSTART:20260502T... 
                val = line.split(':', 1)[-1].strip()
                dt_str = val[:8]  # YYYYMMDD
        if summary and dt_str and len(dt_str) == 8:
            try:
                ev_date = date(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]))
                if today <= ev_date <= cutoff:
                    events.append({'titulo': summary, 'fecha': ev_date.isoformat(),
                                   'descripcion': '', 'id': ''})
            except ValueError:
                pass
    return sorted(events, key=lambda e: e['fecha'])


def _fetch_calendar_events(days_ahead=90):
    """Fetch production calendar events.
    Priority: 1) iCal feed (GCAL_ICAL_URL), 2) Google Calendar API (GOOGLE_API_KEY).
    """
    # ── Option 1: iCal feed (public or secret URL, no API key required) ──────
    if GCAL_ICAL_URL:
        try:
            req = urllib.request.Request(
                GCAL_ICAL_URL,
                headers={'User-Agent': 'EspagiRIA-Inventarios/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                text = r.read().decode('utf-8', errors='replace')
            events = _parse_ical(text, days_ahead)
            return {'events': events, 'error': None, 'source': 'ical'}
        except Exception as e:
            return {'events': [], 'error': f'iCal error: {e}', 'source': 'ical'}

    # ── Option 2: Google Calendar API (requires GOOGLE_API_KEY) ──────────────
    if not GOOGLE_API_KEY:
        return {'events': [], 'error': 'Configura GCAL_ICAL_URL en Render para leer el calendario', 'source': 'none'}

    now = datetime.utcnow()
    time_min = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    time_max = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%dT%H:%M:%SZ')
    params = urllib.parse.urlencode({
        'key': GOOGLE_API_KEY,
        'timeMin': time_min,
        'timeMax': time_max,
        'singleEvents': 'true',
        'orderBy': 'startTime',
        'maxResults': 100,
    })
    cal_id_encoded = urllib.parse.quote(CALENDAR_ID, safe='')
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id_encoded}/events?{params}"
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        events = []
        for item in data.get('items', []):
            start = item.get('start', {})
            start_dt = start.get('dateTime', start.get('date', ''))[:10]
            events.append({
                'titulo': item.get('summary', 'Producción'),
                'fecha': start_dt,
                'descripcion': item.get('description', ''),
                'id': item.get('id', ''),
            })
        return {'events': events, 'error': None, 'source': 'gcal_api'}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        return {'events': [], 'error': f'Calendar API HTTP {e.code}: {body}', 'source': 'gcal_api'}
    except Exception as e:
        return {'events': [], 'error': str(e), 'source': 'gcal_api'}

def _fetch_local_production_events(conn):
    """Return upcoming AND recent past (≤14d) production events from produccion_programada.

    Including recent past events lets the dashboard surface productions that were
    scheduled but not yet marked as 'completado', so they don't silently disappear
    from the Prox. Produccion column. Past-dated events carry past_date=True.
    """
    try:
        rows = conn.execute(
            """SELECT id, producto, fecha_programada, lotes, estado, observaciones
               FROM produccion_programada
               WHERE estado NOT IN ('completado','cancelado')
                 AND fecha_programada >= date('now', '-14 days')
               ORDER BY fecha_programada"""
        ).fetchall()
        import datetime as _dt
        today_str = str(_dt.date.today())
        return [
            {'id': r[0], 'titulo': r[1], 'fecha': r[2],
             'lotes': r[3], 'estado': r[4], 'descripcion': r[5] or '',
             'past_date': r[2] < today_str}
            for r in rows
        ]
    except Exception as e:
        return []

# ─── MP stock ────────────────────────────────────────────────────────────────

def _norm_mp_name(name):
    """Normalise an MP name for fuzzy matching across two legacy ID systems.
    Removes: accents, parenthetical suffixes, hyphens->space, collapse spaces,
    and adds space between digits and letters (50KD -> 50 KD).
    """
    import unicodedata as _ud
    import re as _re
    s = str(name or '').strip()
    # Strip embedded control characters (Excel import artifacts)
    import re as _re2
    s = _re2.sub(r'[\x00-\x1f\x7f]', '', s)
    # Strip accents
    s = ''.join(c for c in _ud.normalize('NFD', s) if _ud.category(c) != 'Mn')
    s = s.upper()
    # Remove parenthetical additions like (LYPHAR), (BASF), (1%)
    s = _re.sub(r'\([^)]*\)', '', s)
    # Hyphens and slashes to space
    s = _re.sub(r'[-/]', ' ', s)
    # Add space between digit and letter: 50KD -> 50 KD, 300KD -> 300 KD
    s = _re.sub(r'(\d)([A-Z])', r'\1 \2', s)
    s = _re.sub(r'([A-Z])(\d)', r'\1 \2', s)
    # Collapse multiple spaces
    s = _re.sub(r'\s+', ' ', s).strip()
    return s


# Static alias map: normalised formula name -> normalised movimientos name
# Handles brand-name differences, typos, Spanish/English variants, presentation suffixes
_MP_NAME_ALIAS = {
    # HIALURONICO missing ACIDO prefix
    'HIALURONICO 50 KD':   'ACIDO HIALURONICO 50 KD',
    'HIALURONICO 300 KD':  'ACIDO HIALURONICO 300 KD',
    'HIALURONICO 1500 KD': 'ACIDO HIALURONICO 1500 KD',
    # Typos in formula names
    'ACIDO HILAURONICO 50 KD':  'ACIDO HIALURONICO 50 KD',   # double A
    'ALCOHOL CETITLICO':        'ALCOHOL CETILICO',            # extra T
    'ACETYL TETRAPETIDE 5':     'ACETYL TETRAPEPTIDE 5',       # missing P
    'ACETYL TETRAPETIDE-5':     'ACETYL TETRAPEPTIDE 5',
    # Spanish -> English ingredient names
    'ACETIL TETRAPEPTIDO 40':  'ACETYL TETRAPEPTIDE 40',
    'ACETIL TETRAPEPTIDO-40':  'ACETYL TETRAPEPTIDE 40',
    'ACETIL TETRAPEPTIDO 3':   'ACETYL TETRAPEPTIDE 3',
    'ACETIL TETRAPEPTIDO-3':   'ACETYL TETRAPEPTIDE 3',
    # Brand/commercial name differences
    'ACEITE DE ARGAN':       'BEAUTY OIL ARGAN',
    'ACEITE ARGAN':          'BEAUTY OIL ARGAN',
    'ACEITE DE JOJOBA':      'BEAUTY OIL JOJOBA',
    'ACEITE JOJOBA':         'BEAUTY OIL JOJOBA',
    'ACEITE DE ROSA MOSQUETA': 'BEAUTY OIL ROSA MOSQUETA',
    # Presentation/form differences
    'ALOE VERA':             'ALOE VERA POLVO',
    'ACEITE ARBOL DE TE':    'ACEITE ESENCIAL ARBOL DE TE',
    'D PANTENOL':            'D PANTENOL LIQUIDO',
    'D-PANTENOL':            'D PANTENOL LIQUIDO',
    # Ascorbic acid derivatives
    '3 O ACIDO ETIL ASCORBICO': 'ETIL ASCORBICO ACID',
    'ASCORBIL GLUCOSIDE':        'ASCORBIL GLUCOSIDE',
    # Pantenol variants (without D- prefix)
    'PANTENOL LIQUIDO':   'D PANTENOL LIQUIDO',
    'PANTENOL SOLIDO':    'D PANTENOL SOLIDO',
    'PANTENOL':           'PANTENOL POLVO',
    # Centella variants
    'CENTELLA ASIATICA POLVO': 'CENTELLA ASIATICA',
    'CENTELLA ASIATICA':       'CENTELLA ASIATICA',
    'CENTELLA':                'CENTELLA ASIATICA',
    # Commercial name differences (formula uses generic, bodega uses brand)
    'EZ 4U':                   'PEMULEN EZ 4U',   # EZ-4U -> Pemulen EZ-4U
    'EZ-4U':                   'PEMULEN EZ 4U',
    'GRANSIL V 419':           'GRANSIL VX 419',   # Gransil variants
    'GRANSIL VX419':           'GRANSIL VX 419',
    'GRANSIL VX-419':          'PEMULEN EZ 4U',   # placeholder, update when confirmed
    # Regaliz / licorice
    'REGALIZ':                 'EXTRACTO DE REGALIZ',
    'EXTRACTO REGALIZ':        'EXTRACTO DE REGALIZ',
    # Silicona (update once Bodega MP name confirmed)
    'SILICONA LIQUIDA':        'DIMETHICONE',
    'SILICONA':                'DIMETHICONE',
}


# MPs that are always available (own production equipment — effectively infinite stock)
_MP_UNLIMITED = {
    'AGUA DESIONIZADA', 'AGUA PURIFICADA', 'AGUA DESTILADA',
    'AGUA PURIFICADA TOTAL', 'AGUA', 'AQUA',
}
_MP_UNLIMITED_NORM = set()  # populated lazily in _get_mp_stock


def _detect_alias_collisions(conn):
    """Detecta nombres de MP distintos que colapsan al mismo nombre normalizado.

    Si dos MPs reales con codigos distintos normalizan al mismo nombre, el
    alias map puede hacer que el stock de uno se atribuya al otro silenciosamente.
    Esta función lo detecta y devuelve la lista para alertar al usuario.

    Returns: lista de dicts con {'norm', 'variantes': [{codigo, nombre}, ...]}
    """
    by_norm = {}
    try:
        rows = conn.execute(
            "SELECT codigo_mp, nombre_comercial FROM maestro_mps WHERE activo=1"
        ).fetchall()
        for codigo, nombre in rows:
            n = _norm_mp_name(nombre or '')
            if not n:
                continue
            by_norm.setdefault(n, []).append({
                'codigo': str(codigo or ''),
                'nombre': str(nombre or ''),
            })
    except Exception:
        return []
    collisions = []
    for n, variantes in by_norm.items():
        if len(variantes) >= 2:
            # Solo es colisión real si los nombres originales son distintos
            distintos = {v['nombre'].strip().upper() for v in variantes}
            if len(distintos) >= 2:
                collisions.append({'normalizado': n, 'variantes': variantes})
    return collisions


def _is_unlimited_mp(nombre):
    """Return True if the MP is produced on-site (water equipment, etc.)."""
    n = str(nombre or '').strip().upper()
    return n in _MP_UNLIMITED or any(u in n for u in ('AGUA DESIONIZADA', 'AGUA PURIFICADA'))


def _get_mp_stock(conn):
    """Returns dict {key: stock_actual_g} keyed by material_id AND all known nombres.

    Two-pass strategy to avoid split-stock bugs when the same material_id appears
    in movimientos under different material_nombre values (e.g. 'PROPYLENE GLYCOL'
    and 'PROPILENGLICOL' are both MP00121):

    Pass 1 – aggregate stock correctly by material_id (canonical total).
    Pass 2 – collect all (material_id, material_nombre) pairs; map every name
             to the canonical stock for that material_id.
    """
    # Pass 1: canonical stock per material_id
    id_stock = {}
    for mid, sg in conn.execute("""
        SELECT material_id,
               COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
                                 THEN cantidad ELSE -cantidad END), 0)
        FROM movimientos
        WHERE material_id IS NOT NULL AND material_id != ''
        GROUP BY material_id
    """).fetchall():
        id_stock[str(mid).strip()] = max(float(sg or 0), 0)

    # Pass 2: collect all name variants per material_id
    name_rows = conn.execute(
        "SELECT DISTINCT material_id, material_nombre FROM movimientos "
        "WHERE material_nombre IS NOT NULL AND material_nombre != ''"
    ).fetchall()

    stock = {}
    # Index by canonical material_id first
    for mid, val in id_stock.items():
        stock[mid] = val

    # Index by every name variant, resolved to the canonical material_id stock
    for mid, nombre in name_rows:
        mid_key = str(mid or '').strip()
        val = id_stock.get(mid_key, 0)  # canonical stock for this material_id
        nombre_s = str(nombre).strip()
        # exact uppercase
        key_exact = nombre_s.upper()
        if key_exact not in stock:
            stock[key_exact] = val
        # normalised (strips accents, hyphens, parentheses, control chars)
        key_norm = _norm_mp_name(nombre_s)
        if key_norm and key_norm not in stock:
            stock[key_norm] = val

    # Also index materials that only appear without a material_id (legacy rows)
    for nombre, sg in conn.execute("""
        SELECT material_nombre,
               COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
                                 THEN cantidad ELSE -cantidad END), 0)
        FROM movimientos
        WHERE (material_id IS NULL OR material_id = '')
          AND material_nombre IS NOT NULL AND material_nombre != ''
        GROUP BY material_nombre
    """).fetchall():
        val = max(float(sg or 0), 0)
        key_exact = str(nombre).strip().upper()
        if key_exact not in stock:
            stock[key_exact] = val
        key_norm = _norm_mp_name(str(nombre))
        if key_norm and key_norm not in stock:
            stock[key_norm] = val

    # Bridge tier (tier 5): formula_material_id → bodega_material_id → canonical stock.
    # This resolves cases where formula_items uses one ID system and movimientos uses another.
    # The mp_formula_bridge table maps them explicitly (populated via admin UI).
    try:
        bridge_rows = conn.execute(
            "SELECT formula_material_id, bodega_material_id FROM mp_formula_bridge WHERE activo=1"
        ).fetchall()
        for fid, bid in bridge_rows:
            fid_key = str(fid or '').strip()
            bid_key = str(bid or '').strip()
            if not fid_key or not bid_key:
                continue
            bodega_stock = id_stock.get(bid_key, 0)
            # Index by formula_material_id (primary bridge key)
            if fid_key not in stock:
                stock[fid_key] = bodega_stock
            # Also index by normalised formula name if available (from bridge table)
    except Exception:
        pass  # bridge table may not exist in older DB snapshots

    return stock

# ─── Formula lookup ──────────────────────────────────────────────────────────

def _get_formulas(conn):
    """Returns dict {producto_nombre: {'lote_size_kg': X, 'items': [...{material_id,pct,g}...]}}"""
    headers = conn.execute(
        "SELECT producto_nombre, unidad_base_g, lote_size_kg FROM formula_headers"
    ).fetchall()
    items_all = conn.execute(
        "SELECT producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote FROM formula_items"
    ).fetchall()

    items_map = {}
    for row in items_all:
        p = row[0]
        items_map.setdefault(p, []).append({
            'material_id': row[1],
            'material_nombre': row[2],
            'porcentaje': float(row[3] or 0),
            'cantidad_g_por_lote': float(row[4] or 0),
        })

    formulas = {}
    for h in headers:
        pname = h[0]
        ub_g = float(h[1] or 0)
        lote_kg = float(h[2] or (ub_g / 1000 if ub_g else 0))
        formulas[pname] = {
            'lote_size_kg': lote_kg,
            'unidad_base_g': ub_g,
            'items': items_map.get(pname, []),
        }
    return formulas

# ─── Helpers: PT stock y MEE stock ──────────────────────────────────────────

def _get_stock_pt(conn):
    """Stock real de producto terminado desde stock_pt.

    REGLA DE AUTORIDAD (fix CRITICAL #1 auditoría): si para un SKU hay rows
    liberados por CC (lote_produccion NO empieza con 'SHOPIFY-'), ESOS son
    la fuente de verdad. Los snapshots de Shopify se IGNORAN para ese SKU
    (porque la app ya descuenta y libera; los rows SHOPIFY son redundantes
    y al sumarlos se doble contaba el stock).

    Si para un SKU SOLO hay rows de SHOPIFY (porque nunca se ha liberado
    desde CC), se usan como fallback. Eso cubre productos que aún no han
    pasado por el flujo de maquila local.

    Loguea warning si los rows SHOPIFY tienen >24h (staleness) — señal de
    que el sync se está retrasando y conviene revisar el cron.
    """
    sku_map = {}
    try:
        for row in conn.execute(
            "SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            k = str(row[0] or '').strip().upper()
            if k:
                sku_map[k] = str(row[1] or '').strip().upper()
    except Exception:
        pass

    # Separar stock por origen: CC liberado vs SHOPIFY snapshot
    cc_stock = {}      # SKU → uds (autoridad real)
    shop_stock = {}    # SKU → uds (snapshot, fallback)
    shop_max_age_hours = 0.0
    try:
        rows = conn.execute("""
            SELECT UPPER(TRIM(sku)) AS sku,
                   COALESCE(lote_produccion, '') AS lote,
                   COALESCE(SUM(unidades_disponible), 0) AS uds,
                   MAX(COALESCE(fecha_liberacion, fecha_creacion, '')) AS fmax
            FROM stock_pt
            WHERE estado = 'Disponible'
            GROUP BY UPPER(TRIM(sku)),
                     CASE WHEN COALESCE(lote_produccion,'') LIKE 'SHOPIFY-%'
                          THEN 'SHOPIFY' ELSE 'CC' END
        """).fetchall()
    except sqlite3.OperationalError:
        # Esquema viejo sin fecha_liberacion/fecha_creacion: fallback simple
        rows = conn.execute("""
            SELECT UPPER(TRIM(sku)) AS sku,
                   COALESCE(lote_produccion, '') AS lote,
                   COALESCE(SUM(unidades_disponible), 0) AS uds,
                   '' AS fmax
            FROM stock_pt
            WHERE estado = 'Disponible'
            GROUP BY UPPER(TRIM(sku)),
                     CASE WHEN COALESCE(lote_produccion,'') LIKE 'SHOPIFY-%'
                          THEN 'SHOPIFY' ELSE 'CC' END
        """).fetchall()

    from datetime import datetime as _dt
    for row in rows:
        raw_sku = str(row[0] or '').strip().upper()
        lote = str(row[1] or '')
        uds = max(int(row[2] or 0), 0)
        fmax = str(row[3] or '')
        if not raw_sku or uds <= 0:
            continue
        if lote.startswith('SHOPIFY-'):
            shop_stock[raw_sku] = shop_stock.get(raw_sku, 0) + uds
            if fmax:
                try:
                    age_h = (_dt.utcnow() - _dt.fromisoformat(fmax.replace('Z', ''))).total_seconds() / 3600.0
                    if age_h > shop_max_age_hours:
                        shop_max_age_hours = age_h
                except Exception:
                    pass
        else:
            cc_stock[raw_sku] = cc_stock.get(raw_sku, 0) + uds

    # Resolver: CC manda; SHOPIFY solo para SKUs sin row de CC
    resolved = {}
    for sku, uds in cc_stock.items():
        resolved[sku] = uds
    for sku, uds in shop_stock.items():
        if sku not in resolved:
            resolved[sku] = uds

    if shop_max_age_hours > 24:
        logging.getLogger('programacion').warning(
            "Stock PT desde SHOPIFY tiene %.1fh de antigüedad — revisa el cron de sync",
            shop_max_age_hours
        )

    # Mapear SKU → producto_nombre
    stock = {}
    for raw_sku, uds in resolved.items():
        prod = sku_map.get(raw_sku)
        if not prod:
            prefix = raw_sku.split('-')[0]
            prod = sku_map.get(prefix)
        if prod:
            stock[prod] = stock.get(prod, 0) + uds
        else:
            stock[raw_sku] = stock.get(raw_sku, 0) + uds

    return stock


def _get_mee_stock(conn):
    """
    MEE stock from movimientos_mee (Entrada-Salida).
    Falls back to maestro_mee.stock_actual where no movements exist.
    Returns dict {codigo_upper: stock_float}
    """
    # From movements (accurate)
    stock = {}
    try:
        for row in conn.execute("""
            SELECT mee_codigo,
                   COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad
                                     WHEN tipo='Salida'  THEN -cantidad
                                     ELSE 0 END), 0)
            FROM movimientos_mee WHERE anulado=0 GROUP BY mee_codigo
        """).fetchall():
            k = str(row[0] or '').strip().upper()
            if k:
                stock[k] = max(float(row[1] or 0), 0)
    except Exception:
        pass
    # Fill in maestro_mee.stock_actual for codes with no movements
    try:
        for row in conn.execute("SELECT codigo, stock_actual FROM maestro_mee").fetchall():
            k = str(row[0] or '').strip().upper()
            if k and k not in stock:
                stock[k] = max(float(row[1] or 0), 0)
    except Exception:
        pass
    return stock


# ─── Stock projection ────────────────────────────────────────────────────────

# Umbrales de cobertura (días). Se leen de env si están definidos para
# permitir ajuste sin redeploy. Default 20/40 = comportamiento histórico.
def _dias_thresholds():
    try:
        c = max(1, int(os.environ.get('DIAS_CRITICOS') or 20))
        a = max(c + 1, int(os.environ.get('DIAS_ALERTA') or 40))
        return c, a
    except (ValueError, TypeError):
        return 20, 40

DIAS_CRITICOS, DIAS_ALERTA = _dias_thresholds()

# Lead time por MP (días). Si una MP viene de China, el sistema necesita
# anticipar la compra ~60 días antes del agotamiento. Para MPs locales,
# 21 días es razonable (compra → entrega).
LEAD_TIME_CHINA = int(os.environ.get('LEAD_TIME_CHINA') or 60)
LEAD_TIME_LOCAL = int(os.environ.get('LEAD_TIME_LOCAL') or 21)


def _compute_mp_deficit_aggregated(conn, days_ahead=90):
    """Calcula déficit REAL de MPs agregando primero, restando stock una sola vez.

    Esta es la lógica correcta — agrupa todas las producciones planificadas
    (calendario + DB local), suma cuánto se necesita por MP, y resta el stock
    actual UNA vez para obtener el déficit real.

    El bug que esto fixea: si calculas deficit per-product y sumas, cuando hay
    stock parcial cada producto "ve" el mismo stock disponible y under-cuentas
    el déficit total. Ej: A pide 3g, B pide 5g, stock=4g → A: déf=0, B: déf=1,
    suma=1g. Real: 3+5-4 = 4g. La suma per-product subestima en 3g.

    Returns dict {material_id: {nombre, total_g, stock_g, deficit_g, productos,
                                proveedor, por_mes, n_meses}}.
    Solo incluye MPs con deficit_g > 0. MPs ilimitados (agua, etc.) excluidos.
    """
    import datetime as _dt
    import re as _re

    cal = _fetch_calendar_events(days_ahead=days_ahead)
    events = cal.get('events', [])
    formulas = _get_formulas(conn)
    mp_stock = _get_mp_stock(conn)
    if not formulas:
        return {}

    # SKU → producto map
    _sku_to_prod = {}
    try:
        for row in conn.execute(
            "SELECT UPPER(sku), producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            _sku_to_prod[row[0]] = row[1]
    except Exception:
        pass

    # Proveedor por MP
    _prov_map = {}
    try:
        for row in conn.execute(
            "SELECT codigo_mp, COALESCE(proveedor,'') FROM maestro_mps"
        ).fetchall():
            _prov_map[row[0]] = row[1]
    except Exception:
        pass

    today = _dt.date.today()
    cutoff = today + _dt.timedelta(days=days_ahead)

    # Tokens que no son SKUs en títulos del calendario
    _NOT_SKU = {
        'FAB','QC','CON','SIN','MICRO','ENVASADO','ACONDICIONAMIENTO',
        'FABRICACION','FABRICACIÓN','LANZAMIENTO','PRODUCCION','PRODUCCIÓN',
        'KG','MES','DIAS','DÍAS','ML','UDS','BATCH','FERNANDO',
        'MESA','LOTES','LOTE','MINI','MACRO','AND','THE','FOR'
    }

    def _skus(titulo):
        tokens = _re.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in _NOT_SKU]

    def _kg_ev(titulo):
        m = _re.findall(r'~?(\d+(?:[,.]\d+)*)\s*kg', titulo, _re.IGNORECASE)
        if not m:
            return None
        try:
            return float(m[-1].replace(',', '.'))
        except Exception:
            return None

    # Filtro: ignorar fases que NO consumen MPs (envasado/acondicionamiento/QC)
    _NON_FAB_KW = {
        'envasado', 'acondicionamiento', 'micro qc', 'control de calidad',
        'dispensado', 'etiquetado', 'llenado',
    }

    producciones = []
    seen_events = set()

    # Calendario
    for ev in events:
        titulo = ev.get('titulo', '')
        fecha_s = ev.get('fecha', '')
        if not fecha_s:
            continue
        try:
            fecha = _dt.date.fromisoformat(fecha_s)
        except ValueError:
            continue
        if fecha < today or fecha > cutoff:
            continue
        if any(kw in titulo.lower() for kw in _NON_FAB_KW):
            continue
        key = (titulo.strip(), fecha_s)
        if key in seen_events:
            continue
        seen_events.add(key)
        kg = _kg_ev(titulo)
        for sku in _skus(titulo):
            prod = _sku_to_prod.get(sku)
            if prod and prod in formulas:
                producciones.append({
                    'fecha': fecha_s, 'mes': fecha.strftime('%Y-%m'),
                    'producto': prod, 'kg': kg or formulas[prod]['lote_size_kg'],
                })
                break

    # produccion_programada (DB local) — complementa el calendario
    _upper_to_prod = {p.upper(): p for p in formulas.keys()}
    try:
        local_rows = conn.execute(
            """SELECT producto, fecha_programada, lotes FROM produccion_programada
               WHERE estado NOT IN ('completado','cancelado')
                 AND fecha_programada >= date('now', '-7 days')
                 AND fecha_programada <= ?
               ORDER BY fecha_programada""",
            (cutoff.isoformat(),)
        ).fetchall()
        for row in local_rows:
            prod_raw = (row[0] or '').strip()
            fecha_s = (row[1] or '').strip()
            lotes = int(row[2] or 1)
            prod = prod_raw if prod_raw in formulas else _upper_to_prod.get(prod_raw.upper())
            if not prod or not fecha_s:
                continue
            key = (prod, fecha_s)
            if key in seen_events:
                continue
            seen_events.add(key)
            try:
                fecha = _dt.date.fromisoformat(fecha_s)
            except ValueError:
                continue
            lote_kg = formulas[prod]['lote_size_kg']
            producciones.append({
                'fecha': fecha_s, 'mes': fecha.strftime('%Y-%m'),
                'producto': prod, 'kg': lote_kg * lotes,
            })
    except Exception:
        pass

    # Agregar necesidad por MP a través de TODAS las producciones
    mp_needed = {}  # mid → {nombre, total_g, productos, por_mes}
    for pr in producciones:
        prod = pr['producto']
        kg_ev = pr['kg']
        formula = formulas.get(prod, {})
        lote_kg = formula.get('lote_size_kg', 1)
        factor = kg_ev / lote_kg if lote_kg > 0 else 1.0
        for item in formula.get('items', []):
            mid = str(item['material_id']).strip()
            nombre = item.get('material_nombre', '')
            g_lote = item.get('cantidad_g_por_lote', 0)
            g_need = float(g_lote) * factor
            if g_need <= 0 or not mid:
                continue
            if _is_unlimited_mp(nombre):
                continue
            if mid not in mp_needed:
                mp_needed[mid] = {
                    'nombre': nombre, 'total_g': 0.0,
                    'productos': [], 'por_mes': {},
                }
            mp_needed[mid]['total_g'] += g_need
            mp_needed[mid]['por_mes'][pr['mes']] = (
                mp_needed[mid]['por_mes'].get(pr['mes'], 0) + g_need
            )
            if prod not in mp_needed[mid]['productos']:
                mp_needed[mid]['productos'].append(prod)

    # Lookup stock por mid o por nombre normalizado
    def _lookup_stock(mid, nombre):
        s = mp_stock.get(mid)
        if s is not None:
            return s
        s = mp_stock.get(mid.upper())
        if s is not None:
            return s
        s = mp_stock.get((nombre or '').upper())
        if s is not None:
            return s
        s = mp_stock.get(_norm_mp_name(nombre or ''))
        if s is not None:
            return s
        return 0

    # Calcular déficit (UNA sola resta — total_g - stock)
    out = {}
    for mid, data in mp_needed.items():
        stock_g = _lookup_stock(mid, data['nombre'])
        deficit = max(0.0, data['total_g'] - stock_g)
        if deficit <= 0:
            continue
        out[mid] = {
            'material_id': mid,
            'nombre': data['nombre'],
            'total_g': round(data['total_g'], 1),
            'stock_g': round(stock_g, 1),
            'deficit_g': round(deficit, 1),
            'productos': data['productos'],
            'por_mes': data['por_mes'],
            'n_meses': len(data['por_mes']),
            'proveedor': _prov_map.get(mid, ''),
        }
    return out


def _project_stock(conn, prod_vel, formulas, mp_stock, calendar_events, china_mps=None):
    """
    Logica correcta de programacion:
    1. Stock PT real = producido (acondicionamiento) - vendido (Shopify)
    2. Vel diaria = vel_mes / 30
    3. Dias de cobertura = stock / vel_diaria
    4. Umbral ROJO < 20 dias, AMARILLO < 40 dias, VERDE >= 40 dias
    5. Validar calendario: hay produccion antes del dia critico?
    6. Validar MPs: alcanzan para un lote?
    7. Alertas de compra si faltan MPs o MEE
    """
    # Stock real de PT
    pt_stock = _get_stock_pt(conn)

    # Calendar: next production date per product
    # Priority: 1) local DB, 2) Google Calendar / iCal via SKU lookup
    products_with_formula = set(formulas.keys())
    next_prod_by_product = {}

    # 1. Local DB events — case-insensitive product name matching
    local_events = _fetch_local_production_events(conn)
    # Build uppercase lookup: UPPER(formula_name) -> original formula_name
    _upper_to_prod = {p.upper(): p for p in products_with_formula}
    for ev in local_events:
        prod_ev_raw = ev.get('titulo', '')
        # Try exact match first, then case-insensitive
        prod_key = prod_ev_raw if prod_ev_raw in products_with_formula             else _upper_to_prod.get(prod_ev_raw.upper())
        if prod_key and prod_key not in next_prod_by_product:
            fecha_ev = ev.get('fecha', '')
            next_prod_by_product[prod_key] = fecha_ev
            # Flag if the scheduled date is already past
            if ev.get('past_date'):
                next_prod_by_product[prod_key + '__past'] = True

    # 2. Google Calendar / iCal events — SKU-first matching
    # Event titles use SKU codes: 'GELH – Fabricacion' -> SKU=GELH -> GEL HIDRATANTE
    import re as _re_cal

    # Load sku -> producto_nombre map from DB
    _sku_to_prod = {}
    try:
        for row in conn.execute(
            "SELECT UPPER(sku), producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            _sku_to_prod[row[0]] = row[1]
    except Exception:
        pass

    # Non-SKU words that appear in event titles — never treat as product codes
    _NOT_SKU = {
        'FAB','QC','CON','SIN','MICRO','ENVASADO','ACONDICIONAMIENTO',
        'FABRICACION','FABRICACIÓN','LANZAMIENTO','PRODUCCION','PRODUCCIÓN',
        'KG','MES','DIAS','DÍAS','ML','UDS','SIN','CON','BATCH','Fernando',
        'MESA','LOTES','LOTE','MINI','MACRO','AND','THE','FOR'
    }

    def _skus_from_title(titulo):
        """Extract SKU candidates from a calendar event title."""
        # All uppercase tokens 2+ chars that are not generic words
        tokens = _re_cal.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in _NOT_SKU]

    next_prod_kg_by_product = {}  # product -> planned kg from calendar title

    def _kg_from_title(titulo):
        """Extract planned kg from calendar event title. Returns float or None."""
        # Match patterns like '50 kg', '~29 kg', '196 kg', '1,250 u / 50 kg'
        matches = _re_cal.findall(r'~?(\d+(?:[,.]\d+)*)\s*kg', titulo, _re_cal.IGNORECASE)
        if not matches:
            return None
        # Take the last match (avoids 'u' counts like '1,250 u / 50 kg')
        val = matches[-1].replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None

    _today_str = str(date.today())

    for ev in calendar_events:
        titulo  = ev.get('titulo', '')
        fecha_ev = ev.get('fecha', '')
        if not fecha_ev:
            continue
        # Skip past calendar events — always show next FUTURE production date
        if fecha_ev < _today_str:
            continue
        # Extract planned kg from title
        kg_ev = _kg_from_title(titulo)
        # Try each SKU extracted from title
        for sku in _skus_from_title(titulo):
            prod_name = _sku_to_prod.get(sku)
            if prod_name and prod_name in products_with_formula:
                # Assign earliest FUTURE date per product
                existing = next_prod_by_product.get(prod_name)
                if not existing or fecha_ev < existing:
                    next_prod_by_product[prod_name] = fecha_ev
                    if kg_ev:
                        next_prod_kg_by_product[prod_name] = kg_ev
                break

    today = date.today()

    projection = []
    all_alerts = []

    for prod, formula in sorted(formulas.items()):
        vel_mes = prod_vel.get(prod, 0)
        vel_dia = vel_mes / 30.0 if vel_mes > 0 else 0.0
        lote_kg = formula['lote_size_kg']
        items   = formula['items']

        # Stock actual PT en unidades
        stock_uds = pt_stock.get(prod.upper(), 0)

        # Dias de cobertura
        # CRITICAL fix: si vel_dia=0 Y stock_uds=0, NO marcar 999 (eso hace
        # cal_ok siempre true y oculta faltantes reales). Mejor None y tratar
        # explícitamente abajo.
        if vel_dia > 0:
            dias_cob = stock_uds / vel_dia
            tiene_datos = True
        elif stock_uds > 0:
            dias_cob = 999.0   # hay stock pero sin ventas = cobertura indefinida real
            tiene_datos = True
        else:
            dias_cob = 0.0     # sin stock y sin ventas → cobertura cero, dato dudoso
            tiene_datos = False

        # Produccion en calendario
        prox_prod = next_prod_by_product.get(prod, 'No programado')

        # Validar si la produccion calendario llega antes del dia critico.
        # Si no hay datos (sin stock ni ventas), no asumir que llega "a tiempo".
        cal_ok = False
        if prox_prod != 'No programado' and tiene_datos:
            try:
                prod_date = date.fromisoformat(prox_prod)
                dias_hasta_prod = (prod_date - today).days
                # cal_ok solo si hay velocidad real Y la prod llega antes del agotamiento
                cal_ok = vel_dia > 0 and dias_hasta_prod <= dias_cob
            except Exception:
                cal_ok = False

        # MP check: alcanza la MP para el lote del calendario?
        # Scale formula quantities by planned kg (from calendar) vs reference lot
        planned_kg = next_prod_kg_by_product.get(prod, lote_kg or 1.0)
        ref_kg     = lote_kg if lote_kg and lote_kg > 0 else planned_kg
        kg_scale   = planned_kg / ref_kg  # e.g. 50kg planned / 35kg ref = 1.43x

        mp_check = []
        can_produce = True        # False only if MP found-in-system but insufficient
        has_data_gap = False      # True if any MP not found in movimientos at all
        items_with_qty = [i for i in items if i.get('cantidad_g_por_lote', 0) > 0]
        if not items_with_qty:
            can_produce = None  # formula sin cantidades definidas
        else:
            for item in items_with_qty:
                mid = str(item['material_id']).strip()
                needed_g = float(item['cantidad_g_por_lote']) * kg_scale
                nombre_raw = str(item.get('material_nombre', '')).strip()
                # Lookup order: unlimited → id → exact name → norm name → alias → NOT_FOUND
                mp_found = True
                if _is_unlimited_mp(nombre_raw):
                    available_g = float('inf')
                elif mid in mp_stock:
                    available_g = mp_stock[mid]
                else:
                    nombre_exact = nombre_raw.upper()
                    if nombre_exact in mp_stock:
                        available_g = mp_stock[nombre_exact]
                    else:
                        nombre_norm = _norm_mp_name(nombre_raw)
                        if nombre_norm in mp_stock:
                            available_g = mp_stock[nombre_norm]
                        else:
                            alias_key = _MP_NAME_ALIAS.get(nombre_norm) or _MP_NAME_ALIAS.get(nombre_exact)
                            if alias_key and alias_key in mp_stock:
                                available_g = mp_stock[alias_key]
                            else:
                                available_g = 0
                                mp_found = False  # genuinely not in movimientos
                deficit_g = 0 if available_g == float('inf') else max(0, needed_g - available_g)
                ok = deficit_g < 1
                if not ok:
                    if mp_found:
                        can_produce = False  # confirmed deficit: found but insufficient
                    else:
                        has_data_gap = True  # data gap: not in movimientos, unknown stock
                mp_check.append({
                    'material_id': mid,
                    'nombre': item['material_nombre'],
                    'needed_g': round(needed_g, 1),
                    'available_g': '∞' if available_g == float('inf') else available_g,
                    'deficit_g': round(deficit_g, 1),
                    'ok': ok,
                    'mp_found': mp_found,
                })

        missing_mp = [m for m in mp_check if not m['ok']]

        # Semaforo basado en dias de cobertura
        if vel_dia > 0:
            if dias_cob < DIAS_CRITICOS:
                semaforo = 'rojo'
            elif dias_cob < DIAS_ALERTA:
                semaforo = 'amarillo'
            else:
                semaforo = 'verde'
        else:
            # Sin ventas: verde si hay stock, amarillo si no hay stock ni ventas
            semaforo = 'verde' if stock_uds > 0 else 'amarillo'

        # Alertas
        if dias_cob < DIAS_CRITICOS and vel_dia > 0:
            dias_str = str(int(dias_cob))
            vel_str = str(int(vel_mes))
            stock_str = str(stock_uds)
            all_alerts.append({
                'producto': prod,
                'nivel': 'critico',
                'tipo': 'cobertura_critica',
                'mensaje': ("Stock: " + stock_str + " uds | " +
                            dias_str + " dias cobertura | Vende " + vel_str + " uds/mes"),
            })

        if missing_mp and can_produce is False:
            n_str = str(len(missing_mp))
            names = ", ".join(m['nombre'] + " -" + str(int(m['deficit_g'])) + "g"
                              for m in missing_mp[:3])
            if len(missing_mp) > 3:
                names += " y " + str(len(missing_mp) - 3) + " mas"
            # Detectar si alguna MP faltante es de China (lead time 60d).
            # Si sí, escalar a CRITICO (no "alto") porque ya estás tarde.
            china_set = china_mps or set()
            mp_china_falta = [m for m in missing_mp
                              if str(m.get('material_id', '')).strip() in china_set]
            if mp_china_falta:
                china_names = ", ".join(m['nombre'] for m in mp_china_falta[:3])
                all_alerts.append({
                    'producto': prod,
                    'nivel': 'critico',
                    'tipo': 'mp_china_faltante',
                    'mensaje': (
                        f"URGENTE — MP de China sin stock: {china_names}. "
                        f"Lead time {LEAD_TIME_CHINA} días. Comprar HOY o se "
                        f"detiene la línea."
                    ),
                })
            all_alerts.append({
                'producto': prod,
                'nivel': 'alto',
                'tipo': 'mp_faltante',
                'mensaje': ("Faltan " + n_str + " MPs para producir: " + names),
            })

        # Alertas anticipadas: para MPs que SÍ tienen stock hoy pero el deficit
        # proyectado va a llegar antes que el lead time del proveedor.
        # Si una MP de China tiene cobertura proyectada < 60d, ya hay que pedir.
        if can_produce is not False and vel_dia > 0:
            china_set = china_mps or set()
            for m in mp_check:
                if not m.get('mp_found', True):
                    continue
                mid = str(m.get('material_id', '')).strip()
                avail = m.get('available_g')
                needed = m.get('needed_g', 0)
                if avail == '∞' or avail == float('inf') or needed <= 0:
                    continue
                # Cuántas producciones futuras puedo cubrir con la MP en stock
                if needed > 0:
                    producciones_cubiertas = float(avail or 0) / needed
                else:
                    continue
                # Días hasta agotamiento de ESA MP (asumiendo ritmo de prod actual)
                # Aproximación: vel_dia uds/día * needed_g/uds = consumo diario MP
                # Pero como needed_g viene del lote, normalizamos: días = avail / (consumo_diario)
                consumo_diario_g = (vel_dia * needed) / max(stock_uds or 1, 1) if stock_uds else 0
                if consumo_diario_g <= 0:
                    continue
                dias_mp = float(avail or 0) / consumo_diario_g
                lead = LEAD_TIME_CHINA if mid in china_set else LEAD_TIME_LOCAL
                if dias_mp < lead:
                    all_alerts.append({
                        'producto': prod,
                        'nivel': 'alto' if mid in china_set else 'medio',
                        'tipo': 'mp_anticipada_china' if mid in china_set else 'mp_anticipada',
                        'mensaje': (
                            f"PEDIR YA: {m['nombre']} dura ~{int(dias_mp)}d, "
                            f"lead time proveedor {lead}d "
                            f"({'China' if mid in china_set else 'local'})."
                        ),
                    })

        if dias_cob < DIAS_ALERTA and vel_dia > 0 and prox_prod == 'No programado':
            vel_str = str(int(vel_mes))
            all_alerts.append({
                'producto': prod,
                'nivel': 'medio',
                'tipo': 'sin_programar',
                'mensaje': ("Vende " + vel_str + " uds/mes y no tiene produccion en calendario"),
            })

        # Proyecciones de unidades faltantes para cubrir N dias
        # vel_dia = unidades vendidas/dia. necesarias_Nd = ceil(vel_dia * N).
        # faltante_Nd = max(0, necesarias_Nd - stock_uds)
        import math as _math
        def _faltante_uds(N):
            if vel_dia <= 0:
                return 0
            necesarias = _math.ceil(vel_dia * N)
            return max(0, necesarias - stock_uds)
        faltante_15d = _faltante_uds(15)
        faltante_30d = _faltante_uds(30)
        faltante_60d = _faltante_uds(60)

        projection.append({
            'producto': prod,
            'lote_kg': lote_kg,
            'vel_mes': round(vel_mes, 1),
            'vel_dia': round(vel_dia, 2),
            'stock_actual': stock_uds,
            'dias_cobertura': round(dias_cob, 0) if dias_cob < 999 else None,
            'faltante_uds_15d': faltante_15d,
            'faltante_uds_30d': faltante_30d,
            'faltante_uds_60d': faltante_60d,
            'prox_produccion': prox_prod,
            'prox_prod_pasada': bool(next_prod_by_product.get(prod + '__past')),
            'cal_ok': cal_ok,
            'mp_lista': can_produce,
            'mp_data_gap': has_data_gap,
            'n_mp_faltantes': len(missing_mp),
            'n_mp_sin_datos': len([m for m in mp_check if not m.get('mp_found', True)]),
            'semaforo': semaforo,
            'mp_check': mp_check,
        })

    order = {'rojo': 0, 'amarillo': 1, 'verde': 2}
    def _sort_key(x):
        sin_fecha = 1 if x['prox_produccion'] == 'No programado' else 0
        return (sin_fecha, order.get(x['semaforo'], 3), x['producto'])
    projection.sort(key=_sort_key)
    all_alerts.sort(key=lambda x: {'critico': 0, 'alto': 1, 'medio': 2}.get(x['nivel'], 3))

    return projection, all_alerts

# ─── Anthropic narrative ─────────────────────────────────────────────────────

# Proveedores China — lead time 60 dias
PROVEEDORES_CHINA = {'lyphar', 'yitibio'}

def _get_china_mps(conn):
    """Retorna set de material_id cuyo proveedor es chino (Lyphar, Yitibio)."""
    china = set()
    try:
        for row in conn.execute(
            "SELECT id, proveedor FROM maestro_mps WHERE proveedor IS NOT NULL"
        ).fetchall():
            prov = str(row[1] or '').lower().strip()
            if any(c in prov for c in PROVEEDORES_CHINA):
                china.add(str(row[0]).strip())
    except Exception:
        pass
    return china


def _generate_narrative(projection, alerts, vel_data, conn=None):
    """
    Analisis IA con horizonte 2 meses.
    Perspectiva: Espagiria recibe demanda de ANIMUS y debe garantizar produccion
    con 20 dias de anticipacion al agotamiento.
    MPs de Lyphar/Yitibio = China = 60 dias lead time.
    """
    if not ANTHROPIC_API_KEY:
        return None

    # Productos criticos (menos de 20 dias)
    criticos = [p for p in projection if p['semaforo'] == 'rojo' and p['vel_dia'] > 0]
    # Productos en alerta (20-40 dias)
    en_alerta = [p for p in projection if p['semaforo'] == 'amarillo' and p['vel_dia'] > 0]
    # MPs faltantes
    mp_faltantes_criticos = [a for a in alerts if a['tipo'] == 'mp_faltante']
    # Sin programar
    sin_programar = [a for a in alerts if a['tipo'] == 'sin_programar']

    # China MPs check
    china_mps = _get_china_mps(conn) if conn else set()
    china_alertas = []
    for p in projection:
        for mp in p.get('mp_check', []):
            if str(mp['material_id']) in china_mps and not mp['ok']:
                china_alertas.append(p['producto'] + ': ' + mp['nombre'] + ' (deficit ' + str(int(mp['deficit_g'])) + 'g de China)')

    # Build data block (no f-strings con chars especiales)
    lines = []
    lines.append('CONTEXTO EMPRESARIAL:')
    lines.append('- ANIMUS Lab: ecommerce que vende por Shopify')
    lines.append('- Espagiria: laboratorio maquila que produce para ANIMUS')
    lines.append('- Regla critica: producir 20 dias ANTES del agotamiento')
    lines.append('- MPs de China (Lyphar, Yitibio): lead time 60 dias — comprar con 2 meses de anticipacion')
    lines.append('')
    lines.append('ESTADO ACTUAL (horizonte 60 dias):')
    lines.append('- Productos criticos (<20 dias stock): ' + str(len(criticos)))
    for p in criticos[:4]:
        dc = str(int(p['dias_cobertura'])) if p['dias_cobertura'] else '?'
        lines.append('  * ' + p['producto'] + ': ' + dc + ' dias, vende ' + str(int(p['vel_mes'])) + ' uds/mes, cal=' + p['prox_produccion'])
    lines.append('- En alerta (20-40 dias): ' + str(len(en_alerta)))
    for p in en_alerta[:3]:
        dc = str(int(p['dias_cobertura'])) if p['dias_cobertura'] else '?'
        lines.append('  * ' + p['producto'] + ': ' + dc + ' dias')
    lines.append('- MPs faltantes para producir: ' + str(len(mp_faltantes_criticos)))
    if mp_faltantes_criticos:
        for a in mp_faltantes_criticos[:3]:
            lines.append('  * ' + a['producto'] + ': ' + a['mensaje'][:80])
    lines.append('- Sin programar en calendario: ' + str(len(sin_programar)))
    lines.append('- MPs de China con deficit: ' + str(len(china_alertas)))
    for ca in china_alertas[:3]:
        lines.append('  * ' + ca)
    lines.append('- Pedidos Shopify ultimos 60d: ' + str(vel_data.get('total_orders', 0)))

    lines.append('')
    lines.append('INSTRUCCION: Genera un analisis ejecutivo en espanol para Espagiria con:')
    lines.append('1. Cuales productos debe producir primero y por que (dias de cobertura)')
    lines.append('2. Que MPs comprar YA (especialmente China — deben pedirse hoy para tenerlos en 60 dias)')
    lines.append('3. Una accion concreta para los proximos 7 dias')
    lines.append('Tono: tecnico-operativo directo. Maximo 5 oraciones.')

    prompt = chr(10).join(lines)

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_API_KEY.strip(),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        return resp.get('content', [{}])[0].get('text', '')
    except urllib.error.HTTPError as e:
        body_err = e.read().decode('utf-8', errors='replace')[:200]
        return '[IA error ' + str(e.code) + ': ' + body_err + ']'
    except Exception as e:
        return '[IA no disponible: ' + str(e) + ']' 

# ─── Routes ──────────────────────────────────────────────────────────────────

@bp.route('/api/programacion/resumen')
def prog_resumen():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db()

    # 1. Shopify velocity
    vel_data = _shopify_velocity(conn, days=60)

    # 2. Calendar events
    cal = _fetch_calendar_events(days_ahead=90)

    # 3. MP stock
    mp_stock = _get_mp_stock(conn)

    # 4. Formulas
    formulas = _get_formulas(conn)

    if not formulas:
        return jsonify({
            'error': 'No hay fórmulas cargadas. Las fórmulas se cargan automáticamente al arrancar la app.',
            'formulas_count': 0,
        }), 200

    # 5. Project stock + alerts (pasamos china_mps para alertas anticipadas)
    china_mps_set = _get_china_mps(conn)
    projection, alerts = _project_stock(
        conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []),
        china_mps=china_mps_set
    )

    # 6. AI narrative (non-blocking)
    narrativa = None
    try:
        narrativa = _generate_narrative(projection, alerts, vel_data, conn=conn)
    except Exception:
        pass

    # Summary KPIs
    n_alertas = len([a for a in alerts if a['nivel'] in ('critico', 'alto')])
    total_vel = sum(vel_data['sku_velocity'].values())
    prox_prod_dates = sorted(
        [p['prox_produccion'] for p in projection if p['prox_produccion'] != 'No programado']
    )
    proxima = prox_prod_dates[0] if prox_prod_dates else 'Sin programar'

    # Warnings de integridad de datos (no son alertas operacionales)
    warnings_data = []
    try:
        collisions = _detect_alias_collisions(conn)
        if collisions:
            warnings_data.append({
                'tipo': 'alias_collision',
                'severidad': 'alta',
                'mensaje': (
                    f"{len(collisions)} grupo(s) de MPs con nombres distintos "
                    f"colapsan al mismo nombre normalizado. El alias map puede "
                    f"hacer que el stock de uno se atribuya al otro silenciosamente."
                ),
                'detalle': collisions[:10],
                'accion': "GET /api/programacion/diagnostico-alias para detalle completo",
            })
    except Exception as _e_w:
        logging.getLogger('programacion').error("warnings_data falló: %s", _e_w)
    if cal.get('error'):
        warnings_data.append({
            'tipo': 'calendar_error',
            'severidad': 'media',
            'mensaje': f"Calendario inaccesible: {cal['error']}",
            'accion': "Las próximas producciones pueden estar incompletas. Verifica GCAL_ICAL_URL o GOOGLE_API_KEY en env.",
        })
    # Warning si la velocidad de ventas viene de datos pobres
    dq = vel_data.get('data_quality', 'ok')
    if dq != 'ok':
        cov = vel_data.get('coverage_pct', 0)
        warnings_data.append({
            'tipo': 'velocidad_data_pobre',
            'severidad': 'alta' if dq in ('no_data', 'very_low') else 'media',
            'mensaje': (
                f"Velocidad de ventas calculada con datos insuficientes "
                f"(calidad={dq}, cobertura={cov}%). Las decisiones de "
                f"producción/compra basadas en esto pueden estar sesgadas."
            ),
            'accion': "Verifica el sync con Shopify (/api/programacion/test-shopify).",
        })
    # Fórmulas con cantidades incompletas
    formulas_incompletas = [
        p for p in projection
        if p.get('mp_lista') is None  # can_produce=None → fórmula sin cantidades
    ]
    if formulas_incompletas:
        warnings_data.append({
            'tipo': 'formulas_incompletas',
            'severidad': 'alta',
            'mensaje': (
                f"{len(formulas_incompletas)} fórmula(s) tienen cantidades vacías "
                f"o inválidas. La proyección de MPs para esos productos no es "
                f"confiable."
            ),
            'productos': [p['producto'] for p in formulas_incompletas[:10]],
            'accion': "Edita la fórmula en /tecnica y completa las cantidades por lote.",
        })

    return jsonify({
        'velocidad_total': round(total_vel, 0),
        'proxima_produccion': proxima,
        'n_alertas': n_alertas,
        'formulas_count': len(formulas),
        'mp_stock_count': len(mp_stock),
        'proyeccion': projection,
        'alertas': alerts,
        'velocidad': vel_data,
        'calendario': cal,
        'calendario_ok': cal.get('error') is None,
        'narrativa_ia': narrativa,
        'warnings_datos': warnings_data,
        'thresholds': {
            'dias_criticos': DIAS_CRITICOS,
            'dias_alerta': DIAS_ALERTA,
            'lead_time_china': LEAD_TIME_CHINA,
            'lead_time_local': LEAD_TIME_LOCAL,
        },
    })


@bp.route('/api/programacion/diagnostico-alias')
def prog_diagnostico_alias():
    """Lista colisiones del alias map: 2+ MPs con nombres distintos que
    normalizan al mismo nombre. Si aparecen, el stock de uno puede
    atribuirse silenciosamente al otro.
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    conn = get_db()
    collisions = _detect_alias_collisions(conn)
    return jsonify({
        'collisions': collisions,
        'count': len(collisions),
        'accion_sugerida': (
            "Para cada grupo, verifica que sean realmente la misma MP. Si lo son, "
            "estandariza el nombre en maestro_mps. Si NO son la misma, renombra "
            "una para que el normalizador no las colapse."
        ),
    })




@bp.route('/api/programacion/que-puedo-producir', methods=['GET'])
def prog_que_puedo_producir():
    """Para cada producto con formula, evalua si las MPs alcanzan para
    producir 1 lote estandar y devuelve faltantes detallados + shopping
    list por proveedor.

    Verificacion paso a paso (auditable):
      1. SOURCE: SELECT material_id, SUM(...) FROM movimientos
         (mismo query que el dashboard usa — kardex actual)
      2. FORMULA: SELECT FROM formula_items WHERE producto=?
         (los gramos requeridos por lote vienen de cantidad_g_por_lote)
      3. MATCH: para cada MP requerida, busca su stock por codigo_mp
         O por nombre (fallback) — incluye los lotes individuales como
         evidencia
      4. PROVEEDOR: cae al canonico de maestro_mps

    Cada MP en la respuesta trae:
      - requerido_g (de formula)
      - stock_actual_g (de kardex)
      - lotes_disponibles[]: evidencia auditable
      - falta_g (negativo => sobra; positivo => falta esa cantidad)
      - ok: true si stock >= requerido

    Producto.puede_producir = todas las MPs ok.
    Si falla, shopping_list agrupa por proveedor lo que hay que comprar.

    Query params:
      cantidad_kg_override: int (opcional) — simular un lote distinto
                            al estandar de la formula
      solo_faltantes: 1 — devuelve solo productos que NO se pueden producir
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db()
    c = conn.cursor()

    cantidad_kg_override = request.args.get('cantidad_kg_override', '').strip()
    try:
        cantidad_kg_override = float(cantidad_kg_override) if cantidad_kg_override else None
    except ValueError:
        cantidad_kg_override = None
    solo_faltantes = request.args.get('solo_faltantes', '0') in ('1', 'true', 'True')

    # Step 1: stock por material_id (canonical)
    mp_stock = _get_mp_stock(conn)

    # Step 2: lotes individuales por material_id (evidencia auditable)
    lotes_por_mp = {}
    try:
        rows = c.execute("""
            SELECT material_id, COALESCE(lote,''),
                   SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as neto,
                   MAX(fecha_vencimiento), MAX(proveedor)
            FROM movimientos
            WHERE material_id IS NOT NULL AND material_id != ''
            GROUP BY material_id, lote
            HAVING neto > 0
            ORDER BY material_id, fecha_vencimiento ASC
        """).fetchall()
        for r in rows:
            mid = (r[0] or '').strip()
            lotes_por_mp.setdefault(mid, []).append({
                'lote': r[1] or '',
                'cantidad_g': round(float(r[2] or 0), 1),
                'fecha_venc': str(r[3])[:10] if r[3] else '',
                'proveedor': r[4] or '',
            })
    except sqlite3.OperationalError:
        pass

    # Step 3: catalogo proveedor canonico
    cat_proveedor = {}
    try:
        for r in c.execute(
            "SELECT codigo_mp, COALESCE(proveedor,''), COALESCE(nombre_comercial,'') "
            "FROM maestro_mps"
        ).fetchall():
            cat_proveedor[r[0]] = {'proveedor': r[1], 'nombre': r[2]}
    except sqlite3.OperationalError:
        pass

    # Step 4: formulas
    formulas = _get_formulas(conn)

    productos = []
    for nombre_prod, info in formulas.items():
        items = info.get('items', [])
        if not items:
            continue
        lote_size_kg = info.get('lote_size_kg') or 0
        cantidad_kg = cantidad_kg_override if cantidad_kg_override else lote_size_kg
        if cantidad_kg <= 0:
            continue

        factor = cantidad_kg / lote_size_kg if lote_size_kg > 0 else 1
        mps_status = []
        falta_total_g = 0.0
        n_ok = 0
        n_falta = 0

        for it in items:
            mid = (it.get('material_id') or '').strip()
            req_g_estandar = float(it.get('cantidad_g_por_lote') or 0)
            req_g = round(req_g_estandar * factor, 2)

            # Stock por id; fallback a nombre si no existe id
            stock_g = mp_stock.get(mid, 0.0)
            if not mid:
                # Buscar por nombre canonical via mp_stock dict (which also indexes by name)
                stock_g = mp_stock.get((it.get('material_nombre') or '').upper().strip(), 0.0)

            falta_g = round(req_g - stock_g, 2)
            ok = stock_g >= req_g

            if ok:
                n_ok += 1
            else:
                n_falta += 1
                if falta_g > 0:
                    falta_total_g += falta_g

            cat_info = cat_proveedor.get(mid, {})
            mps_status.append({
                'codigo_mp': mid,
                'nombre': cat_info.get('nombre') or it.get('material_nombre') or mid,
                'requerido_g': req_g,
                'stock_actual_g': round(stock_g, 1),
                'falta_g': falta_g if falta_g > 0 else 0,
                'sobra_g': abs(falta_g) if falta_g < 0 else 0,
                'ok': ok,
                'lotes_disponibles': lotes_por_mp.get(mid, [])[:5],
                'proveedor_canonico': cat_info.get('proveedor', ''),
            })

        puede_producir = (n_falta == 0)

        if solo_faltantes and puede_producir:
            continue

        productos.append({
            'producto': nombre_prod,
            'lote_size_kg': lote_size_kg,
            'cantidad_kg_evaluada': cantidad_kg,
            'puede_producir': puede_producir,
            'mps_total': len(items),
            'mps_ok': n_ok,
            'mps_faltantes': n_falta,
            'falta_total_g': round(falta_total_g, 1),
            'mps_status': sorted(mps_status, key=lambda m: (m['ok'], -m['falta_g'])),
        })

    # Step 5: shopping list por proveedor
    shopping = {}
    for prod in productos:
        for m in prod['mps_status']:
            if not m['ok'] and m['falta_g'] > 0:
                prov = m['proveedor_canonico'] or '(sin proveedor)'
                bucket = shopping.setdefault(prov, {})
                k = m['codigo_mp']
                if k in bucket:
                    bucket[k]['falta_g'] = max(bucket[k]['falta_g'], m['falta_g'])
                    bucket[k]['productos_afectados'].add(prod['producto'])
                else:
                    bucket[k] = {
                        'codigo_mp': k, 'nombre': m['nombre'],
                        'falta_g': m['falta_g'],
                        'productos_afectados': {prod['producto']},
                    }
    shopping_list = []
    for prov, mps in sorted(shopping.items()):
        items_list = []
        total_g = 0.0
        for k, item in mps.items():
            items_list.append({
                'codigo_mp': item['codigo_mp'],
                'nombre': item['nombre'],
                'falta_g': round(item['falta_g'], 1),
                'productos_afectados': sorted(item['productos_afectados']),
            })
            total_g += item['falta_g']
        items_list.sort(key=lambda x: -x['falta_g'])
        shopping_list.append({
            'proveedor': prov,
            'count_mps': len(items_list),
            'total_g_a_pedir': round(total_g, 1),
            'mps': items_list,
        })
    shopping_list.sort(key=lambda s: -s['total_g_a_pedir'])

    productos.sort(key=lambda p: (p['puede_producir'], -p['falta_total_g']))

    # KPIs resumen
    n_total = len(productos)
    n_pueden = sum(1 for p in productos if p['puede_producir'])
    n_no_pueden = n_total - n_pueden

    return jsonify({
        'ok': True,
        'fecha': __import__('datetime').date.today().isoformat(),
        'fuente_datos': {
            'kardex': '/api/movimientos (SUM signed por material_id)',
            'formulas': 'formula_items.cantidad_g_por_lote escalado a cantidad_kg',
            'proveedor_canonico': 'maestro_mps.proveedor',
        },
        'resumen': {
            'productos_totales': n_total,
            'productos_pueden_producir': n_pueden,
            'productos_con_faltantes': n_no_pueden,
            'cantidad_kg_override_usada': cantidad_kg_override,
        },
        'productos': productos,
        'shopping_list_por_proveedor': shopping_list,
    })


@bp.route('/api/programacion/registrar-stock', methods=['POST'])
def prog_registrar_stock():
    """Registra stock inicial de PT directamente en stock_pt."""
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    d = request.get_json(force=True) or {}
    sku      = str(d.get('sku', '') or '').strip().upper()
    producto = str(d.get('producto', '') or '').strip()
    unidades = int(d.get('unidades', 0) or 0)
    lote     = str(d.get('lote', 'INI-' + datetime.now().strftime('%Y%m%d')) or '')

    if not sku or not producto or unidades <= 0:
        return jsonify({'error': 'sku, producto y unidades requeridos (unidades > 0)'}), 400

    conn = get_db()
    # Invalidate previous carga-inicial entries for same sku to avoid duplicates
    conn.execute(
        "UPDATE stock_pt SET estado='Ajustado' WHERE sku=? AND lote_produccion LIKE 'INI-%'",
        (sku,)
    )
    conn.execute("""
        INSERT INTO stock_pt
            (sku, descripcion, lote_produccion, fecha_produccion,
             unidades_inicial, unidades_disponible, precio_base,
             empresa, estado, observaciones)
        VALUES (?,?,?,date('now'),?,?,0,'ANIMUS','Disponible','Carga inicial de stock')
    """, (sku, producto, lote, unidades, unidades))
    conn.commit()
    return jsonify({'ok': True, 'sku': sku, 'producto': producto, 'unidades': unidades})



@bp.route('/api/programacion/test-shopify')
def prog_test_shopify():
    """GET publico — diagnostico: verifica credenciales y cuenta productos Shopify."""
    try:
        conn = get_db()
        def _cfg(c):
            r = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (c,)).fetchone()
            return r[0] if r else None
        token = _cfg('shopify_token')
        shop  = _cfg('shopify_shop')
        if not token or not shop:
            return jsonify({'ok': False, 'paso': 'credenciales', 'error': 'shopify_token o shopify_shop no configurados en animus_config'})
        url = 'https://' + shop + '/admin/api/2024-01/products/count.json'
        req = urllib.request.Request(url, headers={'X-Shopify-Access-Token': token})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return jsonify({'ok': True, 'shop': shop, 'count': data.get('count', '?'), 'token_prefix': token[:8] + '...'})
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:400]
        return jsonify({'ok': False, 'paso': 'shopify_api', 'http_status': e.code, 'body': body})
    except Exception as e:
        return jsonify({'ok': False, 'paso': 'exception', 'error': str(e)})



@bp.route('/api/programacion/sync-ventas', methods=['POST'])
def prog_sync_ventas():
    """Sincroniza ordenes Shopify directamente — independiente de marketing."""
    try:
        days = int(request.json.get('days', 60)) if request.json else 60
        conn = get_db()
        result = _sync_shopify_orders(conn, days=days)
        if result['ok']:
            return jsonify({
                'ok': True,
                'synced': result['synced'],
                'mensaje': str(result['synced']) + ' ordenes sincronizadas (' + str(days) + 'd)'
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()[-500:]})

@bp.route('/api/programacion/sync-stock-shopify', methods=['POST'])
def prog_sync_stock_shopify():
    """
    Sincroniza inventario desde Shopify products API a stock_pt.
    No requiere auth — usa credenciales server-side de animus_config.
    Siempre retorna JSON; nunca lanza 500 HTML.
    """
    try:
        conn = get_db()

        def _cfg(c):
            r = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (c,)).fetchone()
            return r[0] if r else None

        token = _cfg('shopify_token')
        shop  = _cfg('shopify_shop')
        if not token or not shop:
            return jsonify({'ok': False, 'error': 'Shopify no configurado. Ve a ANIMUS > Configuracion y guarda shopify_token y shopify_shop.'})

        sku_map = {}
        for row in conn.execute("SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1").fetchall():
            sku_map[str(row[0] or '').strip().upper()] = str(row[1] or '').strip()

        all_variants = []
        url = 'https://' + shop + '/admin/api/2024-01/products.json?limit=250&fields=id,title,variants'
        while url:
            req = urllib.request.Request(url, headers={'X-Shopify-Access-Token': token})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read())
                    link_header = r.headers.get('Link', '')
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')[:300]
                return jsonify({'ok': False, 'error': 'Shopify HTTP ' + str(e.code) + ' — ' + body + ' | Verifica que el token tenga scope read_products.'})
            except Exception as e:
                return jsonify({'ok': False, 'error': 'Error red Shopify: ' + str(e)})

            for product in data.get('products', []):
                title = str(product.get('title', '') or '').strip()
                for variant in product.get('variants', []):
                    sku_raw = str(variant.get('sku', '') or '').strip().upper()
                    inv_qty = int(variant.get('inventory_quantity', 0) or 0)
                    all_variants.append({'sku': sku_raw, 'titulo': title, 'inv_qty': inv_qty})

            next_url = None
            for part in link_header.split(','):
                if 'rel="next"' in part:
                    s = part.find('<') + 1
                    e2 = part.find('>')
                    if s > 0 and e2 > s:
                        next_url = part[s:e2].strip()
            url = next_url

        if not all_variants:
            return jsonify({'ok': False, 'error': 'Shopify no devolvio productos. Tienda sin productos o token sin permiso read_products.'})

        conn.execute("UPDATE stock_pt SET estado='Ajustado' WHERE lote_produccion LIKE 'SHOPIFY-%'")
        synced = 0
        skipped = 0
        today = datetime.now().strftime('%Y-%m-%d')

        for v in all_variants:
            sku = v['sku']
            qty = v['inv_qty']
            if qty <= 0:
                skipped += 1
                continue
            producto = sku_map.get(sku)
            if not producto:
                prefix = sku.split('-')[0] if '-' in sku else sku[:6]
                producto = sku_map.get(prefix) or v['titulo']
            conn.execute(
                "INSERT INTO stock_pt (sku,descripcion,lote_produccion,fecha_produccion,unidades_inicial,unidades_disponible,precio_base,empresa,estado,observaciones) VALUES (?,?,?,?,?,?,0,'ANIMUS','Disponible','Sync Shopify')",
                (sku, producto, 'SHOPIFY-' + today, today, qty, qty)
            )
            synced += 1

        conn.commit()
        return jsonify({
            'ok': True,
            'synced': synced,
            'skipped_zero': skipped,
            'total_variantes': len(all_variants),
            'mensaje': str(synced) + ' SKUs sincronizados desde Shopify',
        })

    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': 'Error interno: ' + str(e), 'trace': traceback.format_exc()[-500:]})


@bp.route('/api/programacion/debug-stock')
def prog_debug_stock():
    """Debug publico: muestra stock_pt raw, sku_map y stock calculado por producto."""
    conn = get_db()

    # Raw stock_pt
    try:
        raw_pt = conn.execute(
            "SELECT sku, descripcion, unidades_disponible, estado, lote_produccion FROM stock_pt ORDER BY sku"
        ).fetchall()
        raw_pt_list = [{'sku': r[0], 'desc': r[1], 'uds': r[2], 'estado': r[3], 'lote': r[4]} for r in raw_pt]
    except Exception as e:
        raw_pt_list = [{'error': str(e)}]

    # SKU map
    try:
        sku_map_rows = conn.execute("SELECT sku, producto_nombre, activo FROM sku_producto_map").fetchall()
        sku_map_list = [{'sku': r[0], 'producto': r[1], 'activo': r[2]} for r in sku_map_rows]
    except Exception as e:
        sku_map_list = [{'error': str(e)}]

    # Acondicionamiento summary
    try:
        acon = conn.execute(
            "SELECT producto, estado, SUM(unidades_producidas) FROM acondicionamiento GROUP BY producto, estado"
        ).fetchall()
        acon_list = [{'producto': r[0], 'estado': r[1], 'uds': r[2]} for r in acon]
    except Exception as e:
        acon_list = [{'error': str(e)}]

    # Calculated stock
    stock_calc = _get_stock_pt(conn)

    # Formula headers product names
    try:
        fh = conn.execute('SELECT producto_nombre, lote_size_kg FROM formula_headers ORDER BY producto_nombre').fetchall()
        fh_list = [{'producto': r[0], 'lote_kg': r[1]} for r in fh]
    except Exception as e:
        fh_list = [{'error': str(e)}]

    return jsonify({
        'formula_headers': fh_list,
        'stock_pt_raw': raw_pt_list,
        'sku_producto_map': sku_map_list,
        'acondicionamiento': acon_list,
        'stock_calculado': stock_calc,
    })


@bp.route('/api/programacion/velocidad')
def prog_velocidad():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    days = int(request.args.get('days', 60))
    conn = get_db()
    return jsonify(_shopify_velocity(conn, days=days))


@bp.route('/api/programacion/debug-ventas')
def prog_debug_ventas():
    # Diagnostico completo: datos crudos de animus_shopify_orders
    conn = get_db()
    meta = conn.execute(
        "SELECT COUNT(*), MIN(creado_en), MAX(creado_en) FROM animus_shopify_orders"
    ).fetchone()
    since = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    rows_60 = conn.execute(
        "SELECT COUNT(*) FROM animus_shopify_orders WHERE creado_en >= ?", (since,)
    ).fetchone()[0]
    samples = conn.execute(
        "SELECT shopify_id, creado_en, sku_items, unidades_total FROM animus_shopify_orders WHERE creado_en >= ? AND sku_items IS NOT NULL ORDER BY creado_en DESC LIMIT 5",
        (since,)
    ).fetchall()
    sample_list = [{'id': r[0], 'fecha': r[1], 'sku_items': r[2], 'uds': r[3]} for r in samples]
    vel = _shopify_velocity(conn, days=60)
    return jsonify({
        'ordenes_total_tabla': meta[0],
        'fecha_min': meta[1],
        'fecha_max': meta[2],
        'ordenes_ultimos_60d': rows_60,
        'muestra_reciente': sample_list,
        'sku_velocity': vel['sku_velocity'],
        'prod_velocity': vel['prod_velocity'],
        'meses_analizados': vel['months_analyzed'],
    })



# ─── Producción programada (local calendar) ────────────────────────────────

@bp.route('/api/programacion/programar', methods=['GET'])
def prog_listar_eventos():
    """List all future production events.

    Enriquecido (30-abr-2026): incluye sala asignada + operarios por fase
    para que el modal de programar producto y otras vistas muestren el
    estado de asignacion sin pegarle a otro endpoint.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes, pp.estado,
               pp.observaciones, pp.creado_en,
               pp.area_id, ap.nombre as area_nombre, ap.codigo as area_codigo,
               od.nombre || ' ' || COALESCE(od.apellido,'')  as op_disp,
               oe.nombre || ' ' || COALESCE(oe.apellido,'')  as op_elab,
               oen.nombre || ' ' || COALESCE(oen.apellido,'') as op_env,
               oa.nombre || ' ' || COALESCE(oa.apellido,'')  as op_acon
        FROM produccion_programada pp
        LEFT JOIN areas_planta ap     ON ap.id  = pp.area_id
        LEFT JOIN operarios_planta od  ON od.id  = pp.operario_dispensacion_id
        LEFT JOIN operarios_planta oe  ON oe.id  = pp.operario_elaboracion_id
        LEFT JOIN operarios_planta oen ON oen.id = pp.operario_envasado_id
        LEFT JOIN operarios_planta oa  ON oa.id  = pp.operario_acondicionamiento_id
        ORDER BY pp.fecha_programada
    """).fetchall()
    return jsonify([{
        'id': r[0], 'producto': r[1], 'fecha': r[2],
        'lotes': r[3], 'estado': r[4], 'observaciones': r[5], 'creado_en': r[6],
        'area_id': r[7], 'area_nombre': r[8], 'area_codigo': r[9],
        'operario_dispensacion':      (r[10] or '').strip() or None,
        'operario_elaboracion':       (r[11] or '').strip() or None,
        'operario_envasado':          (r[12] or '').strip() or None,
        'operario_acondicionamiento': (r[13] or '').strip() or None,
    } for r in rows])


@bp.route('/api/programacion/programar', methods=['POST'])
def prog_crear_evento():
    """Create a production event."""
    data = request.get_json(force=True, silent=True) or {}
    producto = (data.get('producto') or '').strip()
    fecha    = (data.get('fecha') or '').strip()
    lotes    = int(data.get('lotes') or 1)
    obs      = (data.get('observaciones') or '').strip()

    if not producto or not fecha:
        return jsonify({'ok': False, 'error': 'producto y fecha son requeridos'}), 400

    # Validate date format
    try:
        import datetime as _dt2
        _dt2.date.fromisoformat(fecha)
    except ValueError:
        return jsonify({'ok': False, 'error': 'fecha inválida (use YYYY-MM-DD)'}), 400

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO produccion_programada (producto, fecha_programada, lotes, observaciones)
           VALUES (?, ?, ?, ?)""",
        (producto, fecha, max(1, lotes), obs)
    )
    conn.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid, 'producto': producto, 'fecha': fecha})


@bp.route('/api/programacion/programar/<int:evento_id>', methods=['DELETE'])
def prog_cancelar_evento(evento_id):
    """Cancel a scheduled production event."""
    conn = get_db()
    conn.execute(
        "UPDATE produccion_programada SET estado='cancelado' WHERE id=?",
        (evento_id,)
    )
    conn.commit()
    return jsonify({'ok': True, 'id': evento_id})


# ─── Planta: catalogo areas + operarios + asignacion (Capa 2) ──────────────
# Sebastian (30-abr-2026): asignar sala fisica + operario por fase a cada
# produccion. Mayerlin fija dispensacion (regla dura). Las salas tienen
# capacidades distintas post-INVIMA (ver migracion 55).

@bp.route('/api/planta/areas', methods=['GET'])
def planta_listar_areas():
    """Lista las 5 salas con capacidades y disponibilidad opcional por fecha.

    Query params:
        fecha: YYYY-MM-DD opcional. Si viene, agrega ocupada_por con la
               produccion que tiene asignada esa sala en esa fecha.
        requiere_marmita_ml: opcional. Si viene, marca solo las que tengan
                             marmita >= ese tamano.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    fecha = (request.args.get('fecha') or '').strip()
    req_marmita = request.args.get('requiere_marmita_ml')
    try:
        req_marmita = int(req_marmita) if req_marmita else None
    except (TypeError, ValueError):
        req_marmita = None

    conn = get_db()
    rows = conn.execute("""
        SELECT id, codigo, nombre, puede_producir, puede_envasar,
               marmita_ml, especial, estado, orden
        FROM areas_planta
        WHERE activo=1
        ORDER BY orden, id
    """).fetchall()

    # Si dieron fecha, calcular ocupacion de cada sala ese dia
    ocupacion = {}
    if fecha:
        try:
            date.fromisoformat(fecha)
            for r in conn.execute("""
                SELECT pp.area_id, pp.id, pp.producto, pp.lotes,
                       COALESCE(pp.lotes,1)*COALESCE(fh.lote_size_kg,0) as kg
                FROM produccion_programada pp
                LEFT JOIN formula_headers fh
                    ON UPPER(TRIM(fh.producto_nombre))=UPPER(TRIM(pp.producto))
                WHERE pp.fecha_programada=?
                  AND pp.area_id IS NOT NULL
                  AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
            """, (fecha,)):
                ocupacion.setdefault(r[0], []).append({
                    'produccion_id': r[1], 'producto': r[2],
                    'lotes': r[3], 'kg': r[4],
                })
        except ValueError:
            pass

    out = []
    for r in rows:
        area = {
            'id': r[0], 'codigo': r[1], 'nombre': r[2],
            'puede_producir': bool(r[3]), 'puede_envasar': bool(r[4]),
            'marmita_ml': r[5], 'especial': r[6],
            'estado': r[7], 'orden': r[8],
        }
        ocup = ocupacion.get(r[0], [])
        area['ocupada_por'] = ocup
        area['libre_en_fecha'] = (len(ocup) == 0) if fecha else None
        if req_marmita is not None:
            area['cumple_marmita'] = (r[5] is not None and r[5] >= req_marmita)
        out.append(area)
    return jsonify({'areas': out, 'fecha': fecha or None})


@bp.route('/api/planta/areas/<int:area_id>/estado', methods=['PATCH'])
def planta_actualizar_estado_area(area_id):
    """Cambia el estado de una sala: libre / ocupada / sucia / limpiando.
    Lo usa quien marca que la senora del aseo ya termino, o que una sala
    quedo sucia despues de produccion."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(force=True, silent=True) or {}
    nuevo = (data.get('estado') or '').strip().lower()
    if nuevo not in ('libre', 'ocupada', 'sucia', 'limpiando'):
        return jsonify({'error': 'estado invalido'}), 400
    conn = get_db()
    cur = conn.execute(
        "UPDATE areas_planta SET estado=? WHERE id=? AND activo=1",
        (nuevo, area_id)
    )
    conn.commit()
    if cur.rowcount == 0:
        return jsonify({'error': 'sala no encontrada'}), 404
    return jsonify({'ok': True, 'id': area_id, 'estado': nuevo})


@bp.route('/api/planta/operarios', methods=['GET', 'POST'])
def planta_listar_operarios():
    """GET: lista crew activo (Mayerlin fija dispensación, Luis Enrique jefe).
    POST: crea un nuevo operario. Solo admin (sebastian/alejandro).

    Body POST:
      nombre (req), apellido, rol_predeterminado (todero/envasado/
      acondicionamiento/dispensacion/jefe), fija_en_dispensacion (bool),
      es_jefe_produccion (bool).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = (session.get('compras_user') or '').lower()
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        try:
            from blueprints.compras import ADMIN_USERS as _ADMIN
        except Exception:
            _ADMIN = ('sebastian', 'alejandro')
        if user not in {u.lower() for u in _ADMIN}:
            return jsonify({'error': 'Solo admin crea operarios'}), 403
        d = request.get_json(force=True, silent=True) or {}
        nombre = (d.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'nombre requerido'}), 400
        rol = (d.get('rol_predeterminado') or 'todero').strip().lower()
        if rol not in ('dispensacion', 'envasado', 'acondicionamiento', 'todero', 'jefe'):
            rol = 'todero'
        fija = 1 if d.get('fija_en_dispensacion') else 0
        jefe = 1 if d.get('es_jefe_produccion') else 0
        c.execute("""INSERT INTO operarios_planta
            (nombre, apellido, rol_predeterminado, fija_en_dispensacion, es_jefe_produccion, activo)
            VALUES (?,?,?,?,?,1)""",
            (nombre, (d.get('apellido') or '').strip() or None, rol, fija, jefe))
        conn.commit()
        return jsonify({'ok': True, 'id': c.lastrowid}), 201

    # GET: incluir tambien inactivos si admin lo pide via ?incluir_inactivos=1
    incluir = request.args.get('incluir_inactivos') == '1'
    sql = """SELECT id, nombre, apellido, rol_predeterminado,
                    fija_en_dispensacion, es_jefe_produccion, activo
             FROM operarios_planta"""
    if not incluir:
        sql += " WHERE activo=1"
    sql += " ORDER BY activo DESC, es_jefe_produccion DESC, fija_en_dispensacion DESC, nombre"
    rows = c.execute(sql).fetchall()
    out = [{
        'id': r[0],
        'nombre': r[1],
        'apellido': r[2] or '',
        'nombre_completo': (r[1] + ' ' + (r[2] or '')).strip(),
        'rol': r[3] or '',
        'fija_dispensacion': bool(r[4]),
        'es_jefe': bool(r[5]),
        'activo': bool(r[6]),
    } for r in rows]
    return jsonify({'operarios': out, 'total': len(out)})


@bp.route('/api/planta/operarios/<int:op_id>', methods=['PATCH', 'DELETE'])
def planta_actualizar_operario(op_id):
    """PATCH: edita campos del operario (nombre, apellido, rol, flags).
    DELETE: soft delete — marca activo=0 (no borra historial de producciones).
    Solo admin."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = (session.get('compras_user') or '').lower()
    try:
        from blueprints.compras import ADMIN_USERS as _ADMIN
    except Exception:
        _ADMIN = ('sebastian', 'alejandro')
    if user not in {u.lower() for u in _ADMIN}:
        return jsonify({'error': 'Solo admin edita operarios'}), 403
    conn = get_db(); c = conn.cursor()

    if request.method == 'DELETE':
        cur = c.execute("UPDATE operarios_planta SET activo=0 WHERE id=?", (op_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'no encontrado'}), 404
        return jsonify({'ok': True, 'id': op_id, 'desactivado': True})

    # PATCH
    d = request.get_json(force=True, silent=True) or {}
    sets = []; params = []
    if 'nombre' in d:
        n = (d['nombre'] or '').strip()
        if not n: return jsonify({'error': 'nombre vacio'}), 400
        sets.append('nombre=?'); params.append(n)
    if 'apellido' in d:
        sets.append('apellido=?'); params.append((d['apellido'] or '').strip() or None)
    if 'rol_predeterminado' in d:
        rol = (d['rol_predeterminado'] or 'todero').strip().lower()
        if rol not in ('dispensacion','envasado','acondicionamiento','todero','jefe'):
            rol = 'todero'
        sets.append('rol_predeterminado=?'); params.append(rol)
    if 'fija_en_dispensacion' in d:
        sets.append('fija_en_dispensacion=?'); params.append(1 if d['fija_en_dispensacion'] else 0)
    if 'es_jefe_produccion' in d:
        sets.append('es_jefe_produccion=?'); params.append(1 if d['es_jefe_produccion'] else 0)
    if 'activo' in d:
        sets.append('activo=?'); params.append(1 if d['activo'] else 0)
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(op_id)
    cur = c.execute(f"UPDATE operarios_planta SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()
    if cur.rowcount == 0:
        return jsonify({'error': 'no encontrado'}), 404
    return jsonify({'ok': True, 'id': op_id})


@bp.route('/api/programacion/programar/<int:evento_id>/asignar', methods=['PATCH'])
def prog_asignar_sala_operarios(evento_id):
    """Asigna sala fisica y operarios por fase a una produccion programada.

    Body JSON (todo opcional, NULL para desasignar):
        area_id: int
        operario_dispensacion_id: int
        operario_elaboracion_id: int
        operario_envasado_id: int
        operario_acondicionamiento_id: int

    Valida que:
    - La sala exista y este activa.
    - Si se asigna sala que NO produce y la produccion implica producir → 400.
    - Conflicto: si OTRA produccion ya tomo esa sala ese dia → warning en
      la respuesta (no bloquea — Sebastian decide).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()

    # Verificar que la produccion existe
    pp = c.execute(
        "SELECT id, producto, fecha_programada, area_id FROM produccion_programada WHERE id=?",
        (evento_id,)
    ).fetchone()
    if not pp:
        return jsonify({'error': 'produccion no encontrada'}), 404

    updates = []
    params = []
    warnings = []

    # Sala
    if 'area_id' in data:
        new_area = data['area_id']
        if new_area is not None:
            try:
                new_area = int(new_area)
            except (TypeError, ValueError):
                return jsonify({'error': 'area_id invalido'}), 400
            sala = c.execute(
                "SELECT id, nombre, puede_producir FROM areas_planta WHERE id=? AND activo=1",
                (new_area,)
            ).fetchone()
            if not sala:
                return jsonify({'error': 'sala no existe o inactiva'}), 400
            # Conflicto: misma fecha, sala ya tomada por otra produccion
            conflictos = c.execute("""
                SELECT id, producto FROM produccion_programada
                WHERE fecha_programada=? AND area_id=? AND id<>?
                  AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
            """, (pp[2], new_area, evento_id)).fetchall()
            if conflictos:
                warnings.append({
                    'tipo': 'sala_ocupada',
                    'sala': sala[1],
                    'fecha': pp[2],
                    'choca_con': [{'id': x[0], 'producto': x[1]} for x in conflictos],
                })
        updates.append('area_id=?'); params.append(new_area)

    # Operarios por fase
    for campo in ('operario_dispensacion_id', 'operario_elaboracion_id',
                  'operario_envasado_id', 'operario_acondicionamiento_id'):
        if campo in data:
            val = data[campo]
            if val is not None:
                try:
                    val = int(val)
                except (TypeError, ValueError):
                    return jsonify({'error': f'{campo} invalido'}), 400
                op = c.execute(
                    "SELECT id, nombre FROM operarios_planta WHERE id=? AND activo=1",
                    (val,)
                ).fetchone()
                if not op:
                    return jsonify({'error': f'{campo}: operario no existe'}), 400
            updates.append(f'{campo}=?'); params.append(val)

    if not updates:
        return jsonify({'error': 'nada que actualizar'}), 400

    params.append(evento_id)
    c.execute(
        f"UPDATE produccion_programada SET {', '.join(updates)} WHERE id=?",
        params
    )
    conn.commit()
    return jsonify({'ok': True, 'id': evento_id, 'warnings': warnings})


@bp.route('/api/planta/operarios/historial', methods=['GET'])
def planta_historial_operarios():
    """Devuelve cuantos dias lleva cada operario en cada fase, ultimos 14 dias.
    Sirve para sugerir rotacion: si Camilo lleva 5 dias en acondicionamiento,
    el UI lo marca con un badge 'rotar'. Mayerlin se excluye (es fija)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    # Cuenta apariciones por operario+fase en producciones de los ultimos 14 dias
    sql = """
        SELECT op.id, op.nombre, op.apellido, fase, COUNT(*) as veces
        FROM operarios_planta op
        LEFT JOIN (
            SELECT operario_dispensacion_id as op_id, 'dispensacion' as fase, fecha_programada
              FROM produccion_programada
              WHERE operario_dispensacion_id IS NOT NULL
                AND fecha_programada >= date('now','-14 day')
                AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado')
            UNION ALL
            SELECT operario_elaboracion_id, 'elaboracion', fecha_programada
              FROM produccion_programada
              WHERE operario_elaboracion_id IS NOT NULL
                AND fecha_programada >= date('now','-14 day')
                AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado')
            UNION ALL
            SELECT operario_envasado_id, 'envasado', fecha_programada
              FROM produccion_programada
              WHERE operario_envasado_id IS NOT NULL
                AND fecha_programada >= date('now','-14 day')
                AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado')
            UNION ALL
            SELECT operario_acondicionamiento_id, 'acondicionamiento', fecha_programada
              FROM produccion_programada
              WHERE operario_acondicionamiento_id IS NOT NULL
                AND fecha_programada >= date('now','-14 day')
                AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado')
        ) hist ON hist.op_id = op.id
        WHERE op.activo=1 AND op.es_jefe_produccion=0
        GROUP BY op.id, fase
        ORDER BY op.nombre, fase
    """
    raw = conn.execute(sql).fetchall()
    # Reformatear: { op_id: {nombre, fija, fases: {fase: count}} }
    result = {}
    for r in raw:
        op_id, nombre, apellido, fase, veces = r
        if op_id not in result:
            result[op_id] = {
                'id': op_id, 'nombre': nombre, 'apellido': apellido or '',
                'fases': {}, 'total': 0,
            }
        if fase:
            result[op_id]['fases'][fase] = veces
            result[op_id]['total'] += veces
    # Marcar quien necesita rotar (>=4 veces seguidas en una sola fase)
    for op in result.values():
        for fase, cnt in op['fases'].items():
            if cnt >= 4 and op['total'] == cnt:
                op['sugerir_rotar'] = True
                op['fase_acumulada'] = fase
                op['dias_en_fase'] = cnt
                break
    return jsonify({'operarios': list(result.values()), 'ventana_dias': 14})


@bp.route('/api/programacion/programar/<int:evento_id>/iniciar', methods=['POST'])
def prog_iniciar_produccion(evento_id):
    """Operario aprieta 'Iniciar produccion' — graba inicio_real_at,
    marca la sala asignada como 'ocupada' y registra evento en area_eventos.

    Idempotente: si ya tiene inicio_real_at, retorna ok=False con el ts
    existente — no sobreescribe (evita doble inicio accidental)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    pp = c.execute("""SELECT id, producto, area_id, inicio_real_at, fin_real_at
                      FROM produccion_programada WHERE id=?""", (evento_id,)).fetchone()
    if not pp:
        return jsonify({'error': 'produccion no existe'}), 404
    if pp[3]:  # ya iniciada
        return jsonify({'ok': True, 'ya_iniciada': True, 'inicio_real_at': pp[3]})
    if pp[4]:  # ya terminada
        return jsonify({'error': 'produccion ya terminada'}), 400
    c.execute("UPDATE produccion_programada SET inicio_real_at=datetime('now') WHERE id=?", (evento_id,))
    if pp[2]:  # tiene sala asignada → marcar ocupada
        prev = c.execute("SELECT estado FROM areas_planta WHERE id=?", (pp[2],)).fetchone()
        c.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=?", (pp[2],))
        c.execute("""INSERT INTO area_eventos
            (area_id, tipo, estado_anterior, estado_nuevo, produccion_id, usuario, nota)
            VALUES (?,?,?,?,?,?,?)""",
            (pp[2], 'iniciar_prod', (prev[0] if prev else None), 'ocupada',
             evento_id, user, f'inicio: {pp[1]}'))
    conn.commit()
    return jsonify({'ok': True, 'evento_id': evento_id})


@bp.route('/api/programacion/programar/<int:evento_id>/terminar', methods=['POST'])
def prog_terminar_produccion(evento_id):
    """Operario aprieta 'Terminar' — graba fin_real_at, marca sala 'sucia'
    (asume que despues de produccion siempre hay limpieza), registra evento.

    Idempotente: si ya tiene fin_real_at, no sobreescribe."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    pp = c.execute("""SELECT id, producto, area_id, inicio_real_at, fin_real_at
                      FROM produccion_programada WHERE id=?""", (evento_id,)).fetchone()
    if not pp:
        return jsonify({'error': 'produccion no existe'}), 404
    if pp[4]:
        return jsonify({'ok': True, 'ya_terminada': True, 'fin_real_at': pp[4]})
    if not pp[3]:
        return jsonify({'error': 'produccion no ha iniciado'}), 400
    c.execute("UPDATE produccion_programada SET fin_real_at=datetime('now') WHERE id=?", (evento_id,))
    if pp[2]:
        prev = c.execute("SELECT estado FROM areas_planta WHERE id=?", (pp[2],)).fetchone()
        c.execute("UPDATE areas_planta SET estado='sucia' WHERE id=?", (pp[2],))
        c.execute("""INSERT INTO area_eventos
            (area_id, tipo, estado_anterior, estado_nuevo, produccion_id, usuario, nota)
            VALUES (?,?,?,?,?,?,?)""",
            (pp[2], 'terminar_prod', (prev[0] if prev else None), 'sucia',
             evento_id, user, f'fin: {pp[1]} → sala sucia, espera limpieza'))
    conn.commit()
    # Calcular cycle time real
    cycle = c.execute("""SELECT
        CAST((julianday(fin_real_at) - julianday(inicio_real_at)) * 24 * 60 AS INTEGER) as min
        FROM produccion_programada WHERE id=?""", (evento_id,)).fetchone()
    return jsonify({'ok': True, 'evento_id': evento_id,
                    'cycle_time_min': cycle[0] if cycle else None})


@bp.route('/api/planta/centro-mando', methods=['GET'])
def planta_centro_mando():
    """Endpoint agregado del Centro de Mando — devuelve TODO en una llamada
    para que la UI haga UN fetch y pinte el tablero completo. Optimizado
    para auto-refresh cada 30s.

    Retorna:
      areas: list[{id, codigo, nombre, tipo, estado, capacidades, ocupada_por[]}]
        ocupada_por incluye produccion_id, producto, lotes, kg, operarios y
        inicio_real_at + minutos_corridos para timer en vivo.
      operarios_libres: list — quienes no estan en una produccion en curso.
      kpis: produciones_activas_ahora, prods_terminadas_hoy,
            cycle_time_promedio_min, salas_libres, salas_sucias.
      eventos_recientes: ultimos 10 eventos para timeline lateral.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    hoy = date.today().isoformat()

    # Areas con producciones activas (in progress: inicio_real_at NOT NULL,
    # fin_real_at NULL)
    areas = []
    for r in conn.execute("""
        SELECT id, codigo, nombre, tipo, puede_producir, puede_envasar,
               marmita_ml, especial, estado, orden
        FROM areas_planta WHERE activo=1 ORDER BY orden, id
    """):
        areas.append({
            'id': r[0], 'codigo': r[1], 'nombre': r[2], 'tipo': r[3],
            'puede_producir': bool(r[4]), 'puede_envasar': bool(r[5]),
            'marmita_ml': r[6], 'especial': r[7],
            'estado': r[8], 'orden': r[9],
            'ocupada_por': [],
        })
    area_by_id = {a['id']: a for a in areas}
    # Producciones en curso (no terminadas) — vienen siempre, las del dia mas
    # las que se quedaron sin terminar (ocupando sala todavia)
    for r in conn.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes, pp.estado,
               pp.area_id, pp.inicio_real_at, pp.fin_real_at,
               COALESCE(pp.lotes,1)*COALESCE(fh.lote_size_kg,0) as kg,
               od.nombre || ' ' || COALESCE(od.apellido,'')  as op_disp,
               oe.nombre || ' ' || COALESCE(oe.apellido,'')  as op_elab,
               oen.nombre || ' ' || COALESCE(oen.apellido,'') as op_env,
               oa.nombre || ' ' || COALESCE(oa.apellido,'')  as op_acon,
               CAST((julianday('now') - julianday(pp.inicio_real_at)) * 24 * 60 AS INTEGER) as min_corridos
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre))=UPPER(TRIM(pp.producto))
        LEFT JOIN operarios_planta od  ON od.id  = pp.operario_dispensacion_id
        LEFT JOIN operarios_planta oe  ON oe.id  = pp.operario_elaboracion_id
        LEFT JOIN operarios_planta oen ON oen.id = pp.operario_envasado_id
        LEFT JOIN operarios_planta oa  ON oa.id  = pp.operario_acondicionamiento_id
        WHERE pp.area_id IS NOT NULL
          AND (pp.inicio_real_at IS NOT NULL AND pp.fin_real_at IS NULL
               OR pp.fecha_programada=? AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado'))
        ORDER BY pp.inicio_real_at DESC NULLS LAST
    """, (hoy,)):
        info = {
            'produccion_id': r[0], 'producto': r[1], 'fecha': r[2],
            'lotes': r[3], 'estado': r[4],
            'inicio_real_at': r[6], 'fin_real_at': r[7], 'kg': r[8],
            'minutos_corridos': r[13] if r[6] and not r[7] else None,
            'operario_dispensacion':      (r[9]  or '').strip() or None,
            'operario_elaboracion':       (r[10] or '').strip() or None,
            'operario_envasado':          (r[11] or '').strip() or None,
            'operario_acondicionamiento': (r[12] or '').strip() or None,
            'en_curso': bool(r[6] and not r[7]),
        }
        a = area_by_id.get(r[5])
        if a:
            a['ocupada_por'].append(info)

    # KPIs del dia
    kpi_row = conn.execute("""
        SELECT
            SUM(CASE WHEN inicio_real_at IS NOT NULL AND fin_real_at IS NULL THEN 1 ELSE 0 END) as activas,
            SUM(CASE WHEN DATE(fin_real_at)=? THEN 1 ELSE 0 END) as terminadas_hoy,
            AVG(CASE WHEN DATE(fin_real_at)=?
                     THEN (julianday(fin_real_at)-julianday(inicio_real_at))*24*60
                     ELSE NULL END) as ct_prom_min
        FROM produccion_programada
        WHERE fecha_programada >= date('now','-30 day')
    """, (hoy, hoy)).fetchone()
    salas_libres = sum(1 for a in areas if a['estado'] == 'libre' and a['tipo']=='produccion')
    salas_sucias = sum(1 for a in areas if a['estado'] == 'sucia')
    salas_ocupadas = sum(1 for a in areas if a['estado'] == 'ocupada')

    # Eventos recientes (ultimos 15)
    eventos = []
    for r in conn.execute("""
        SELECT ev.tipo, ev.estado_anterior, ev.estado_nuevo,
               ev.usuario, ev.nota, ev.ts,
               ap.codigo, ap.nombre,
               pp.producto
        FROM area_eventos ev
        LEFT JOIN areas_planta ap ON ap.id=ev.area_id
        LEFT JOIN produccion_programada pp ON pp.id=ev.produccion_id
        ORDER BY ev.ts DESC LIMIT 15
    """):
        eventos.append({
            'tipo': r[0], 'de': r[1], 'a': r[2], 'usuario': r[3],
            'nota': r[4], 'ts': r[5], 'area_codigo': r[6],
            'area_nombre': r[7], 'producto': r[8],
        })

    return jsonify({
        'areas': areas,
        'kpis': {
            'producciones_activas_ahora': kpi_row[0] or 0,
            'terminadas_hoy': kpi_row[1] or 0,
            'cycle_time_promedio_min': int(kpi_row[2]) if kpi_row[2] else None,
            'salas_libres': salas_libres,
            'salas_sucias': salas_sucias,
            'salas_ocupadas': salas_ocupadas,
        },
        'eventos_recientes': eventos,
        'fecha': hoy,
    })


@bp.route('/api/programacion/produccion-programada/listado', methods=['GET'])
def listado_produccion_programada():
    """Lista todas las producciones programadas activas con su origen,
    para diagnostico de producciones fantasma. Sebastian lo necesita
    cuando ve algo en el horizonte que no recuerda haber programado."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    rows = conn.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
               pp.estado, COALESCE(pp.origen,'manual') as origen,
               pp.observaciones,
               COALESCE(pp.lotes,1) * COALESCE(fh.lote_size_kg,0) as kg,
               pp.area_id, ap.nombre as area_nombre,
               pp.operario_dispensacion_id, od.nombre || ' ' || COALESCE(od.apellido,'') as op_disp,
               pp.operario_elaboracion_id,  oe.nombre || ' ' || COALESCE(oe.apellido,'') as op_elab,
               pp.operario_envasado_id,     oen.nombre || ' ' || COALESCE(oen.apellido,'') as op_env,
               pp.operario_acondicionamiento_id, oa.nombre || ' ' || COALESCE(oa.apellido,'') as op_acon
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        LEFT JOIN operarios_planta od  ON od.id  = pp.operario_dispensacion_id
        LEFT JOIN operarios_planta oe  ON oe.id  = pp.operario_elaboracion_id
        LEFT JOIN operarios_planta oen ON oen.id = pp.operario_envasado_id
        LEFT JOIN operarios_planta oa  ON oa.id  = pp.operario_acondicionamiento_id
        WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
          AND pp.fecha_programada >= date('now','-7 day')
        ORDER BY pp.fecha_programada ASC, pp.id ASC
    """).fetchall()
    out = [{
        'id': r[0], 'producto': r[1], 'fecha_programada': r[2], 'lotes': r[3],
        'estado': r[4], 'origen': r[5], 'observaciones': r[6], 'kg': r[7],
        'area_id': r[8], 'area_nombre': r[9],
        'operario_dispensacion_id': r[10], 'operario_dispensacion': (r[11] or '').strip() or None,
        'operario_elaboracion_id':  r[12], 'operario_elaboracion':  (r[13] or '').strip() or None,
        'operario_envasado_id':     r[14], 'operario_envasado':     (r[15] or '').strip() or None,
        'operario_acondicionamiento_id': r[16], 'operario_acondicionamiento': (r[17] or '').strip() or None,
    } for r in rows]
    return jsonify({'producciones': out, 'total': len(out)})


@bp.route('/api/programacion/produccion-programada/<int:evento_id>/borrar', methods=['DELETE'])
def borrar_produccion_programada(evento_id):
    """Borra una produccion programada (HARD DELETE, no solo cancelar).
    Solo admin. Usado para limpiar fantasmas que aparecen en el horizonte
    sin razon (ej. una entrada manual antigua que sobrevivio)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    # Importar lista de admins desde compras (misma fuente de verdad)
    try:
        from blueprints.compras import ADMIN_USERS as _ADMIN
    except Exception:
        _ADMIN = ('sebastian', 'alejandro')
    if user not in _ADMIN:
        return jsonify({'error': 'Solo admin puede borrar'}), 403
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT producto, fecha_programada, COALESCE(origen,'manual') "
        "FROM produccion_programada WHERE id=?",
        (evento_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'Produccion no encontrada'}), 404
    # Tambien borrar items de checklist huerfanos asociados
    try:
        c.execute("DELETE FROM produccion_checklist WHERE produccion_id=?", (evento_id,))
    except sqlite3.OperationalError:
        pass
    c.execute("DELETE FROM produccion_programada WHERE id=?", (evento_id,))
    conn.commit()
    return jsonify({
        'ok': True, 'id': evento_id,
        'producto': row[0], 'fecha': row[1], 'origen': row[2],
        'mensaje': f'Produccion {row[0]} ({row[1]}) borrada definitivamente',
    })


def _distribuir_fefo(c, codigo_mp, cantidad_a_descontar):
    """Distribuye una cantidad a descontar entre lotes activos siguiendo FEFO
    (First-Expired-First-Out): consume primero del lote con fecha_vencimiento
    más cercana, luego del siguiente, etc.

    Sebastian (29-abr-2026): "FEFO perfecto". Antes el descuento era global
    (anotaba el lote sugerido en obs pero no era estricto). Ahora el descuento
    es POR LOTE: cada movimiento de Salida lleva el codigo del lote del que
    realmente se está consumiendo.

    Returns: lista de dicts [{lote, cantidad, fecha_vencimiento, sin_lote}, ...]
    Si la suma de stock por lotes < cantidad_a_descontar, el remainder se
    devuelve con sin_lote=True (consumo de stock sin trazabilidad de lote —
    suele indicar drift del inventario o entradas históricas sin lote).
    """
    if cantidad_a_descontar <= 0:
        return []

    # Stock disponible por lote: SUM(Entradas con lote) - SUM(Salidas con lote)
    # Excluye lotes Vencidos/Bloqueados (no se debe consumir).
    rows = c.execute("""
        SELECT lote, fecha_vencimiento,
               SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_lote
        FROM movimientos
        WHERE material_id = ?
          AND COALESCE(lote, '') != ''
          AND COALESCE(estado_lote, '') NOT IN ('Vencido','Bloqueado','Rechazado')
        GROUP BY lote, fecha_vencimiento
        HAVING stock_lote > 0
        ORDER BY COALESCE(fecha_vencimiento, '9999-12-31') ASC,
                 lote ASC
    """, (codigo_mp,)).fetchall()

    distribucion = []
    restante = float(cantidad_a_descontar)
    for lote, fv, stock_lote in rows:
        if restante <= 0:
            break
        toma = min(float(stock_lote), restante)
        distribucion.append({
            'lote': lote,
            'cantidad': round(toma, 2),
            'fecha_vencimiento': fv,
            'sin_lote': False,
        })
        restante -= toma

    # Si aún queda cantidad por descontar, viene de stock sin lote (entradas
    # históricas sin trazabilidad). Lo registramos sin lote para mantener
    # consistencia del stock total.
    if restante > 0.01:
        distribucion.append({
            'lote': None,
            'cantidad': round(restante, 2),
            'fecha_vencimiento': None,
            'sin_lote': True,
        })

    return distribucion


@bp.route('/api/programacion/programar/<int:evento_id>/completar', methods=['POST'])
def prog_completar_evento(evento_id):
    """Marca una produccion como completada Y descuenta inventario.

    Sebastian (29-abr-2026): "que todo descuente que el inventario este
    perfecto". Antes solo cambiaba estado — ahora:
      1. Calcula consumo de MPs desde formula_items: cantidad_g_por_lote * lotes
         (o si no hay cantidad_g_por_lote, usa porcentaje * cantidad_kg * 1000).
      2. Calcula consumo de MEEs desde produccion_checklist (items con
         mee_codigo_asignado en estado verificado_ok / recibido / listo).
      3. Inserta movimientos de Salida por cada MP.
      4. Inserta movimientos_mee + actualiza maestro_mee.stock_actual por MEE.
      5. UPDATE produccion_programada estado='completado',
         inventario_descontado_at=NOW.
      6. Idempotente: si ya tiene inventario_descontado_at, no descontar 2x.

    Body opcional: {forzar_redescuento: true} para casos de emergencia
    (ej. el flag quedó stale por bug). Solo admin.
    Body opcional: {dry_run: true} para preview sin escribir nada.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json() or {}
    forzar = bool(d.get('forzar_redescuento'))
    dry_run = bool(d.get('dry_run'))
    if forzar and user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin puede forzar re-descuento'}), 403

    conn = get_db(); c = conn.cursor()
    prod = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
               pp.estado, COALESCE(pp.inventario_descontado_at,'') as descontado_at,
               COALESCE(pp.cantidad_kg, 0)         as cantidad_kg_explicita,
               COALESCE(fh.lote_size_kg, 0)        as lote_kg_formula
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh
               ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        WHERE pp.id=?
    """, (evento_id,)).fetchone()
    if not prod:
        return jsonify({'error': 'Producción no encontrada'}), 404
    pid, producto, fecha, lotes, estado, descontado_at, cant_kg_exp, lote_kg = prod
    lotes = int(lotes or 1)
    cant_kg_total = float(cant_kg_exp or 0) or (lotes * float(lote_kg or 0))

    if descontado_at and not forzar:
        return jsonify({
            'error': f'Inventario ya fue descontado el {descontado_at}',
            'codigo': 'YA_DESCONTADO',
            'hint': 'Si necesitas re-descontar (admin), envía {forzar_redescuento: true}',
            'inventario_descontado_at': descontado_at,
        }), 409

    # ── 1. Calcular MPs a consumir ─────────────────────────────────────
    mps_a_consumir = []
    try:
        rows = c.execute("""
            SELECT material_id, material_nombre,
                   COALESCE(porcentaje, 0)                as pct,
                   COALESCE(cantidad_g_por_lote, 0)       as g_por_lote
            FROM formula_items
            WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
        """, (producto,)).fetchall()
        for cod, nom, pct, g_lote in rows:
            # Preferimos cantidad_g_por_lote * lotes. Fallback: porcentaje*kg*1000
            g_total = float(g_lote or 0) * lotes
            if g_total <= 0 and cant_kg_total > 0:
                g_total = (float(pct or 0) / 100.0) * cant_kg_total * 1000.0
            if g_total > 0:
                mps_a_consumir.append({
                    'codigo_mp': cod or '',
                    'nombre': nom or '',
                    'cantidad_g': round(g_total, 2),
                })
    except Exception as e:
        return jsonify({'error': f'Error calculando MPs: {e}'}), 500

    # ── 2. Calcular MEEs a consumir desde checklist (solo recibidos/verificados) ──
    mees_a_consumir = []
    try:
        crows = c.execute("""
            SELECT mee_codigo_asignado, descripcion, cantidad_unidades, item_tipo
            FROM produccion_checklist
            WHERE produccion_id = ?
              AND COALESCE(mee_codigo_asignado,'') != ''
              AND COALESCE(cantidad_unidades, 0) > 0
              AND estado IN ('verificado_ok','recibido','listo')
        """, (pid,)).fetchall()
        for mee_cod, desc, cant_ud, tipo_item in crows:
            mees_a_consumir.append({
                'codigo': mee_cod, 'descripcion': desc or '',
                'cantidad_unidades': int(cant_ud or 0),
                'tipo_item': tipo_item or '',
            })
    except Exception:
        # Si la tabla checklist no existe o falla, seguimos sin MEEs (no bloqueamos MPs)
        pass

    # ── 3. Si dry_run, devolver preview sin escribir ───────────────────
    if dry_run:
        return jsonify({
            'ok': True,
            'dry_run': True,
            'producto': producto,
            'fecha': fecha,
            'lotes': lotes,
            'cantidad_kg_total': cant_kg_total,
            'mps_a_descontar': mps_a_consumir,
            'mees_a_descontar': mees_a_consumir,
            'total_mps': len(mps_a_consumir),
            'total_mees': len(mees_a_consumir),
            'total_g_mps': round(sum(m['cantidad_g'] for m in mps_a_consumir), 2),
            'total_unidades_mees': sum(m['cantidad_unidades'] for m in mees_a_consumir),
        })

    # ── 4. ESCRIBIR descuentos (transaccional) ─────────────────────────
    obs_base = f"Producción COMPLETADA: {producto} — {fecha} — {lotes} lote(s) × {cant_kg_total:.0f}kg"
    descontados_mps = []
    descontados_mees = []
    fecha_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    try:
        # MPs → FEFO REAL: distribuir el consumo entre lotes según fecha
        # de vencimiento (más cercano primero). Cada lote genera su propio
        # movimiento de Salida con cantidad específica. Si la suma de stock
        # por lote no alcanza, el remainder se registra sin lote (legacy).
        for mp in mps_a_consumir:
            distrib = _distribuir_fefo(c, mp['codigo_mp'], mp['cantidad_g'])
            mp['distribucion_fefo'] = []
            for d in distrib:
                lote_fragment = d['lote'] or '(sin lote — stock legacy)'
                obs_mp = (obs_base +
                          f" | FEFO lote: {lote_fragment}" +
                          (f" (vence {d['fecha_vencimiento']})" if d['fecha_vencimiento'] else ""))
                c.execute("""
                    INSERT INTO movimientos
                      (material_id, material_nombre, cantidad, tipo, fecha,
                       observaciones, operador, lote)
                    VALUES (?, ?, ?, 'Salida', ?, ?, ?, ?)
                """, (mp['codigo_mp'], mp['nombre'], d['cantidad'],
                      fecha_iso, obs_mp, user, d['lote']))
                mp['distribucion_fefo'].append({
                    'lote': d['lote'],
                    'cantidad_g': d['cantidad'],
                    'fecha_vencimiento': d['fecha_vencimiento'],
                    'sin_lote': d['sin_lote'],
                })
            descontados_mps.append(mp)
        # MEEs → INSERT INTO movimientos_mee + UPDATE maestro_mee
        for me in mees_a_consumir:
            try:
                c.execute("""
                    INSERT INTO movimientos_mee
                      (mee_codigo, tipo, cantidad, observaciones, responsable, fecha)
                    VALUES (?, 'Salida', ?, ?, ?, ?)
                """, (me['codigo'], me['cantidad_unidades'], obs_base, user, fecha_iso))
                c.execute(
                    "UPDATE maestro_mee SET stock_actual = COALESCE(stock_actual,0) - ? "
                    "WHERE codigo=?",
                    (me['cantidad_unidades'], me['codigo'])
                )
                descontados_mees.append(me)
            except sqlite3.OperationalError:
                # Si tabla mee no existe, seguimos
                continue
        # Actualizar produccion_programada
        c.execute("""
            UPDATE produccion_programada
               SET estado='completado',
                   inventario_descontado_at=?,
                   observaciones = COALESCE(observaciones,'') ||
                                   ' | INVENTARIO DESCONTADO ' || ? || ' por ' || ?
             WHERE id=?
        """, (fecha_iso, fecha_iso, user, pid))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({
            'error': f'Error descontando inventario: {e}',
            'mps_descontados_antes_de_fallar': descontados_mps,
            'mees_descontados_antes_de_fallar': descontados_mees,
        }), 500

    return jsonify({
        'ok': True,
        'id': pid,
        'producto': producto,
        'inventario_descontado_at': fecha_iso,
        'mps_descontados': descontados_mps,
        'mees_descontados': descontados_mees,
        'total_mps': len(descontados_mps),
        'total_mees': len(descontados_mees),
        'total_g_mps': round(sum(m['cantidad_g'] for m in descontados_mps), 2),
        'total_unidades_mees': sum(m['cantidad_unidades'] for m in descontados_mees),
        'mensaje': f"{producto} marcada completada. Descontados {len(descontados_mps)} MPs y {len(descontados_mees)} MEEs."
    })


@bp.route('/api/programacion/programar/<int:evento_id>/revertir-completado', methods=['POST'])
def prog_revertir_completado(evento_id):
    """Revierte una produccion completada: regresa MPs y MEEs al inventario,
    cambia estado a 'programado' y limpia el flag inventario_descontado_at.

    Solo admin. Sebastian (29-abr-2026): por si Sebastian o alguien marca
    completada por error o quiere re-hacer el descuento.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin'}), 403

    conn = get_db(); c = conn.cursor()
    prod = c.execute(
        "SELECT producto, fecha_programada, lotes, "
        "COALESCE(inventario_descontado_at,'') FROM produccion_programada WHERE id=?",
        (evento_id,)
    ).fetchone()
    if not prod:
        return jsonify({'error': 'Producción no encontrada'}), 404
    producto, fecha, lotes, descontado_at = prod
    if not descontado_at:
        return jsonify({'error': 'Esta producción no tenía inventario descontado'}), 400

    obs_filtro = f"Producción COMPLETADA: {producto} — {fecha}"
    revertidos_mps = []
    revertidos_mees = []
    fecha_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    try:
        # Reversión de MPs: insertar movimientos de Entrada compensatorios
        # PRESERVANDO el lote (FEFO reverso — cada lote consumido vuelve
        # a su lote de origen para que el stock por-lote quede coherente).
        rows = c.execute("""
            SELECT id, material_id, material_nombre, cantidad, lote, fecha_vencimiento
            FROM movimientos
            WHERE tipo='Salida' AND observaciones LIKE ?
        """, (f"{obs_filtro}%",)).fetchall()
        for mid, cod, nom, cant, lote, fv in rows:
            c.execute("""
                INSERT INTO movimientos
                  (material_id, material_nombre, cantidad, tipo, fecha,
                   observaciones, operador, lote, fecha_vencimiento)
                VALUES (?, ?, ?, 'Entrada', ?, ?, ?, ?, ?)
            """, (cod, nom, cant, fecha_iso,
                  f"REVERSIÓN producción completada — original mov #{mid}",
                  user, lote, fv))
            revertidos_mps.append({
                'codigo_mp': cod, 'nombre': nom,
                'cantidad_g': cant, 'lote': lote,
            })

        # Reversión de MEEs: insertar movimientos_mee de entrada + UPDATE stock
        try:
            rows_mee = c.execute("""
                SELECT id, mee_codigo, cantidad
                FROM movimientos_mee
                WHERE LOWER(tipo)='salida' AND observaciones LIKE ?
            """, (f"{obs_filtro}%",)).fetchall()
            for mid, mee_cod, cant in rows_mee:
                c.execute("""
                    INSERT INTO movimientos_mee
                      (mee_codigo, tipo, cantidad, observaciones, responsable, fecha)
                    VALUES (?, 'Entrada', ?, ?, ?, ?)
                """, (mee_cod, cant,
                      f"REVERSIÓN producción completada — original mov_mee #{mid}",
                      user, fecha_iso))
                c.execute(
                    "UPDATE maestro_mee SET stock_actual = COALESCE(stock_actual,0) + ? "
                    "WHERE codigo=?",
                    (cant, mee_cod)
                )
                revertidos_mees.append({'codigo': mee_cod, 'cantidad_unidades': cant})
        except sqlite3.OperationalError:
            pass

        # Limpiar flag y estado
        c.execute("""
            UPDATE produccion_programada
               SET estado='programado',
                   inventario_descontado_at=NULL,
                   observaciones = COALESCE(observaciones,'') ||
                                   ' | REVERTIDO ' || ? || ' por ' || ?
             WHERE id=?
        """, (fecha_iso, user, evento_id))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': f'Error revirtiendo: {e}'}), 500

    return jsonify({
        'ok': True,
        'id': evento_id,
        'mps_revertidos': revertidos_mps,
        'mees_revertidos': revertidos_mees,
        'mensaje': f"Producción revertida. {len(revertidos_mps)} MPs y {len(revertidos_mees)} MEEs regresados al inventario."
    })


@bp.route('/api/inventario/ajuste-manual', methods=['POST'])
def inventario_ajuste_manual():
    """Registra un ajuste manual de inventario con razón obligatoria.

    Sebastian (29-abr-2026): "que se mantenga, sea perfecta". Para los
    casos legítimos donde Sebastián/Daniela necesitan corregir stock
    (conteo físico, merma, robo, daño, etc.) — TODO ajuste queda en
    movimientos con observaciones específicas para auditoría.

    Body: {
      tipo_material: 'MP' | 'MEE',
      codigo: 'MP00001',
      cantidad: 1500,        # positivo siempre — el signo lo da motivo
      motivo: 'conteo_fisico' | 'merma' | 'robo' | 'daño' | 'correccion' | 'otro',
      direccion: 'sumar' | 'restar',
      observaciones: 'detalle libre obligatorio'
    }
    Solo admin.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin puede ajustar inventario'}), 403
    d = request.get_json() or {}
    tipo_mat = (d.get('tipo_material') or '').upper().strip()
    codigo = (d.get('codigo') or '').strip()
    cantidad = abs(float(d.get('cantidad') or 0))
    motivo = (d.get('motivo') or '').strip().lower()
    direccion = (d.get('direccion') or '').strip().lower()
    obs = (d.get('observaciones') or '').strip()

    MOTIVOS_OK = {'conteo_fisico', 'merma', 'robo', 'daño', 'dano',
                  'correccion', 'corrección', 'otro'}
    if tipo_mat not in ('MP', 'MEE'):
        return jsonify({'error': 'tipo_material debe ser MP o MEE'}), 400
    if not codigo:
        return jsonify({'error': 'codigo requerido'}), 400
    if cantidad <= 0:
        return jsonify({'error': 'cantidad debe ser > 0'}), 400
    if motivo not in MOTIVOS_OK:
        return jsonify({'error': f'motivo invalido — usar uno de {MOTIVOS_OK}'}), 400
    if direccion not in ('sumar', 'restar'):
        return jsonify({'error': "direccion debe ser 'sumar' o 'restar'"}), 400
    if not obs or len(obs) < 10:
        return jsonify({'error': 'observaciones obligatorias (min 10 chars)'}), 400

    conn = get_db(); c = conn.cursor()
    fecha_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    obs_full = f"AJUSTE_MANUAL[{motivo}]: {obs} (por {user})"

    if tipo_mat == 'MP':
        # Verificar que el MP existe
        mp = c.execute(
            "SELECT codigo_mp, nombre_inci FROM maestro_mps WHERE codigo_mp=?",
            (codigo,)
        ).fetchone()
        if not mp:
            return jsonify({'error': f'MP {codigo} no encontrado'}), 404
        tipo_mov = 'Entrada' if direccion == 'sumar' else 'Salida'
        c.execute("""
            INSERT INTO movimientos
              (material_id, material_nombre, cantidad, tipo, fecha,
               observaciones, operador)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (codigo, mp[1] or '', cantidad, tipo_mov, fecha_iso, obs_full, user))
    else:
        # MEE: actualizar maestro_mee + insertar movimientos_mee
        mee = c.execute(
            "SELECT codigo, descripcion, COALESCE(stock_actual,0) "
            "FROM maestro_mee WHERE codigo=?", (codigo,)
        ).fetchone()
        if not mee:
            return jsonify({'error': f'MEE {codigo} no encontrado'}), 404
        delta = cantidad if direccion == 'sumar' else -cantidad
        nuevo_stock = max(0, float(mee[2]) + delta)
        c.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?",
                  (nuevo_stock, codigo))
        c.execute("""
            INSERT INTO movimientos_mee
              (mee_codigo, tipo, cantidad, observaciones, responsable, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (codigo, 'Entrada' if direccion == 'sumar' else 'Salida',
              cantidad, obs_full, user, fecha_iso))
    conn.commit()
    return jsonify({
        'ok': True,
        'tipo_material': tipo_mat,
        'codigo': codigo,
        'cantidad': cantidad,
        'direccion': direccion,
        'motivo': motivo,
        'mensaje': f'Ajuste {direccion} {cantidad} a {codigo} registrado.'
    })


@bp.route('/api/programacion/debug-calendario')
def prog_debug_calendario():
    """Show raw calendar events and how they match to products."""
    conn = get_db()
    cal  = _fetch_calendar_events(days_ahead=120)
    conn2 = get_db()
    formulas = _get_formulas(conn2)
    products_with_formula = list(formulas.keys())

    import re as _re_dbg
    _stop = {'DE','DEL','LA','EL','LOS','LAS','CON','MAS','PARA',
             'PRODUCCION','PRODUCCIÓN','LOTE','ESPAGIRIA','ANIMUS'}

    def score(t, p):
        tu, pu = t.upper(), p.upper()
        if pu in tu: return 100
        tw = set(w for w in _re_dbg.split(r'[^A-Z0-9]+', tu) if len(w)>2)
        pw = set(w for w in _re_dbg.split(r'[^A-Z0-9]+', pu) if len(w)>2) - _stop
        if not pw: return 0
        return int(100*len(pw&tw)/len(pw))

    # Load sku map
    import re as _re_d
    _NOT_SKU = {'FAB','QC','CON','SIN','MICRO','ENVASADO','ACONDICIONAMIENTO',
                'FABRICACION','FABRICACIÓN','LANZAMIENTO','KG','MES','DIAS','ML'}
    sku_map = {}
    try:
        for r in conn.execute("SELECT UPPER(sku), producto_nombre FROM sku_producto_map WHERE activo=1").fetchall():
            sku_map[r[0]] = r[1]
    except Exception:
        pass

    def _skus_d(titulo):
        tokens = _re_d.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in _NOT_SKU]

    sku_matches = {}
    matches = []
    for ev in cal.get('events', []):
        titulo = ev.get('titulo','')
        fecha  = ev.get('fecha','')
        skus   = _skus_d(titulo)
        matched_prod = None
        for sku in skus:
            pn = sku_map.get(sku)
            if pn and pn in products_with_formula:
                matched_prod = pn
                if pn not in sku_matches or fecha < sku_matches[pn]:
                    sku_matches[pn] = fecha
                break
        matches.append({
            'evento': titulo, 'fecha': fecha,
            'skus_extracted': skus,
            'matched_product': matched_prod
        })

    return jsonify({
        'source': cal.get('source','?'),
        'error':  cal.get('error'),
        'total_events': len(cal.get('events',[])),
        'gcal_ical_url_set': bool(GCAL_ICAL_URL),
        'google_api_key_set': bool(GOOGLE_API_KEY),
        'sku_matches_summary': sku_matches,
        'unmatched_events': [m for m in matches if not m['matched_product']],
        'matched_events': [m for m in matches if m['matched_product']]
    })

@bp.route('/api/programacion/calendario')
def prog_calendario():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    days = int(request.args.get('days', 90))
    return jsonify(_fetch_calendar_events(days_ahead=days))


@bp.route('/api/programacion/stock-60d')
def prog_stock_60d():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    conn = get_db()
    vel_data = _shopify_velocity(conn, days=60)
    mp_stock = _get_mp_stock(conn)
    formulas = _get_formulas(conn)
    cal = _fetch_calendar_events(days_ahead=90)
    china_mps_set = _get_china_mps(conn)
    projection, _ = _project_stock(conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []), china_mps=china_mps_set)
    return jsonify({'proyeccion': projection, 'generado_en': datetime.now().isoformat()})


@bp.route('/api/programacion/alertas')
def prog_alertas():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    conn = get_db()
    vel_data = _shopify_velocity(conn, days=60)
    mp_stock = _get_mp_stock(conn)
    formulas = _get_formulas(conn)
    cal = _fetch_calendar_events(days_ahead=90)
    china_mps_set = _get_china_mps(conn)
    _, alerts = _project_stock(conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []), china_mps=china_mps_set)
    return jsonify({'alertas': alerts, 'n_alertas': len(alerts)})


@bp.route('/api/programacion/productos')
def prog_productos():
    """Lista de productos con fórmulas — usada por selectores en Envasado/Acond."""
    conn = get_db()
    rows = conn.execute(
        "SELECT producto_nombre, lote_size_kg FROM formula_headers ORDER BY producto_nombre"
    ).fetchall()
    return jsonify({
        'formulas': [{'nombre': r[0], 'lote_size_kg': r[1]} for r in rows],
        'count': len(rows),
    })


@bp.route('/api/programacion/regenerar-oc', methods=['POST'])
def prog_regenerar_oc():
    """Borra solicitudes auto-generadas Pendientes + sus OCs Borrador y
    vuelve a llamar al generador con los datos ACTUALES de Programación.

    Útil cuando el cálculo cambió (más producciones programadas, nuevos
    déficits) y las solicitudes viejas tienen cantidades obsoletas.

    NO toca solicitudes en estado Aprobada/Pagada (esas se respetan como
    histórico). Solo borra Pendientes auto-generadas (observaciones LIKE
    '%Centro Programación%' o '%Centro Programacion%' o '%Auto-generada%').
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db()
    c = conn.cursor()
    deleted = {'solicitudes': 0, 'ordenes_compra': 0, 'items': 0}

    try:
        # 1. Listar solicitudes auto-generadas Pendientes y sus OCs
        rows = c.execute("""
            SELECT numero, numero_oc FROM solicitudes_compra
            WHERE estado = 'Pendiente'
              AND categoria IN ('Materia Prima', 'MP')
              AND (observaciones LIKE '%Centro Programación%'
                   OR observaciones LIKE '%Centro Programacion%'
                   OR observaciones LIKE '%Auto-generada%')
        """).fetchall()
        nums_sol = [r[0] for r in rows]
        nums_oc = [r[1] for r in rows if r[1]]

        if nums_sol:
            ph_sol = ','.join('?' * len(nums_sol))
            try:
                d = c.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph_sol})", nums_sol)
                deleted['items'] = d.rowcount or 0
            except sqlite3.OperationalError:
                pass
            d = c.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph_sol})", nums_sol)
            deleted['solicitudes'] = d.rowcount or 0

        if nums_oc:
            ph_oc = ','.join('?' * len(nums_oc))
            # Solo borrar OCs en estado Borrador (las Aprobadas/Pagadas son histórico)
            ocs_borrar = [r[0] for r in c.execute(
                f"SELECT numero_oc FROM ordenes_compra WHERE numero_oc IN ({ph_oc}) AND estado='Borrador'",
                nums_oc
            ).fetchall()]
            if ocs_borrar:
                ph_b = ','.join('?' * len(ocs_borrar))
                try:
                    c.execute(f"DELETE FROM ordenes_compra_items WHERE numero_oc IN ({ph_b})", ocs_borrar)
                except sqlite3.OperationalError:
                    pass
                d = c.execute(f"DELETE FROM ordenes_compra WHERE numero_oc IN ({ph_b})", ocs_borrar)
                deleted['ordenes_compra'] = d.rowcount or 0

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': 'Falló el borrado de solicitudes viejas',
            'detalle': str(e),
        }), 500

    # 2. Recalcular déficit con la lógica correcta (total_g - stock una sola
    # vez). Misma fuente de verdad que /programacion para no divergir.
    mp_deficit = _compute_mp_deficit_aggregated(conn, days_ahead=90)

    if not mp_deficit:
        return jsonify({'ok': True, 'mensaje': 'Sin déficits actuales — solo se borraron viejas',
                        'borradas': deleted, 'creadas': []})

    SIN_PROV = 'Sin asignar'
    grupos = {}
    for cod, info in mp_deficit.items():
        prov = info.get('proveedor') or SIN_PROV
        grupos.setdefault(prov, []).append({
            'codigo': cod,
            'nombre': info['nombre'],
            'deficit_g': info['deficit_g'],
            'productos': info['productos'],
        })

    from datetime import datetime as _dt
    year = _dt.now().strftime('%Y')
    last_n = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM solicitudes_compra WHERE numero LIKE ?",
        (f"SOL-{year}-%",)
    ).fetchone()[0] or 0
    n_sol = last_n
    user = session.get('compras_user', 'Sistema')

    creadas = []
    proveedores_ordenados = sorted(grupos.keys(), key=lambda p: (p == SIN_PROV, p.lower()))

    try:
        for prov in proveedores_ordenados:
            items = grupos[prov]
            if not items:
                continue
            n_sol += 1
            sol_numero = f"SOL-{year}-{n_sol:04d}"
            n_oc = (conn.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) FROM ordenes_compra WHERE numero_oc LIKE ?",
                (f"OC-{year}-%",)
            ).fetchone()[0] or 0) + 1
            num_oc = f"OC-{year}-{n_oc:04d}"

            mps_resumen_items = sorted(items, key=lambda x: -x['deficit_g'])[:5]
            mps_resumen = ', '.join([
                (it['nombre'][:25] + f" ({int(it['deficit_g']):,} g)".replace(',', '.'))
                for it in mps_resumen_items
            ])
            if len(items) > 5:
                mps_resumen += f' +{len(items) - 5} más'

            es_sin_prov = (prov == SIN_PROV)
            obs_prefix = (
                "REQUIERE ASIGNAR PROVEEDOR — " if es_sin_prov else
                "Auto-generada Centro Programación — "
            )
            obs = f"{obs_prefix}Proveedor: {prov} · {len(items)} MPs · {mps_resumen}"
            if es_sin_prov:
                obs += " · ACCIÓN: Catalina debe asignar proveedor en /admin → Catálogo MPs y disparar Generar OC nuevamente."

            conn.execute("""INSERT INTO solicitudes_compra
                (numero, fecha, estado, solicitante, urgencia, observaciones,
                 area, empresa, categoria, tipo, numero_oc)
                VALUES (?, datetime('now'), 'Pendiente', ?, 'Alta', ?,
                        'Produccion', 'Espagiria', 'Materia Prima', 'Compra', ?)""",
                (sol_numero, user, obs, num_oc))

            conn.execute("""INSERT INTO ordenes_compra
                (numero_oc, fecha, estado, proveedor, valor_total, observaciones, creado_por, categoria)
                VALUES (?, datetime('now'), 'Borrador', ?, 0, ?, ?, 'MP')""",
                (num_oc, prov,
                 f"OC sugerida desde Centro Programación · {len(items)} MPs",
                 user))

            items_created_this = []
            for it in items:
                just = f"Déficit para producción de: {', '.join(it['productos'][:3])}"
                if len(it['productos']) > 3:
                    just += f' +{len(it["productos"])-3} más'
                conn.execute("""INSERT INTO solicitudes_compra_items
                    (numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion)
                    VALUES (?,?,?,?,?,?)""",
                    (sol_numero, it['codigo'], it['nombre'],
                     it['deficit_g'], 'g', just))
                try:
                    conn.execute("""INSERT INTO ordenes_compra_items
                        (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
                        VALUES (?,?,?,?,0,0)""",
                        (num_oc, it['codigo'], it['nombre'], it['deficit_g']))
                except sqlite3.OperationalError:
                    pass
                items_created_this.append({
                    'codigo': it['codigo'], 'nombre': it['nombre'],
                    'deficit_g': round(it['deficit_g'], 1),
                })

            creadas.append({
                'solicitud': sol_numero, 'orden_compra': num_oc,
                'proveedor': prov, 'n_items': len(items_created_this),
                'requiere_asignacion': es_sin_prov,
            })
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': 'Borrado OK pero falló la regeneración',
            'detalle': str(e),
            'borradas': deleted,
        }), 500

    n_total_mps = sum(len(g) for g in grupos.values())
    n_proveedores = len([p for p in grupos.keys() if p != SIN_PROV])
    n_huerfanos = len(grupos.get(SIN_PROV, []))

    return jsonify({
        'ok': True,
        'borradas': deleted,
        'creadas': creadas,
        'total_solicitudes_nuevas': len(creadas),
        'total_mps': n_total_mps,
        'proveedores_resueltos': n_proveedores,
        'mps_huerfanos': n_huerfanos,
        'mensaje': (
            f"✅ Borradas {deleted['solicitudes']} solicitudes viejas + "
            f"creadas {len(creadas)} nuevas con datos actuales "
            f"({n_total_mps} MPs, {n_proveedores} proveedores"
            + (f", {n_huerfanos} huérfanos" if n_huerfanos else "") + ")"
        ),
    })


@bp.route('/api/programacion/generar-oc', methods=['POST'])
def prog_generar_oc():
    """Genera solicitudes de compra agrupadas POR PROVEEDOR.

    Política operacional definida con el dueño del negocio:
      - 1 solicitud por cada proveedor que tenga MPs en déficit
      - 1 solicitud SEPARADA con todas las MPs sin proveedor asignado
        (proveedor='Sin asignar') para que Catalina las revise, asigne en
        /admin → Catálogo MPs, y al refrescar la próxima vez ya queden
        agrupadas en sus proveedores correctos.

    Lee el proveedor de cada MP desde maestro_mps.proveedor.
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db()

    # Cálculo correcto: agrega total_g por MP y resta stock UNA vez.
    # Antes se sumaban deficits per-product (under-cuenta cuando hay stock
    # parcial). Esto deja las cantidades del OC alineadas con lo que muestra
    # /programacion (planificacion_estrategica + mps-deficit).
    mp_deficit = _compute_mp_deficit_aggregated(conn, days_ahead=90)

    if not mp_deficit:
        return jsonify({
            'ok': True,
            'mensaje': 'No hay déficits de MP — sin OC necesaria',
            'creadas': []
        })

    # Agrupar MPs en déficit por proveedor; sin proveedor → '(Sin asignar)'
    SIN_PROV = 'Sin asignar'
    grupos = {}  # proveedor → lista de items
    for cod, info in mp_deficit.items():
        prov = info.get('proveedor') or SIN_PROV
        grupos.setdefault(prov, []).append({
            'codigo': cod,
            'nombre': info['nombre'],
            'deficit_g': info['deficit_g'],
            'productos': info['productos'],
        })

    # Numero de SOL inicial
    from datetime import datetime as _dt
    year = _dt.now().strftime('%Y')
    last_n = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM solicitudes_compra WHERE numero LIKE ?",
        (f"SOL-{year}-%",)
    ).fetchone()[0] or 0
    n_sol = last_n
    user = session.get('compras_user', 'Sistema')

    creadas = []
    huerfana_info = None

    # Ordenar: primero proveedores reales, al final 'Sin asignar' para que
    # quede visualmente claro como solicitud "por revisar"
    proveedores_ordenados = sorted(
        grupos.keys(),
        key=lambda p: (p == SIN_PROV, p.lower())
    )

    try:
        for prov in proveedores_ordenados:
            items = grupos[prov]
            if not items:
                continue
            n_sol += 1
            sol_numero = f"SOL-{year}-{n_sol:04d}"
            n_oc = (conn.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) FROM ordenes_compra WHERE numero_oc LIKE ?",
                (f"OC-{year}-%",)
            ).fetchone()[0] or 0) + 1
            num_oc = f"OC-{year}-{n_oc:04d}"

            # Resumen de MPs principales para observaciones (legibilidad)
            mps_resumen_items = sorted(items, key=lambda x: -x['deficit_g'])[:5]
            mps_resumen = ', '.join([
                (it['nombre'][:25] + f" ({int(it['deficit_g']):,} g)".replace(',', '.'))
                for it in mps_resumen_items
            ])
            if len(items) > 5:
                mps_resumen += f' +{len(items) - 5} más'

            es_sin_prov = (prov == SIN_PROV)
            obs_prefix = (
                "REQUIERE ASIGNAR PROVEEDOR — " if es_sin_prov else
                "Auto-generada Centro Programación — "
            )
            obs = (
                f"{obs_prefix}Proveedor: {prov} · "
                f"{len(items)} MPs · {mps_resumen}"
            )
            if es_sin_prov:
                obs += " · ACCIÓN: Catalina debe asignar proveedor en /admin → Catálogo MPs y disparar Generar OC nuevamente."

            conn.execute("""INSERT INTO solicitudes_compra
                (numero, fecha, estado, solicitante, urgencia, observaciones,
                 area, empresa, categoria, tipo, numero_oc)
                VALUES (?, datetime('now'), 'Pendiente', ?, 'Alta', ?,
                        'Produccion', 'Espagiria', 'Materia Prima', 'Compra', ?)""",
                (sol_numero, user, obs, num_oc))

            # OC asociada con el proveedor correcto (o 'Sin asignar')
            valor_estimado_total = 0
            conn.execute("""INSERT INTO ordenes_compra
                (numero_oc, fecha, estado, proveedor, valor_total, observaciones, creado_por, categoria)
                VALUES (?, datetime('now'), 'Borrador', ?, 0, ?, ?, 'MP')""",
                (num_oc, prov,
                 f"OC sugerida desde Centro Programación · {len(items)} MPs",
                 user))

            items_created_this = []
            for it in items:
                just = f"Déficit para producción de: {', '.join(it['productos'][:3])}"
                if len(it['productos']) > 3:
                    just += f' +{len(it["productos"])-3} más'
                conn.execute("""INSERT INTO solicitudes_compra_items
                    (numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion)
                    VALUES (?,?,?,?,?,?)""",
                    (sol_numero, it['codigo'], it['nombre'],
                     it['deficit_g'], 'g', just))
                try:
                    conn.execute("""INSERT INTO ordenes_compra_items
                        (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
                        VALUES (?,?,?,?,0,0)""",
                        (num_oc, it['codigo'], it['nombre'], it['deficit_g']))
                except sqlite3.OperationalError:
                    pass
                items_created_this.append({
                    'codigo': it['codigo'],
                    'nombre': it['nombre'],
                    'deficit_g': round(it['deficit_g'], 1),
                })

            entry = {
                'solicitud': sol_numero,
                'orden_compra': num_oc,
                'proveedor': prov,
                'n_items': len(items_created_this),
                'items': items_created_this,
                'requiere_asignacion': es_sin_prov,
            }
            creadas.append(entry)
            if es_sin_prov:
                huerfana_info = entry

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': 'Falló la generación de OCs',
            'detalle': str(e),
        }), 500

    n_total_mps = sum(len(g) for g in grupos.values())
    n_proveedores = len([p for p in grupos.keys() if p != SIN_PROV])
    n_huerfanos = len(grupos.get(SIN_PROV, []))

    msg = f'{len(creadas)} solicitudes creadas — {n_total_mps} MPs en {n_proveedores} proveedores'
    if n_huerfanos:
        msg += f' + 1 solicitud SIN ASIGNAR ({n_huerfanos} MPs huérfanos para revisar)'

    return jsonify({
        'ok': True,
        'creadas': creadas,
        'total_solicitudes': len(creadas),
        'total_mps': n_total_mps,
        'proveedores_resueltos': n_proveedores,
        'mps_huerfanos': n_huerfanos,
        'huerfana': huerfana_info,
        'mensaje': msg,
    })


@bp.route('/api/programacion/mps-deficit')
def prog_mps_deficit():
    """Lista plana de MPs con déficit real según Centro de Programación.

    A diferencia de /api/alertas-reabastecimiento (que compara stock_actual
    < stock_minimo y depende de un campo desactualizado), esta calcula
    déficit REAL: necesidad para producciones futuras + velocidad de ventas
    proyectada vs stock actual.

    Cada item: codigo_mp, nombre, stock_actual_g, deficit_g, productos_afectados,
                proveedor, lead_time_estimado.
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    conn = get_db()
    try:
        china_mps_set = _get_china_mps(conn)
        # Misma fuente de verdad que /generar-oc y /planificacion
        mp_def_raw = _compute_mp_deficit_aggregated(conn, days_ahead=90)
        if not mp_def_raw:
            return jsonify({'mps': [], 'total': 0, 'deficit_total_kg': 0})

        items = []
        for mid, info in mp_def_raw.items():
            items.append({
                'codigo_mp': mid,
                'nombre': info['nombre'],
                'stock_actual_g': info['stock_g'],
                'deficit_g': info['deficit_g'],
                'productos_afectados': info['productos'],
                'es_china': mid in china_mps_set,
                'proveedor': info.get('proveedor', ''),
            })
        items.sort(key=lambda x: -x['deficit_g'])
        deficit_total_kg = sum(i['deficit_g'] for i in items) / 1000.0

        return jsonify({
            'mps': items,
            'total': len(items),
            'deficit_total_kg': round(deficit_total_kg, 2),
            'china_count': sum(1 for i in items if i.get('es_china')),
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()[-500:],
            'mps': [],
            'total': 0,
        }), 500


@bp.route('/api/programacion/n-alertas')
def prog_n_alertas():
    """Endpoint rápido — retorna solo el conteo de alertas (para badge en Compras)."""
    if not _auth():
        return jsonify({'n': 0})
    conn = get_db()
    try:
        vel_data = _shopify_velocity(conn, days=60)
        mp_stock = _get_mp_stock(conn)
        formulas = _get_formulas(conn)
        if not formulas:
            return jsonify({'n': 0, 'criticos': 0})
        _, alerts = _project_stock(
            conn, vel_data['prod_velocity'], formulas, mp_stock, []
        )
        criticos = len([a for a in alerts if a['nivel'] == 'critico'])
        return jsonify({'n': len(alerts), 'criticos': criticos})
    except Exception as e:
        return jsonify({'n': 0, 'error': str(e)})


@bp.route('/api/programacion/debug-mps')
def prog_debug_mps():
    """Debug: cross-reference mp_stock entries vs formula_items material_ids."""
    if not _auth():
        return jsonify({'error': 'no auth'}), 401
    conn = get_db()

    # MP stock from movimientos
    mp_stock = _get_mp_stock(conn)

    # All material_ids used in formulas
    formula_mids = conn.execute(
        "SELECT DISTINCT material_id, material_nombre FROM formula_items ORDER BY material_id"
    ).fetchall()

    matched   = []
    unmatched = []
    for mid, nombre in formula_mids:  # nombre = material_nombre
        # Try: unlimited → ID → exact name → norm name → alias
        nombre_str = str(nombre or '')
        if _is_unlimited_mp(nombre_str):
            stock = float('inf')
            match_via = 'unlimited'
        elif mid in mp_stock:
            stock = mp_stock[mid]
            match_via = 'id'
        else:
            nombre_exact = nombre_str.strip().upper()
            if nombre_exact in mp_stock:
                stock = mp_stock[nombre_exact]
                match_via = 'nombre_exact'
            else:
                nombre_norm = _norm_mp_name(nombre_str)
                if nombre_norm in mp_stock:
                    stock = mp_stock[nombre_norm]
                    match_via = 'nombre_norm'
                else:
                    alias_key = _MP_NAME_ALIAS.get(nombre_norm) or _MP_NAME_ALIAS.get(nombre_exact)
                    if alias_key and alias_key in mp_stock:
                        stock = mp_stock[alias_key]
                        match_via = 'alias'
                    else:
                        stock = None
                        match_via = None

        if stock is not None:
            matched.append({'material_id': mid, 'nombre': nombre,
                            'stock_g': round(stock, 1), 'match_via': match_via})
        else:
            unmatched.append({'material_id': mid, 'nombre': nombre})

    # Sample mp_stock keys (first 20)
    sample_stock_keys = sorted(mp_stock.keys())[:20]

    # Movimientos table row count
    n_mov = conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]

    # Check if movimientos has any 'entrada' tipo
    n_entradas = conn.execute(
        "SELECT COUNT(*) FROM movimientos WHERE tipo IN ('entrada','Entrada','ENTRADA')"
    ).fetchone()[0]

    # Search mp_stock for critical keywords
    keywords = ['AGUA', 'ALOE', 'ARGAN', 'JOJOBA', 'ASCORBICO', 'FERULICO',
                'PANTENOL', 'CETILICO', 'CETEARIL', 'ROSA MOSQUETA',
                'ACETIL', 'ACETYL', 'HIALURONICO',
                'SILICONA', 'EZ', 'REGALIZ', 'GLYCYRRHIZA', 'LICORICE',
                'CENTELLA', 'PROPILEN', 'CARBOPOL', 'CAFEINA', 'CERAMIDA',
                'BETAGLUCAN', 'BACKUCHIOL', 'NIACINAMIDA', 'RETINOL']
    keyword_hits = {}
    for kw in keywords:
        hits = [k for k in mp_stock if kw in k]
        if hits:
            keyword_hits[kw] = hits[:5]

    # Show normalized form of unmatched names for debugging
    unmatched_with_norm = []
    for item in unmatched:
        norm_key = _norm_mp_name(item['nombre'])
        in_stock = norm_key in mp_stock
        unmatched_with_norm.append({**item, 'norm_key': norm_key, 'norm_in_stock': in_stock})

    return jsonify({
        'mp_stock_total_entries': len(mp_stock),
        'mp_stock_sample_keys': sample_stock_keys,
        'formula_items_distinct_materials': len(formula_mids),
        'matched_count': len(matched),
        'unmatched_count': len(unmatched),
        'unmatched': unmatched_with_norm[:30],
        'matched_sample': matched[:10],
        'movimientos_total_rows': n_mov,
        'movimientos_entradas': n_entradas,
        'keyword_hits_in_stock': keyword_hits,
    })


@bp.route('/api/programacion/debug-mp-check/<producto>')
def prog_debug_mp_check(producto):
    """Debug: muestra el mp_check completo para un producto específico."""
    if not _auth():
        return jsonify({'error': 'no auth'}), 401
    conn = get_db()
    mp_stock = _get_mp_stock(conn)
    formulas = _get_formulas(conn)

    prod_key = None
    for k in formulas:
        if k.upper() == producto.upper() or producto.upper() in k.upper():
            prod_key = k
            break

    if not prod_key:
        available = list(formulas.keys())
        return jsonify({'error': f'Producto no encontrado', 'disponibles': available[:20]}), 404

    data = formulas[prod_key]
    lote_kg = data.get('lote_size_kg') or 1.0
    items = data.get('items', [])
    items_with_qty = [i for i in items if i.get('cantidad_g_por_lote', 0) > 0]

    result = []
    for item in items_with_qty:
        mid = str(item['material_id']).strip()
        nombre_raw = str(item.get('material_nombre', '')).strip()
        needed_g = float(item['cantidad_g_por_lote'])

        # Mirror exact lookup logic from _project_stock
        if _is_unlimited_mp(nombre_raw):
            available_g = float('inf')
            match_via = 'unlimited'
        elif mid in mp_stock:
            available_g = mp_stock[mid]
            match_via = 'id'
        else:
            nombre_exact = nombre_raw.upper()
            if nombre_exact in mp_stock:
                available_g = mp_stock[nombre_exact]
                match_via = 'nombre_exact'
            else:
                nombre_norm = _norm_mp_name(nombre_raw)
                if nombre_norm in mp_stock:
                    available_g = mp_stock[nombre_norm]
                    match_via = 'nombre_norm'
                else:
                    alias_key = _MP_NAME_ALIAS.get(nombre_norm) or _MP_NAME_ALIAS.get(nombre_exact)
                    if alias_key and alias_key in mp_stock:
                        available_g = mp_stock[alias_key]
                        match_via = f'alias→{alias_key}'
                    else:
                        available_g = 0
                        match_via = 'NOT_FOUND'

        deficit_g = 0 if available_g == float('inf') else max(0, needed_g - available_g)
        ok = deficit_g < 1
        result.append({
            'material_id': mid,
            'nombre': nombre_raw,
            'needed_g': round(needed_g, 1),
            'available_g': '∞' if available_g == float('inf') else round(available_g, 1),
            'deficit_g': round(deficit_g, 1),
            'ok': ok,
            'match_via': match_via,
        })

    result.sort(key=lambda x: (x['ok'], -x['deficit_g']))  # failing first
    failing = [r for r in result if not r['ok']]
    return jsonify({
        'producto': prod_key,
        'lote_kg': lote_kg,
        'total_ingredientes': len(result),
        'ingredientes_faltantes': len(failing),
        'can_produce': len(failing) == 0,
        'failing_first': result,
    })


# ─── MP Bridge — admin endpoints ─────────────────────────────────────────────

@bp.route('/api/programacion/mp-bridge', methods=['GET'])
def mp_bridge_list():
    """List all bridge mappings (active and inactive)."""
    with _db() as conn:
        rows = conn.execute("""
            SELECT id, formula_material_id, formula_material_nombre,
                   bodega_material_id, bodega_material_nombre, bodega_inci,
                   notas, activo, creado_en
            FROM mp_formula_bridge
            ORDER BY formula_material_nombre NULLS LAST
        """).fetchall()
        keys = ['id', 'formula_material_id', 'formula_material_nombre',
                'bodega_material_id', 'bodega_material_nombre', 'bodega_inci',
                'notas', 'activo', 'creado_en']
        return jsonify([dict(zip(keys, r)) for r in rows])


@bp.route('/api/programacion/mp-bridge', methods=['POST'])
def mp_bridge_add():
    """Add or update a bridge mapping.

    Body JSON: {
        formula_material_id, formula_material_nombre,
        bodega_material_id, bodega_material_nombre, bodega_inci, notas
    }
    """
    data = request.get_json(force=True) or {}
    fid   = str(data.get('formula_material_id', '') or '').strip()
    fname = str(data.get('formula_material_nombre', '') or '').strip()
    bid   = str(data.get('bodega_material_id', '') or '').strip()
    bname = str(data.get('bodega_material_nombre', '') or '').strip()
    binci = str(data.get('bodega_inci', '') or '').strip()
    notas = str(data.get('notas', '') or '').strip()

    if not fid or not bid:
        return jsonify({'error': 'formula_material_id y bodega_material_id son obligatorios'}), 400

    with _db() as conn:
        conn.execute("""
            INSERT INTO mp_formula_bridge
                (formula_material_id, formula_material_nombre,
                 bodega_material_id, bodega_material_nombre, bodega_inci, notas, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(formula_material_id, bodega_material_id)
            DO UPDATE SET
                formula_material_nombre = excluded.formula_material_nombre,
                bodega_material_nombre  = excluded.bodega_material_nombre,
                bodega_inci             = excluded.bodega_inci,
                notas                   = excluded.notas,
                activo                  = 1
        """, (fid, fname or None, bid, bname or None, binci or None, notas or None))
        conn.commit()
    return jsonify({'ok': True, 'formula_material_id': fid, 'bodega_material_id': bid})


@bp.route('/api/programacion/mp-bridge/<int:bridge_id>', methods=['DELETE'])
def mp_bridge_delete(bridge_id):
    """Soft-delete a bridge mapping (sets activo=0)."""
    with _db() as conn:
        conn.execute("UPDATE mp_formula_bridge SET activo=0 WHERE id=?", (bridge_id,))
        conn.commit()
    return jsonify({'ok': True, 'id': bridge_id, 'activo': 0})


@bp.route('/api/programacion/mp-bridge/unmatched', methods=['GET'])
def mp_bridge_unmatched():
    """Return formula_items that cannot be matched to any movimientos entry.

    Useful for populating the bridge table: shows what still needs linking,
    along with candidate bodega materials (fuzzy name match by keywords).
    """
    with _db() as conn:
        mp_stock = _get_mp_stock(conn)

        # All bridge mappings already in place (formula_material_id → bodega_material_id)
        bridged_fids = set(r[0] for r in conn.execute(
            "SELECT formula_material_id FROM mp_formula_bridge WHERE activo=1"
        ).fetchall())

        # Fetch distinct formula items (one entry per material_id)
        items = conn.execute("""
            SELECT DISTINCT material_id, material_nombre
            FROM formula_items
            WHERE material_id IS NOT NULL AND material_id != ''
            ORDER BY material_nombre
        """).fetchall()

        # Fetch all bodega materials for candidate suggestions
        bodega_mats = conn.execute("""
            SELECT DISTINCT material_id, material_nombre
            FROM movimientos
            WHERE material_id IS NOT NULL AND material_id != ''
              AND material_nombre IS NOT NULL AND material_nombre != ''
            ORDER BY material_nombre
        """).fetchall()

        unmatched = []
        for mid, nombre in items:
            mid = str(mid or '').strip()
            nombre_raw = str(nombre or '').strip()

            # Skip already bridged
            if mid in bridged_fids:
                continue
            # Skip unlimited MPs
            if _is_unlimited_mp(nombre_raw):
                continue
            # Check if already matched via stock dict
            nombre_exact = nombre_raw.upper()
            nombre_norm  = _norm_mp_name(nombre_raw)
            alias_key    = _MP_NAME_ALIAS.get(nombre_norm) or _MP_NAME_ALIAS.get(nombre_exact)

            already_matched = (
                mid in mp_stock
                or nombre_exact in mp_stock
                or nombre_norm in mp_stock
                or (alias_key and alias_key in mp_stock)
            )
            if already_matched:
                continue

            # Build candidate suggestions: bodega materials whose normalized name
            # shares at least one 4-char keyword with the formula material name
            formula_keywords = set(w for w in nombre_norm.split() if len(w) >= 4)
            candidates = []
            for bid, bname in bodega_mats:
                bname_norm = _norm_mp_name(str(bname or ''))
                bname_words = set(w for w in bname_norm.split() if len(w) >= 4)
                shared = formula_keywords & bname_words
                if shared:
                    candidates.append({
                        'material_id': bid,
                        'material_nombre': bname,
                        'shared_keywords': sorted(shared),
                        'score': len(shared)
                    })
            candidates.sort(key=lambda x: -x['score'])

            unmatched.append({
                'formula_material_id':     mid,
                'formula_material_nombre': nombre_raw,
                'candidates':              candidates[:5]  # top 5 suggestions
            })

        return jsonify({
            'total_unmatched': len(unmatched),
            'unmatched': unmatched
        })


# ─── Planificación Estratégica ────────────────────────────────────────────────

@bp.route('/api/programacion/planificacion')
def planificacion_estrategica():
    """
    Proyección de MPs para 2, 6 o 12 meses basada en calendario de producción.
    Detecta déficits, oportunidades de compra en volumen e inteligencia de origen.
    """
    import datetime as _dt
    import re as _re

    # Aceptar ?dias=N (15/30/60/90/180/365) o ?meses=N (back-compat).
    # dias prevalece si esta presente.
    dias_param = request.args.get('dias')
    if dias_param:
        try:
            dias = max(1, min(int(dias_param), 365))
        except ValueError:
            dias = 60
        meses = max(1, dias // 31 + (1 if dias % 31 else 0))
    else:
        meses = min(int(request.args.get('meses', 2)), 12)
        dias = meses * 31
    days_ahead = dias  # cutoff exacto basado en dias del horizonte

    conn = get_db()

    # ── 1. Cargar datos base ──────────────────────────────────────────────────
    cal     = _fetch_calendar_events(days_ahead=days_ahead)
    events  = cal.get('events', [])
    formulas = _get_formulas(conn)
    mp_stock = _get_mp_stock(conn)

    # SKU → producto map
    _sku_to_prod = {}
    try:
        for row in conn.execute(
            "SELECT UPPER(sku), producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            _sku_to_prod[row[0]] = row[1]
    except Exception:
        pass

    # Proveedor map: material_id → proveedor
    _prov_map = {}
    try:
        for row in conn.execute(
            "SELECT codigo_mp, proveedor FROM maestro_mps WHERE proveedor IS NOT NULL AND proveedor != ''"
        ).fetchall():
            _prov_map[row[0]] = row[1]
    except Exception:
        pass

    # ── 2. Parsear eventos del calendario ────────────────────────────────────
    today = _dt.date.today()
    cutoff = today + _dt.timedelta(days=days_ahead)

    _NOT_SKU = {
        'FAB','QC','CON','SIN','MICRO','ENVASADO','ACONDICIONAMIENTO',
        'FABRICACION','FABRICACIÓN','LANZAMIENTO','PRODUCCION','PRODUCCIÓN',
        'KG','MES','DIAS','DÍAS','ML','UDS','BATCH','FERNANDO',
        'MESA','LOTES','LOTE','MINI','MACRO','AND','THE','FOR'
    }

    def _skus(titulo):
        tokens = _re.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in _NOT_SKU]

    def _kg_ev(titulo):
        m = _re.findall(r'~?(\d+(?:[,.]\d+)*)\s*kg', titulo, _re.IGNORECASE)
        if not m: return None
        try: return float(m[-1].replace(',', '.'))
        except: return None

    # Producciones planificadas: lista de {fecha, producto, kg, mes_label}
    producciones = []
    seen_events = set()

    # ── 2a. Fuente primaria: Google Calendar / iCal ───────────────────────
    for ev in events:
        titulo   = ev.get('titulo', '')
        fecha_s  = ev.get('fecha', '')
        if not fecha_s: continue
        try:
            fecha = _dt.date.fromisoformat(fecha_s)
        except ValueError:
            continue
        if fecha < today or fecha > cutoff:
            continue

        key = (titulo.strip(), fecha_s)
        if key in seen_events:
            continue
        seen_events.add(key)

        # ── Phase filter: skip non-Fabricación events ──────────────────────
        # Envasado / Acondicionamiento / QC no consumen MPs crudas.
        # Contarlos duplica/triplica los requerimientos (infla 2-3×).
        _NON_FAB_KW = {
            'envasado', 'acondicionamiento', 'micro qc',
            'control de calidad', 'dispensado', 'etiquetado', 'llenado',
        }
        if any(kw in titulo.lower() for kw in _NON_FAB_KW):
            continue

        kg = _kg_ev(titulo)
        for sku in _skus(titulo):
            prod = _sku_to_prod.get(sku)
            if prod and prod in formulas:
                mes_label = fecha.strftime('%Y-%m')
                producciones.append({
                    'fecha': fecha_s,
                    'mes':   mes_label,
                    'producto': prod,
                    'kg': kg or formulas[prod]['lote_size_kg'],
                    'sku': sku,
                    'titulo': titulo,
                    'fuente': 'calendario',
                })
                break

    # ── 2b. Fuente secundaria: produccion_programada (DB local, MANUALES) ─
    # Complementa cuando el calendario no tiene eventos o no hay SKUs en títulos.
    # IMPORTANTE: filtramos origen='calendar' (filas auto-sync) para evitar
    # duplicados — esas ya se procesan en 2a directamente del calendar source.
    # Solo manuales (origen='manual' o NULL).
    _upper_to_prod = {p.upper(): p for p in formulas.keys()}
    try:
        local_rows = conn.execute(
            """SELECT producto, fecha_programada, lotes FROM produccion_programada
               WHERE estado NOT IN ('completado','cancelado')
                 AND fecha_programada >= date('now', '-7 days')
                 AND fecha_programada <= ?
                 AND COALESCE(origen,'manual') != 'calendar'
               ORDER BY fecha_programada""",
            (cutoff.isoformat(),)
        ).fetchall()
        for row in local_rows:
            prod_raw = (row[0] or '').strip()
            fecha_s  = (row[1] or '').strip()
            lotes    = int(row[2] or 1)
            prod = prod_raw if prod_raw in formulas else _upper_to_prod.get(prod_raw.upper())
            if not prod or not fecha_s:
                continue
            key = (prod, fecha_s)
            if key in seen_events:
                continue
            seen_events.add(key)
            try:
                fecha = _dt.date.fromisoformat(fecha_s)
            except ValueError:
                continue
            lote_kg = formulas[prod]['lote_size_kg']
            mes_label = fecha.strftime('%Y-%m')
            producciones.append({
                'fecha': fecha_s,
                'mes': mes_label,
                'producto': prod,
                'kg': lote_kg * lotes,
                'sku': '',
                'titulo': f'{prod} — {lotes} lote(s)',
                'fuente': 'local',
            })
    except Exception:
        pass

    # ── 3. Calcular MPs necesarias por producción ────────────────────────────
    # mp_needed: {material_id: {nombre, total_g, meses: set(), prods: list}}
    mp_needed = {}

    # Helper de stock antes del loop para reusarlo en mps_status por-producción
    # Ahora con ROLLING STOCK: el stock se va decrementando a medida que las
    # producciones cronologicamente anteriores consumen MPs.
    # Bug fix 2026-04-28: antes evaluaba cada produccion contra el stock total,
    # asi que si dos producciones usaban la misma MP, ambas decian "puede"
    # aunque entre las dos no alcanzara el stock.
    def _lookup_stock_key(mid, nombre):
        """Devuelve la clave del dict mp_stock usada para este MP, o None
        si no se encuentra. Permite decrementar el stock simulado en la
        clave correcta despues."""
        if _is_unlimited_mp(nombre):
            return None  # ilimitado, no decrementar
        for k in (mid, mid.upper(), nombre.upper(), _norm_mp_name(nombre)):
            if k in stock_simulado:
                return k
        return None

    def _lookup_stock(mid, nombre):
        """Devuelve stock simulado actual del MP. -1 si es ilimitado."""
        if _is_unlimited_mp(nombre):
            return -1
        k = _lookup_stock_key(mid, nombre)
        if k is None:
            return 0
        return stock_simulado[k]

    # Stock simulado: copia mutable del stock real que se decrementa a
    # medida que avanzan las producciones cronologicas.
    stock_simulado = dict(mp_stock)

    # ORDEN CRITICO: las producciones DEBEN evaluarse en orden cronologico
    # para que el rolling stock tenga sentido.
    producciones.sort(key=lambda p: (p.get('fecha', ''), p.get('producto', '')))

    for prod_ev in producciones:
        prod   = prod_ev['producto']
        kg_ev  = prod_ev['kg']
        mes    = prod_ev['mes']
        formula = formulas.get(prod, {})
        lote_kg = formula.get('lote_size_kg', 1)
        factor  = kg_ev / lote_kg if lote_kg > 0 else 1.0

        # Per-producción MP status — evalua contra stock_simulado actual.
        # Si esta produccion alcanza, decrementa stock_simulado para la
        # siguiente produccion cronologica.
        mps_status = []
        n_alcanza = 0
        n_falta   = 0
        decrementos_si_alcanza = []  # (key, g_need) para aplicar al final

        for item in formula.get('items', []):
            mid    = item['material_id']
            nombre = item['material_nombre']
            g_lote = item.get('cantidad_g_por_lote', 0)
            g_need = round(g_lote * factor, 1)

            if mid not in mp_needed:
                mp_needed[mid] = {
                    'material_id': mid,
                    'nombre': nombre,
                    'total_g': 0,
                    'por_mes': {},   # mes_label → g
                    'productos': [],
                }
            mp_needed[mid]['total_g'] += g_need
            mp_needed[mid]['por_mes'][mes] = mp_needed[mid]['por_mes'].get(mes, 0) + g_need
            if prod not in mp_needed[mid]['productos']:
                mp_needed[mid]['productos'].append(prod)

            # Status individual para esta producción usando stock SIMULADO
            stock_g_raw = _lookup_stock(mid, nombre)
            stock_key   = _lookup_stock_key(mid, nombre)

            if stock_g_raw == -1:
                # Ilimitado (agua, etc.) — siempre alcanza, no decrementa
                mps_status.append({
                    'material_id': mid, 'nombre': nombre,
                    'necesario_g': g_need, 'stock_g': -1,
                    'alcanza': True, 'deficit_g': 0,
                    'ilimitado': True,
                })
                n_alcanza += 1
            else:
                alcanza = stock_g_raw >= g_need
                mps_status.append({
                    'material_id': mid, 'nombre': nombre,
                    'necesario_g': g_need, 'stock_g': round(stock_g_raw, 1),
                    'alcanza': alcanza,
                    'deficit_g': round(max(0, g_need - stock_g_raw), 1),
                    'ilimitado': False,
                })
                if alcanza:
                    n_alcanza += 1
                    if stock_key is not None:
                        decrementos_si_alcanza.append((stock_key, g_need))
                else:
                    n_falta += 1

        # Solo decrementar stock_simulado si TODAS las MPs alcanzan
        # (de lo contrario la produccion no se va a hacer y no se consume nada).
        puede_producir = (n_falta == 0)
        if puede_producir:
            for k, g in decrementos_si_alcanza:
                stock_simulado[k] = max(0, stock_simulado.get(k, 0) - g)

        prod_ev['mps_status']    = mps_status
        prod_ev['n_mps_alcanza'] = n_alcanza
        prod_ev['n_mps_falta']   = n_falta
        prod_ev['puede_producir'] = puede_producir

    # ── 4. Cruzar con stock actual → déficit ────────────────────────────────

    resultado = []
    for mid, data in mp_needed.items():
        stock_g_raw = _lookup_stock(mid, data['nombre'])
        if stock_g_raw == -1:
            # Producido en sitio (agua desionizada, etc.) — sin déficit, sin compra
            continue
        stock_g   = stock_g_raw
        deficit   = max(0, data['total_g'] - stock_g)
        cobertura = round(min(stock_g / data['total_g'] * 100, 100), 1) if data['total_g'] > 0 else 100
        meses_uso = sorted(data['por_mes'].keys())
        n_meses   = len(meses_uso)
        proveedor = _prov_map.get(mid, '')

        # ── Inteligencia de origen ──────────────────────────────────────────
        # Palabras clave que sugieren origen China / importación directa
        _CHINA_KEYWORDS = {'lyphar','tianki','bloomage','sinomax','croda','basf','evonik',
                           'givaudan','dsm','lubrizol','ashland','clariant','solvay',
                           'chinese','china','guangzhou','shanghai','beijing'}
        _COL_KEYWORDS   = {'inchemical','en qu','quiminet','prodycon','corquiven','quimicos',
                           'colombia','agenquimicos','ytbio','bolite','laboratorios','bogota',
                           'medellin','cali','distribuidora'}
        prov_lower = proveedor.lower()
        is_china   = any(k in prov_lower for k in _CHINA_KEYWORDS) or mid.startswith('MP001') or mid.startswith('MP002')
        is_col     = any(k in prov_lower for k in _COL_KEYWORDS)

        # Oportunidad de bulk: si se usa en 3+ meses consecutivos
        bulk_opp = False
        bulk_msg = ''
        if n_meses >= 2:
            bulk_opp = True
            _qty = f'{int(round(data["total_g"])):,} g'.replace(',', '.')
            if is_china:
                bulk_msg = f'Importar {_qty} en un solo pedido desde proveedor internacional — ahorro estimado 15-25% en flete'
            else:
                bulk_msg = f'Pedir {_qty} para {n_meses} meses a proveedor local — negociar descuento por volumen'

        resultado.append({
            'material_id':  mid,
            'nombre':       data['nombre'],
            'proveedor':    proveedor,
            'total_g':      round(data['total_g'], 1),
            'stock_g':      round(stock_g, 1),
            'deficit_g':    round(deficit, 1),
            'cobertura_pct': cobertura,
            'meses_uso':    meses_uso,
            'n_meses':      n_meses,
            'productos':    data['productos'],
            'bulk_opp':     bulk_opp,
            'bulk_msg':     bulk_msg,
            'origen':       'china' if is_china else ('colombia' if is_col else 'desconocido'),
        })

    # Ordenar: déficit primero, luego por total requerido
    resultado.sort(key=lambda x: (-x['deficit_g'], -x['total_g']))

    # ── 5. Resumen ejecutivo ─────────────────────────────────────────────────
    total_prods   = len(producciones)
    total_mps     = len(resultado)
    mps_deficit   = [r for r in resultado if r['deficit_g'] > 0]
    mps_ok        = [r for r in resultado if r['deficit_g'] == 0]
    bulk_opps     = [r for r in resultado if r['bulk_opp'] and r['deficit_g'] > 0]
    meses_unicos  = sorted(set(p['mes'] for p in producciones))

    horizonte_label = (f'{dias} días' if dias <= 90 else
                       f'{round(dias/30)} meses' if dias < 365 else '1 año')

    return jsonify({
        'meses':           meses,
        'dias':            dias,
        'horizonte_label': horizonte_label,
        'producciones':    producciones,
        'meses_unicos':    meses_unicos,
        'total_prods':     total_prods,
        'total_mps':       total_mps,
        'mps_deficit':     mps_deficit,
        'mps_ok':          mps_ok,           # staff general view
        'mps_ok_count':    len(mps_ok),
        'bulk_opps':       bulk_opps,
        'cal_error':       cal.get('error'),
        'generado_en':     _dt.datetime.now().isoformat(),
    })


@bp.route('/api/programacion/planificacion/solicitar-bulk', methods=['POST'])
def planificacion_solicitar_bulk():
    """Crea solicitudes_compra agrupadas por proveedor para los MPs en
    deficit del horizonte indicado.

    Una solicitud por proveedor con todos sus MPs faltantes. Texto
    auto-generado deja claro que fue creada por planificacion bulk.

    Body:
      dias: int (15/30/60/90/180/365)
      urgencia: 'Alta'|'Normal'|'Baja' (default 'Normal')

    Reusa la logica del GET planificacion para no duplicar matemathics.

    Solo autenticado (cualquier user puede crear solicitud — es flujo
    operativo). Audit log captura accion.
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    user = session.get('compras_user', '') or 'sistema'

    d = request.json or {}
    try:
        dias = max(1, min(int(d.get('dias', 60)), 365))
    except ValueError:
        dias = 60
    urgencia = (d.get('urgencia') or 'Normal').strip()
    if urgencia not in ('Alta', 'Normal', 'Baja'):
        urgencia = 'Normal'

    # Llamar el endpoint de planificacion via test_request_context — pero
    # mejor reusar la logica directa para no enredar.
    from flask import current_app
    with current_app.test_request_context(f'/api/programacion/planificacion?dias={dias}'):
        plan_resp = planificacion_estrategica()
    plan_data = plan_resp.get_json()
    if not plan_data:
        return jsonify({'error': 'No pude obtener planificacion'}), 500

    deficits = plan_data.get('mps_deficit', []) or []
    if not deficits:
        return jsonify({
            'ok': True,
            'mensaje': 'Sin déficits — no hay nada que pedir.',
            'solicitudes_creadas': [],
        })

    # Agrupar por proveedor canónico (el de maestro_mps)
    por_proveedor = {}
    for mp in deficits:
        prov = (mp.get('proveedor') or '(SIN PROVEEDOR)').strip() or '(SIN PROVEEDOR)'
        por_proveedor.setdefault(prov, []).append(mp)

    conn = get_db()
    c = conn.cursor()
    from datetime import datetime as _dt

    solicitudes_creadas = []
    errores = []
    for prov, mps in por_proveedor.items():
        try:
            # Generar numero
            year = _dt.now().strftime('%Y')
            row = c.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) "
                "FROM solicitudes_compra WHERE numero LIKE ?",
                (f'SOL-{year}-%',)
            ).fetchone()
            num = (row[0] or 0) + 1
            numero = f'SOL-{year}-{num:04d}'

            obs = (f'Auto-generada Planificación Estratégica {dias} días — '
                   f'Proveedor: {prov} · {len(mps)} MPs · ' +
                   ', '.join([
                       f'{m["nombre"]} ({int(round(m["deficit_g"])):,} g)'.replace(',', '.')
                       for m in mps[:5]
                   ]) +
                   (f' +{len(mps)-5} más' if len(mps) > 5 else ''))[:1500]

            c.execute(
                """INSERT INTO solicitudes_compra
                   (numero, fecha, estado, solicitante, urgencia, observaciones,
                    area, empresa, categoria, tipo)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (numero, _dt.now().isoformat(), 'Pendiente', user, urgencia,
                 obs, 'Produccion', 'Espagiria', 'Materia Prima', 'Compra')
            )
            for mp in mps:
                c.execute(
                    """INSERT INTO solicitudes_compra_items
                       (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                        justificacion, valor_estimado)
                       VALUES (?,?,?,?,?,?,?)""",
                    (numero, mp.get('material_id', ''), mp.get('nombre', ''),
                     float(mp.get('deficit_g', 0)), 'g',
                     f'Déficit horizonte {dias}d (Planificación Estratégica)',
                     0)
                )
            conn.commit()
            solicitudes_creadas.append({
                'numero': numero,
                'proveedor': prov,
                'count_mps': len(mps),
                'total_g': round(sum(m.get('deficit_g', 0) for m in mps), 1),
            })
        except Exception as _e:
            try: conn.rollback()
            except Exception: pass
            errores.append({'proveedor': prov, 'error': str(_e)})
            continue

    # Audit
    try:
        import json as _json
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (user, 'PLANIFICACION_BULK_REQUEST', 'solicitudes_compra',
                   '_BULK_',
                   _json.dumps({
                       'dias': dias, 'urgencia': urgencia,
                       'count_solicitudes': len(solicitudes_creadas),
                       'count_errores': len(errores),
                       'total_g_pedido': round(sum(
                           s['total_g'] for s in solicitudes_creadas
                       ), 1),
                   }, ensure_ascii=False),
                   request.remote_addr))
        conn.commit()
    except sqlite3.OperationalError:
        pass

    return jsonify({
        'ok': True,
        'horizonte_dias': dias,
        'count_solicitudes': len(solicitudes_creadas),
        'count_errores': len(errores),
        'solicitudes_creadas': solicitudes_creadas,
        'errores': errores,
        'mensaje': (
            f'{len(solicitudes_creadas)} solicitudes creadas '
            f'(una por proveedor) para horizonte {dias} días.'
        ),
    })


@bp.route('/api/programacion/planificacion/checklist-verificacion')
def planificacion_checklist_verificacion():
    """Genera XLSX con MPs reportadas en STOCK CERO por horizonte para que
    la asistente verifique fisicamente en bodega si estan o no.

    Query params:
      horizontes: csv de dias (default '15,30'). Cada uno es una hoja.

    Cada hoja incluye:
      - Material, Codigo, Proveedor, Necesario (g/kg), Para Producto(s)
      - Casillas vacias: 'En bodega? (S/N)', 'Cantidad real (g)', 'Notas'
      - Solo MPs con stock_g <= 0 (las que parcialmente tienen stock no
        van — ya sabemos que existen, solo falta cantidad)

    Auth requerida.
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    horizontes_param = request.args.get('horizontes', '15,30')
    horizontes = []
    for h in horizontes_param.split(','):
        h = h.strip()
        if not h: continue
        try:
            v = max(1, min(int(h), 365))
            if v not in horizontes:
                horizontes.append(v)
        except ValueError:
            continue
    if not horizontes:
        horizontes = [15, 30]

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({'error': 'openpyxl no disponible'}), 500

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # quitar hoja por defecto

    from flask import current_app, send_file
    import io

    thin = Side(border_style='thin', color='CCCCCC')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill   = PatternFill('solid', fgColor='1A4A7A')
    title_fill    = PatternFill('solid', fgColor='1A4A7A')
    alt_fill      = PatternFill('solid', fgColor='F8F9FA')
    warn_fill     = PatternFill('solid', fgColor='FFF3CD')

    total_en_cero = 0
    for dias in horizontes:
        with current_app.test_request_context(f'/api/programacion/planificacion?dias={dias}'):
            plan_resp = planificacion_estrategica()
        plan_data = plan_resp.get_json() or {}
        deficits = plan_data.get('mps_deficit', []) or []
        en_cero = [mp for mp in deficits if (mp.get('stock_g') or 0) <= 0]
        # Ordenar por necesario desc
        en_cero.sort(key=lambda m: -(m.get('total_g') or 0))
        total_en_cero += len(en_cero)

        # Etiqueta de hoja: '15 dias' / '1 mes' / '60 dias' etc
        if dias == 15:    sheet_name = '15 dias'
        elif dias == 30:  sheet_name = '1 mes'
        elif dias == 60:  sheet_name = '2 meses'
        elif dias == 90:  sheet_name = '3 meses'
        elif dias == 180: sheet_name = '6 meses'
        elif dias == 365: sheet_name = '1 ano'
        else:             sheet_name = f'{dias} dias'

        ws = wb.create_sheet(sheet_name)

        # Titulo
        ws.cell(row=1, column=1, value=f'Lista de verificacion de bodega — Horizonte {sheet_name}')
        ws.cell(row=1, column=1).font = Font(size=14, bold=True, color='FFFFFF')
        ws.cell(row=1, column=1).fill = title_fill
        ws.cell(row=1, column=1).alignment = Alignment(horizontal='left', vertical='center')
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
        ws.row_dimensions[1].height = 24

        # Subtitulo
        gen = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws.cell(row=2, column=1,
                value=f'Generado: {gen} · {len(en_cero)} MP(s) reportada(s) en STOCK CERO por sistema · Verificar fisicamente en bodega y marcar.')
        ws.cell(row=2, column=1).font = Font(size=10, italic=True, color='666666')
        ws.cell(row=2, column=1).fill = warn_fill
        ws.cell(row=2, column=1).alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
        ws.row_dimensions[2].height = 30

        # Nota: hint sobre duplicados
        ws.cell(row=3, column=1,
                value='OJO: Si un material no esta bajo el codigo indicado, busca por NOMBRE — puede estar bajo codigo distinto. Anota lo que encuentres en "Notas".')
        ws.cell(row=3, column=1).font = Font(size=9, color='856404')
        ws.cell(row=3, column=1).alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=7)
        ws.row_dimensions[3].height = 20

        # Headers — todo en gramos (acordado con Alejandro)
        headers = [
            'Material', 'Codigo', 'Proveedor',
            'Necesario (g)',
            'Para producto(s)',
            'En bodega? (S/N)', 'Cantidad real (g)',
        ]
        for i, h in enumerate(headers, 1):
            cell = ws.cell(row=5, column=i, value=h)
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = border
        ws.row_dimensions[5].height = 32

        # Filas
        if en_cero:
            for idx, mp in enumerate(en_cero, 6):
                nec_g = float(mp.get('total_g') or 0)
                values = [
                    mp.get('nombre', ''),
                    mp.get('material_id', ''),
                    mp.get('proveedor', '') or '(Sin asignar)',
                    int(round(nec_g)),
                    ', '.join(mp.get('productos', []) or []),
                    '',  # asistente marca S/N
                    '',  # cantidad real
                ]
                for j, v in enumerate(values, 1):
                    cell = ws.cell(row=idx, column=j, value=v)
                    cell.border = border
                    cell.alignment = Alignment(
                        horizontal='right' if j == 4 else ('center' if j == 6 else 'left'),
                        vertical='center', wrap_text=(j == 5),
                    )
                    if j == 4:  # cantidad necesaria con separador de miles
                        cell.number_format = '#,##0'
                    if (idx - 6) % 2 == 1:
                        cell.fill = alt_fill
                    if j == 2:  # codigo monoespaciado
                        cell.font = Font(name='Consolas', size=9)
                # Resaltar columnas de verificacion
                ws.cell(row=idx, column=6).fill = warn_fill
                ws.cell(row=idx, column=7).fill = warn_fill
        else:
            ws.cell(row=6, column=1, value='Sin MPs en stock cero para este horizonte')
            ws.cell(row=6, column=1).font = Font(italic=True, color='888888')
            ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=7)

        # Anchos columnas
        widths = [30, 16, 18, 14, 42, 16, 16]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # Freeze header
        ws.freeze_panes = 'A6'

    # Audit
    try:
        conn = get_db()
        c = conn.cursor()
        import json as _json
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (session.get('compras_user', '') or 'sistema',
                   'PLANIFICACION_CHECKLIST_DOWNLOAD',
                   'planificacion', '_CHECKLIST_',
                   _json.dumps({'horizontes': horizontes, 'total_en_cero': total_en_cero},
                               ensure_ascii=False),
                   request.remote_addr))
        conn.commit()
    except Exception:
        pass

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    fname = f'verificar_bodega_{"-".join(str(h) for h in horizontes)}d_{date.today().isoformat()}.xlsx'
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=fname,
    )


# ═════════════════════════════════════════════════════════════════════════
#  CHECKLIST PRE-PRODUCCION
#  Sistema que para cada produccion programada genera lista de items a
#  verificar con anticipacion: MPs, envases, tapas, etiquetas, serigrafia,
#  tampografia. Conecta con compras: si falta algo, genera SOL automatica.
# ═════════════════════════════════════════════════════════════════════════

ITEMS_CHECKLIST_DEFAULT = [
    ('envase_primario',  'Envase primario (frasco/contenedor)', 30, 1),
    ('tapa',             'Tapa o sistema dosificador',          30, 2),
    ('etiqueta_frontal', 'Etiqueta frontal',                    25, 3),
    ('etiqueta_posterior','Etiqueta posterior con info legal',  25, 4),
    ('caja_exterior',    'Caja exterior individual',            20, 5),
    ('serigrafia',       'Serigrafia en envase si aplica',      30, 6),
    ('tampografia',      'Tampografia en tapa si aplica',       30, 7),
]

# Tipos legacy que ya NO se generan ni muestran. La decoracion del envase
# (etiqueta_adhesiva / serigrafia / tampografia) cubre estas necesidades
# y crea las OCs/tareas operativas correspondientes desde Compras.
# Pedido Sebastian 2026-04-29: "quita lo de etiquetas frontales porque ya
# esta en el que sale". Si necesitas reactivarlas, vacia esta tupla.
TIPOS_LEGACY_OCULTOS = ('etiqueta_frontal', 'etiqueta_posterior', 'etiqueta_lateral')


def _calcular_disponibilidad_mp(c, codigo_mp, fecha_horizonte=None):
    """Calcula disponibilidad real de un MP considerando TODAS las
    producciones programadas hasta fecha_horizonte.

    Returns dict con:
      - stock_actual: gramos en bodega ahora (sumando movimientos)
      - en_transito: gramos en OCs activas no recibidas todavia
                     (Aprobada/Autorizada/Pagada categoria MP)
      - demanda_total_horizonte: gramos requeridos para TODAS las
                                 producciones programadas hasta fecha
      - solicitado_pendiente: gramos en SOLs activas (no convertidas a OC)
      - disponibilidad_neta: stock + en_transito - demanda
                             (si negativo, hay que solicitar)

    Esto resuelve la queja de Sebastian: el checklist NO debe ver una
    produccion en aislado, sino TODAS las del horizonte. Si la suma de
    demanda excede stock+transito, hay que pedir HOY aunque sea para
    una produccion de dentro de un mes.
    """
    if not codigo_mp:
        return {'stock_actual': 0, 'en_transito': 0,
                'demanda_total_horizonte': 0,
                'solicitado_pendiente': 0,
                'disponibilidad_neta': 0}
    out = {}
    # 1) Stock actual
    try:
        row = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +') THEN cantidad
                                     WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad
                                     ELSE 0 END), 0)
            FROM movimientos WHERE material_id=?
        """, (codigo_mp,)).fetchone()
        out['stock_actual'] = float(row[0] or 0)
    except Exception:
        out['stock_actual'] = 0.0

    # 2) En transito: OCs en estados activos no Recibida/Pagada
    # Sumamos cantidad_g de items de OCs en Borrador/Pendiente/Revisada/
    # Aprobada/Autorizada/Parcial. Pagada significa que se pago pero la
    # mercancia puede no haber llegado todavia, asi que tambien suma.
    try:
        row = c.execute("""
            SELECT COALESCE(SUM(i.cantidad_g - COALESCE(i.cantidad_recibida_g,0)), 0)
            FROM ordenes_compra_items i
            JOIN ordenes_compra oc ON oc.numero_oc = i.numero_oc
            WHERE i.codigo_mp = ?
              AND oc.estado IN ('Borrador','Pendiente','Revisada','Aprobada',
                                'Autorizada','Parcial','Pagada')
        """, (codigo_mp,)).fetchone()
        out['en_transito'] = float(row[0] or 0)
    except Exception:
        out['en_transito'] = 0.0

    # 3) En SOL pendientes (aun no convertidas a OC)
    try:
        row = c.execute("""
            SELECT COALESCE(SUM(si.cantidad_g), 0)
            FROM solicitudes_compra_items si
            JOIN solicitudes_compra s ON s.numero = si.numero
            WHERE si.codigo_mp = ?
              AND s.estado IN ('Pendiente','En revision','Aprobada')
              AND COALESCE(s.numero_oc, '') = ''
        """, (codigo_mp,)).fetchone()
        out['solicitado_pendiente'] = float(row[0] or 0)
    except Exception:
        out['solicitado_pendiente'] = 0.0

    # 4) Demanda total del horizonte: sumar de TODAS las producciones
    # programadas hasta fecha_horizonte cuyo formula_items incluya este MP.
    # produccion_programada tiene cols: producto, fecha_programada, lotes
    # cantidad_g real = fi.cantidad_g_por_lote * pp.lotes
    try:
        params = [codigo_mp]
        sql = """
            SELECT COALESCE(SUM(
                COALESCE(fi.cantidad_g_por_lote, 0) * COALESCE(pp.lotes, 1)
            ), 0) as demanda_g
            FROM produccion_programada pp
            JOIN formula_items fi ON fi.producto_nombre = pp.producto
            WHERE fi.material_id = ?
              AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
              AND pp.fecha_programada >= date('now','-1 day')
        """
        if fecha_horizonte:
            sql += " AND pp.fecha_programada <= ?"
            params.append(fecha_horizonte)
        row = c.execute(sql, params).fetchone()
        out['demanda_total_horizonte'] = float(row[0] or 0)
    except Exception:
        out['demanda_total_horizonte'] = 0.0

    # 5) Disponibilidad neta = stock + transito + solicitado - demanda
    # solicitado_pendiente todavia no es seguro pero suma como cobertura tentativa.
    out['disponibilidad_neta'] = (
        out['stock_actual']
        + out['en_transito']
        + out['solicitado_pendiente']
        - out['demanda_total_horizonte']
    )
    return out


def _generar_checklist_produccion(c, produccion_id, producto_nombre, fecha_planeada,
                                   cantidad_kg, generar_mps=True, usuario='sistema'):
    """Genera items de checklist para una produccion.

    Si generar_mps=True, lee la formula del producto y crea 1 item por cada
    MP con la cantidad requerida + analisis de disponibilidad CONSIDERANDO
    TODAS las producciones del horizonte (decision Sebastian 2026-04-28).

    Tambien crea items default de envases/etiquetas/etc segun plantilla.

    Idempotente: si ya hay items para esta produccion_id, no duplica.
    """
    # Verificar si ya hay items
    existing = c.execute(
        "SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=?",
        (produccion_id,)
    ).fetchone()[0]
    if existing > 0:
        return 0  # ya tiene checklist

    items_creados = 0

    # 1) MPs desde la formula con calculo de disponibilidad agregada
    if generar_mps:
        try:
            mps = c.execute("""
                SELECT material_id, material_nombre, porcentaje, cantidad_g_por_lote
                FROM formula_items
                WHERE producto_nombre = ?
            """, (producto_nombre,)).fetchall()
            for mp in mps:
                codigo_mp = mp[0] or ''
                nombre_mp = mp[1] or ''
                porcentaje = float(mp[2] or 0)
                # Cantidad requerida SOLO para esta produccion individual
                cant_req_g = (porcentaje / 100.0) * (cantidad_kg or 0) * 1000.0

                # Disponibilidad agregada considerando TODO el horizonte
                # hasta la fecha de esta produccion (inclusive)
                disp = _calcular_disponibilidad_mp(c, codigo_mp,
                                                    fecha_horizonte=fecha_planeada)

                # Determinar estado segun disponibilidad NETA del horizonte
                if disp['disponibilidad_neta'] >= 0 and disp['en_transito'] == 0 and disp['solicitado_pendiente'] == 0:
                    # Stock cubre la demanda total
                    estado = 'verificado_ok'
                elif disp['en_transito'] > 0 and disp['disponibilidad_neta'] >= 0:
                    # Hay material en transito que cubre o complementa
                    estado = 'en_transito'
                elif disp['solicitado_pendiente'] > 0 and disp['disponibilidad_neta'] >= 0:
                    # Hay SOL pendiente que cubre
                    estado = 'solicitado'
                else:
                    # Falta material: debe solicitarse HOY
                    estado = 'pendiente'

                # Deficit = lo que aun falta cubrir
                deficit = max(0, -disp['disponibilidad_neta'])

                obs_extra = (
                    f"Stock: {disp['stock_actual']:.0f}g "
                    f"+ Transito: {disp['en_transito']:.0f}g "
                    f"+ Solicitado: {disp['solicitado_pendiente']:.0f}g "
                    f"- Demanda total horizonte: {disp['demanda_total_horizonte']:.0f}g "
                    f"= Neta: {disp['disponibilidad_neta']:.0f}g"
                )

                c.execute("""INSERT INTO produccion_checklist
                    (produccion_id, producto_nombre, fecha_planeada, cantidad_kg,
                     item_tipo, descripcion, cantidad_requerida, unidad, codigo_mp,
                     stock_actual, deficit, estado, dias_anticipacion,
                     observaciones, actualizado_por)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (produccion_id, producto_nombre, fecha_planeada, cantidad_kg,
                     'mp', nombre_mp, cant_req_g, 'g', codigo_mp,
                     disp['stock_actual'], deficit, estado, 30,
                     obs_extra, usuario))
                items_creados += 1
        except Exception:
            pass

    # 2) Envases / etiquetas / decoracion (plantilla del producto o default)
    # Sebastian (29-abr-2026): "ya la app sabe la presentacion del producto,
    # deberia calcular en automatico la cantidad de envases ... pero con la
    # opcion de corregir de ser necesario". Calculamos cantidad_unidades
    # desde formula_headers.volumen_unitario_ml o peso_g; el editor inline
    # ya existente permite ajustar manualmente.
    try:
        # Presentacion del producto (en g o ml — para cosmeticos densidad ~1)
        presentacion_g_ml = 0.0
        try:
            pres = c.execute("""
                SELECT COALESCE(volumen_unitario_ml, 0), COALESCE(peso_g, 0)
                FROM formula_headers
                WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
            """, (producto_nombre,)).fetchone()
            if pres:
                vol_ml = float(pres[0] or 0)
                peso_g = float(pres[1] or 0)
                # Preferir volumen_unitario_ml; fallback a peso_g de Shopify
                presentacion_g_ml = vol_ml or peso_g
        except Exception:
            pass

        # Calcular unidades objetivo con 5% de merma (estandar industrial)
        import math as _math
        if presentacion_g_ml > 0 and (cantidad_kg or 0) > 0:
            unidades_objetivo = int(_math.ceil(
                (cantidad_kg * 1000.0) / presentacion_g_ml * 1.05
            ))
        else:
            unidades_objetivo = 0  # sin info; frontend mostrara "—"

        # Tipos que llevan cantidad_unidades (los que son piezas fisicas);
        # serigrafia/tampografia son servicios, no aplican unidades.
        TIPOS_CON_UNIDADES = {
            'envase_primario', 'envase_secundario', 'tapa', 'caja_exterior',
            'etiqueta_frontal', 'etiqueta_posterior', 'etiqueta_lateral',
            'instructivo', 'otro',
        }

        # Buscar plantilla especifica del producto
        plantilla = c.execute("""
            SELECT item_tipo, descripcion, dias_anticipacion, orden, proveedor_default, obligatorio
            FROM checklist_plantillas
            WHERE producto_nombre=? OR producto_nombre=''
            ORDER BY CASE WHEN producto_nombre=? THEN 0 ELSE 1 END, orden
        """, (producto_nombre, producto_nombre)).fetchall()

        # Deduplicar: prioritar la del producto sobre la generica
        seen = set()
        items_a_crear = []
        for row in plantilla:
            tipo = row[0]
            if tipo in seen:
                continue
            seen.add(tipo)
            items_a_crear.append(row)

        for row in items_a_crear:
            tipo, desc, dias, orden, prov, obligatorio = row
            if not obligatorio:
                continue  # solo crear los obligatorios automaticamente
            if tipo in TIPOS_LEGACY_OCULTOS:
                continue  # cubierto por la decoracion del envase
            cant_ud = unidades_objetivo if tipo in TIPOS_CON_UNIDADES else 0
            unidad_label = 'ud' if cant_ud > 0 else ''
            obs_calc = (
                f"Auto: {cantidad_kg:.1f}kg / {presentacion_g_ml:.0f}{'ml' if (pres and (pres[0] or 0)>0) else 'g'} "
                f"= {cant_ud} ud (+5% merma)"
            ) if cant_ud > 0 else ''
            c.execute("""INSERT INTO produccion_checklist
                (produccion_id, producto_nombre, fecha_planeada, cantidad_kg,
                 item_tipo, descripcion, cantidad_unidades, unidad,
                 estado, proveedor, dias_anticipacion, observaciones,
                 actualizado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (produccion_id, producto_nombre, fecha_planeada, cantidad_kg,
                 tipo, desc, cant_ud, unidad_label,
                 'pendiente', prov or '', dias or 30, obs_calc, usuario))
            items_creados += 1
    except Exception:
        pass

    return items_creados


@bp.route('/api/programacion/checklist/generar/<int:produccion_id>', methods=['POST'])
def checklist_generar(produccion_id):
    """Genera o regenera checklist para una produccion programada.

    Body opcional: {forzar: true} para regenerar borrando items existentes.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    conn = get_db(); c = conn.cursor()

    # Obtener datos de la produccion programada
    # produccion_programada tiene: producto, fecha_programada, lotes
    # kg total = lotes * formula_headers.lote_size_kg
    prod = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
               COALESCE(fh.lote_size_kg, 0) as lote_kg,
               COALESCE(pp.cantidad_kg, 0)  as cantidad_kg_explicita
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        WHERE pp.id=?
    """, (produccion_id,)).fetchone()
    if not prod:
        return jsonify({'error': 'Produccion no encontrada'}), 404
    lotes = int(prod[3] or 1)
    lote_kg = float(prod[4] or 0)
    cant_explicita = float(prod[5] or 0)
    # Prioridad: cantidad_kg explicita (del calendario) > lotes * lote_kg
    cant = cant_explicita if cant_explicita > 0 else (lotes * lote_kg)

    if d.get('forzar'):
        c.execute("DELETE FROM produccion_checklist WHERE produccion_id=?", (produccion_id,))

    items = _generar_checklist_produccion(
        c, produccion_id, prod[1], prod[2], cant,
        generar_mps=True,
        usuario=session.get('compras_user', 'sistema'))
    conn.commit()
    return jsonify({'ok': True, 'items_creados': items})


@bp.route('/api/programacion/checklist/<int:produccion_id>', methods=['GET'])
def checklist_get(produccion_id):
    """Devuelve el checklist completo de una produccion con totales por estado.

    Sebastian (28-abr-2026): el modal NO debe mostrar items tipo 'mp'
    (materias primas) — esos ya viven en Planificacion Estrategica con
    detalle agregado de stock+transito+solicitado-demanda. El checklist
    Pre-Produccion se enfoca en MEE: envases, tapas, etiquetas, serigrafia,
    tampografia. Por default, ?include_mps=0 (excluye MPs); pasar
    ?include_mps=1 para listarlas (uso debug/auditor).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    include_mps = request.args.get('include_mps', '0') == '1'
    conn = get_db(); c = conn.cursor()
    where_extra = "" if include_mps else " AND item_tipo != 'mp'"
    # Excluir tipos legacy que ya se cubren con la decoracion del envase
    if TIPOS_LEGACY_OCULTOS:
        placeholders = ','.join(['?'] * len(TIPOS_LEGACY_OCULTOS))
        where_extra += f" AND item_tipo NOT IN ({placeholders})"
        legacy_params = list(TIPOS_LEGACY_OCULTOS)
    else:
        legacy_params = []
    rows = c.execute(f"""
        SELECT id, item_tipo, descripcion, cantidad_requerida, unidad, codigo_mp,
               stock_actual, deficit, estado, proveedor, solicitud_numero,
               oc_numero, fecha_solicitud, fecha_eta, fecha_recibido,
               responsable, observaciones, dias_anticipacion, actualizado_at,
               producto_nombre, fecha_planeada
        FROM produccion_checklist
        WHERE produccion_id=?{where_extra}
        ORDER BY
          CASE item_tipo WHEN 'mp' THEN 1
                         WHEN 'envase_primario' THEN 2
                         WHEN 'tapa' THEN 3
                         WHEN 'etiqueta_frontal' THEN 4
                         WHEN 'etiqueta_posterior' THEN 5
                         WHEN 'caja_exterior' THEN 6
                         WHEN 'serigrafia' THEN 7
                         WHEN 'tampografia' THEN 8
                         ELSE 9 END,
          descripcion ASC
    """, [produccion_id] + legacy_params).fetchall()
    cols = [x[0] for x in c.description]
    items = [dict(zip(cols, r)) for r in rows]

    # Totales por estado (solo de los items mostrados — sin MPs por default)
    totales = {'pendiente': 0, 'verificado_ok': 0, 'solicitado': 0,
               'en_transito': 0, 'recibido': 0, 'listo': 0, 'no_aplica': 0}
    for it in items:
        totales[it['estado']] = totales.get(it['estado'], 0) + 1

    total_items = len(items)
    completados = totales['verificado_ok'] + totales['recibido'] + totales['listo']
    porcentaje = round((completados / total_items * 100), 1) if total_items > 0 else 0

    # Metadata del producto desde formula_headers + auto-sync Shopify si pendiente
    producto_nombre = ''
    producto_meta = {}
    try:
        if items and items[0].get('producto_nombre'):
            producto_nombre = items[0]['producto_nombre']
        else:
            r = c.execute(
                "SELECT producto FROM produccion_programada WHERE id=?",
                (produccion_id,)
            ).fetchone()
            producto_nombre = r[0] if r else ''

        if producto_nombre:
            def _read_meta():
                mr = c.execute("""
                    SELECT COALESCE(imagen_url,''), COALESCE(sku_principal,''),
                           COALESCE(descripcion_plain,''), COALESCE(precio_venta,0),
                           COALESCE(peso_g,0), COALESCE(imagenes_extra_json,'[]'),
                           COALESCE(shopify_handle,''), COALESCE(shopify_synced_at,'')
                    FROM formula_headers WHERE producto_nombre=?
                """, (producto_nombre,)).fetchone()
                return mr

            mr = _read_meta()

            # Auto-sync inmediato del producto si NUNCA se sincronizo (max 8s).
            # Asi el primer click al checklist trae la foto sin que Sebastian
            # tenga que hacer click manual.
            if mr and not mr[7]:  # shopify_synced_at vacio
                try:
                    from blueprints.inventario import _shopify_sync_producto
                    _shopify_sync_producto(conn, producto_nombre, timeout=8)
                    mr = _read_meta()  # re-leer despues del sync
                except Exception:
                    pass

            # Disparar sync masivo en background para los demas productos
            # (no bloquea esta respuesta — corre en thread separado)
            try:
                from blueprints.inventario import _sync_shopify_pendientes_background
                _sync_shopify_pendientes_background(max_edad_horas=24, max_productos=50)
            except Exception:
                pass

            if mr:
                import json as _json
                try:
                    imagenes_extra = _json.loads(mr[5] or '[]')
                except Exception:
                    imagenes_extra = []
                producto_meta = {
                    'imagen_url':       mr[0],
                    'sku':              mr[1],
                    'descripcion':      mr[2],
                    'precio':           float(mr[3] or 0),
                    'peso_g':           float(mr[4] or 0),
                    'imagenes_extra':   imagenes_extra,
                    'shopify_handle':   mr[6],
                    'shopify_synced_at': mr[7],
                }
    except Exception:
        pass

    return jsonify({
        'items': items,
        'totales_por_estado': totales,
        'total_items': total_items,
        'completados': completados,
        'porcentaje_listo': porcentaje,
        'producto_nombre': producto_nombre,
        # Compat con UI vieja
        'imagen_url': producto_meta.get('imagen_url', ''),
        # Metadata Shopify completa
        'producto_meta': producto_meta,
    })


@bp.route('/api/programacion/checklist/items/<int:item_id>', methods=['PATCH'])
def checklist_item_update(item_id):
    """Actualiza estado/proveedor/observaciones/etc de un item."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    fields = ['estado', 'proveedor', 'observaciones', 'responsable',
              'fecha_eta', 'fecha_recibido', 'fecha_solicitud',
              'solicitud_numero', 'oc_numero', 'cantidad_requerida']
    sets = []
    vals = []
    for f in fields:
        if f in d:
            sets.append(f'{f}=?')
            vals.append(d[f])
    if not sets:
        return jsonify({'error': 'Nada que actualizar'}), 400
    sets.append("actualizado_at=datetime('now')")
    sets.append("actualizado_por=?")
    vals.append(session.get('compras_user', 'sistema'))
    vals.append(item_id)
    conn = get_db(); c = conn.cursor()
    c.execute(f"UPDATE produccion_checklist SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/programacion/checklist/items/<int:item_id>/solicitar', methods=['POST'])
def checklist_item_solicitar(item_id):
    """Genera una SOL automatica para este item si requiere compra.

    Crea solicitud_compra con datos del item + actualiza estado a 'solicitado'.
    Si el item ya tiene solicitud_numero, no crea nueva.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    item = c.execute("""SELECT * FROM produccion_checklist WHERE id=?""", (item_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Item no encontrado'}), 404
    item_dict = dict(zip([x[0] for x in c.description], item))

    if item_dict.get('solicitud_numero'):
        return jsonify({'ok': True, 'ya_solicitado': True,
                        'solicitud_numero': item_dict['solicitud_numero']})

    # Generar numero SOL
    from datetime import datetime as _dt
    year = _dt.now().year
    last = c.execute(
        "SELECT numero FROM solicitudes_compra WHERE numero LIKE ? ORDER BY numero DESC LIMIT 1",
        (f'SOL-{year}-%',)
    ).fetchone()
    seq = 1
    if last:
        try: seq = int(last[0].split('-')[-1]) + 1
        except: seq = 1
    sol_num = f'SOL-{year}-{seq:04d}'

    # Determinar categoria segun tipo
    cat_map = {
        'mp': 'Materia Prima',
        'envase_primario': 'Material de Empaque',
        'envase_secundario': 'Material de Empaque',
        'tapa': 'Material de Empaque',
        'etiqueta_frontal': 'Material de Empaque',
        'etiqueta_posterior': 'Material de Empaque',
        'etiqueta_lateral': 'Material de Empaque',
        'caja_exterior': 'Material de Empaque',
        'serigrafia': 'Servicios',
        'tampografia': 'Servicios',
        'instructivo': 'Material de Empaque',
        'estuche': 'Material de Empaque',
    }
    categoria = cat_map.get(item_dict.get('item_tipo'), 'Material de Empaque')

    descripcion = (
        f"[Checklist Produccion] {item_dict.get('descripcion','')}"
        f" para {item_dict.get('producto_nombre','')}"
        f" (lote programado {item_dict.get('fecha_planeada','')})"
    )
    if item_dict.get('cantidad_requerida') and item_dict.get('item_tipo') == 'mp':
        descripcion += f" | Cantidad: {item_dict['cantidad_requerida']:.0f} {item_dict.get('unidad','g')}"

    user = session.get('compras_user', 'sistema')
    user_email = ''
    try:
        from config import USER_EMAILS as _UE
        user_email = _UE.get(user, '')
    except Exception:
        pass

    c.execute("""INSERT INTO solicitudes_compra
        (numero, fecha, estado, solicitante, email_solicitante, urgencia,
         observaciones, area, empresa, categoria, tipo)
        VALUES (?,date('now'),'Pendiente',?,?,?,?,?,?,?,?)""",
        (sol_num, user, user_email, 'Alta', descripcion,
         'Produccion', 'Espagiria', categoria,
         'Servicio' if categoria == 'Servicios' else 'Material'))

    # Si es MP con codigo + cantidad: tambien insertar el item
    try:
        if item_dict.get('codigo_mp') and item_dict.get('cantidad_requerida'):
            c.execute("""INSERT INTO solicitudes_compra_items
                (numero, codigo_mp, nombre_mp, cantidad_g, justificacion)
                VALUES (?,?,?,?,?)""",
                (sol_num, item_dict['codigo_mp'],
                 item_dict.get('descripcion',''),
                 float(item_dict['cantidad_requerida']),
                 'Generado desde checklist pre-produccion'))
    except Exception:
        pass

    # Actualizar item del checklist
    c.execute("""UPDATE produccion_checklist
                 SET estado='solicitado', solicitud_numero=?,
                     fecha_solicitud=date('now'),
                     actualizado_at=datetime('now'), actualizado_por=?
                 WHERE id=?""",
              (sol_num, user, item_id))
    conn.commit()
    return jsonify({'ok': True, 'solicitud_numero': sol_num,
                    'mensaje': f'Solicitud {sol_num} creada para {item_dict.get("descripcion","")}'})


def _ensure_sync_log_table(conn):
    """Tabla minima para registrar el timestamp del ultimo sync de cada
    fuente externa (calendario, shopify, etc). Una fila por sync_type."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                sync_type    TEXT PRIMARY KEY,
                last_run_at  TEXT NOT NULL,
                last_count   INTEGER DEFAULT 0,
                last_error   TEXT
            )
        """)
    except Exception:
        pass


def _record_sync(conn, sync_type, count, error=None):
    """Registra timestamp del ultimo sync exitoso/fallido de un tipo."""
    _ensure_sync_log_table(conn)
    try:
        ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute("""
            INSERT INTO sync_log (sync_type, last_run_at, last_count, last_error)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(sync_type) DO UPDATE SET
                last_run_at = excluded.last_run_at,
                last_count  = excluded.last_count,
                last_error  = excluded.last_error
        """, (sync_type, ts, count, error))
        conn.commit()
    except Exception:
        pass


def _get_last_sync(conn, sync_type):
    """Lee timestamp y count del ultimo sync de un tipo. None si nunca."""
    _ensure_sync_log_table(conn)
    try:
        row = conn.execute(
            "SELECT last_run_at, last_count, last_error FROM sync_log WHERE sync_type=?",
            (sync_type,)
        ).fetchone()
        if not row:
            return None
        return {'last_run_at': row[0], 'last_count': row[1] or 0, 'last_error': row[2]}
    except Exception:
        return None


def _sync_calendar_a_produccion_programada(conn, days_ahead=90):
    """Sincroniza eventos de Google Calendar a la tabla produccion_programada.

    Idempotente: usa (producto, fecha_programada) como key para evitar
    duplicados. Marca origen='calendar' para distinguir de manuales.

    Sebastian (28-abr-2026): el checklist Pre-Produccion lee de
    produccion_programada, pero los eventos viven en el calendario
    animuslb.com. Antes habia que duplicar manualmente. Ahora se
    auto-sincroniza al cargar el checklist.

    Returns: count de filas insertadas en esta corrida.
    """
    import datetime as _dt
    import re as _re
    try:
        cal = _fetch_calendar_events(days_ahead=days_ahead)
    except Exception:
        return 0
    events = cal.get('events', [])
    if not events:
        return 0

    # Cargar mapa SKU → producto y formulas (para validar y obtener kg/lote)
    formulas = _get_formulas(conn)
    sku_to_prod = {}
    try:
        for row in conn.execute(
            "SELECT UPPER(sku), producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            sku_to_prod[row[0]] = row[1]
    except Exception:
        pass

    # Filtrar tokens que NO son SKUs (mismo set que planificacion_estrategica)
    NOT_SKU = {
        'FAB','QC','CON','SIN','MICRO','ENVASADO','ACONDICIONAMIENTO',
        'FABRICACION','FABRICACIÓN','LANZAMIENTO','PRODUCCION','PRODUCCIÓN',
        'KG','MES','DIAS','DÍAS','ML','UDS','BATCH','FERNANDO',
        'MESA','LOTES','LOTE','MINI','MACRO','AND','THE','FOR'
    }
    NON_FAB_KW = {
        'envasado', 'acondicionamiento', 'micro qc',
        'control de calidad', 'dispensado', 'etiquetado', 'llenado',
    }

    def _skus(titulo):
        tokens = _re.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in NOT_SKU]

    def _kg(titulo):
        m = _re.findall(r'~?(\d+(?:[,.]\d+)*)\s*kg', titulo, _re.IGNORECASE)
        if not m: return None
        try: return float(m[-1].replace(',', '.'))
        except Exception: return None

    today = _dt.date.today()
    inserted = 0
    for ev in events:
        titulo = ev.get('titulo', '')
        fecha_s = ev.get('fecha', '')
        if not fecha_s:
            continue
        try:
            fecha = _dt.date.fromisoformat(fecha_s)
        except ValueError:
            continue
        if fecha < today:
            continue
        # Saltar eventos que NO son fabricacion (envasado/QC/etc consumen
        # nada de MPs crudas y no tienen sentido en el checklist).
        tlow = titulo.lower()
        if any(kw in tlow for kw in NON_FAB_KW):
            continue
        kg_evento = _kg(titulo)
        for sku in _skus(titulo):
            prod = sku_to_prod.get(sku)
            if not prod or prod not in formulas:
                continue
            lote_kg = formulas[prod].get('lote_size_kg', 0) or 0
            lotes = max(1, round((kg_evento or lote_kg) / lote_kg)) if lote_kg > 0 else 1
            # cantidad_kg explicita: prioriza kg extraido del titulo del evento
            # ("~5kg") sobre el calculo derivado lotes*lote_kg. Si ninguno aplica,
            # 0 (el frontend mostrara "Sin tamano de lote — verificar formula").
            cantidad_kg_calc = (kg_evento or 0) or (lotes * lote_kg if lote_kg > 0 else 0)
            # INSERT idempotente: si ya existe (producto, fecha), no duplicar
            try:
                exists = conn.execute(
                    "SELECT id, COALESCE(cantidad_kg,0) FROM produccion_programada "
                    "WHERE producto=? AND fecha_programada=? LIMIT 1",
                    (prod, fecha_s)
                ).fetchone()
                if not exists:
                    # origen='calendar' para que planificacion_estrategica las
                    # filtre y no duplique con su lectura directa del calendar.
                    conn.execute(
                        """INSERT INTO produccion_programada
                           (producto, fecha_programada, lotes, cantidad_kg,
                            estado, observaciones, origen)
                           VALUES (?, ?, ?, ?, 'programado', ?, 'calendar')""",
                        (prod, fecha_s, lotes, cantidad_kg_calc,
                         f'[auto-sync calendar] {titulo[:200]}')
                    )
                    inserted += 1
                elif (exists[1] or 0) <= 0 and cantidad_kg_calc > 0:
                    # Backfill: la fila existe pero sin cantidad_kg — actualizar.
                    conn.execute(
                        "UPDATE produccion_programada SET cantidad_kg=? WHERE id=?",
                        (cantidad_kg_calc, exists[0])
                    )
            except Exception:
                continue
            break  # un evento → un producto match
    if inserted:
        conn.commit()

    # ── Sync BIDIRECCIONAL ─────────────────────────────────────────────
    # Marcar como 'cancelado' las filas con origen='calendar' cuya
    # (producto, fecha_programada) YA NO existe en el calendar — es decir,
    # Sebastian las borro o movio en Google Calendar y aqui quedaron de
    # huerfanas. Si NO hacemos esto, el horizonte del checklist mostrara
    # producciones fantasma que ya no estan programadas.
    # Solo toca origen='calendar' — las manuales (origen NULL/manual) NO
    # se tocan jamas porque no tienen contraparte en el calendar.
    archived = 0
    try:
        # Set de (producto, fecha) que SI existen actualmente en calendar
        keys_calendar = set()
        for ev in events:
            tlow = ev.get('titulo', '').lower()
            if any(kw in tlow for kw in NON_FAB_KW):
                continue
            fecha_s = ev.get('fecha', '')
            if not fecha_s:
                continue
            for sku in _skus(ev.get('titulo', '')):
                prod = sku_to_prod.get(sku)
                if prod and prod in formulas:
                    keys_calendar.add((prod, fecha_s))
                    break
        # Filas activas con origen='calendar' que NO estan en el calendar actual
        candidatos = conn.execute(
            "SELECT id, producto, fecha_programada FROM produccion_programada "
            "WHERE origen='calendar' "
            "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado') "
            "AND fecha_programada >= date('now','-1 day')"
        ).fetchall()
        huerfanos = [r[0] for r in candidatos if (r[1], r[2]) not in keys_calendar]
        if huerfanos:
            placeholders = ','.join(['?'] * len(huerfanos))
            conn.execute(
                f"UPDATE produccion_programada SET estado='cancelado', "
                f"observaciones=COALESCE(observaciones,'') || ' [auto-cancelado: ya no esta en calendar]' "
                f"WHERE id IN ({placeholders})",
                huerfanos
            )
            archived = len(huerfanos)
            conn.commit()
    except Exception:
        archived = 0

    # Registrar timestamp del sync (independiente de si hubo nuevas)
    _record_sync(conn, 'calendar', inserted + archived, error=cal.get('error'))
    return inserted


def _start_calendar_sync_background_loop():
    """Arranca un thread daemon que cada N minutos sincroniza el calendario
    sin requerir que alguien tenga la pantalla abierta. Idempotente: solo
    arranca una instancia por proceso. Se reinicia al primer request del
    blueprint si Render hace cold-start.

    Frecuencia configurable via env var CALENDAR_SYNC_INTERVAL_MIN
    (default 10 min). Si <=0, queda desactivado.

    Decision Sebastian 2026-04-29: el checklist debe estar fresco aunque
    nadie lo este mirando — Catalina entra en la mañana y la cola ya
    refleja lo que se agrego al calendar.
    """
    import threading, os, time as _t
    if getattr(_start_calendar_sync_background_loop, '_running', False):
        return
    try:
        interval_min = int(os.environ.get('CALENDAR_SYNC_INTERVAL_MIN', '10'))
    except ValueError:
        interval_min = 10
    if interval_min <= 0:
        return  # desactivado
    _start_calendar_sync_background_loop._running = True

    def _worker():
        from config import DB_PATH
        import sqlite3
        # Pequeño delay inicial para no chocar con el startup del proceso
        _t.sleep(20)
        while True:
            try:
                local_conn = sqlite3.connect(DB_PATH, timeout=30)
                try:
                    _sync_calendar_a_produccion_programada(local_conn, days_ahead=120)
                finally:
                    local_conn.close()
            except Exception:
                pass  # el loop nunca debe morir por una falla puntual
            _t.sleep(max(60, interval_min * 60))

    t = threading.Thread(target=_worker, daemon=True, name='calendar-sync-loop')
    t.start()


# Arrancar el loop al importar el blueprint (una vez por proceso)
try:
    _start_calendar_sync_background_loop()
except Exception:
    pass


@bp.route('/api/programacion/checklist/sync-calendar', methods=['POST'])
def checklist_sync_calendar_endpoint():
    """Endpoint manual para forzar sincronizacion calendario → produccion_programada.

    Tambien se llama automaticamente al cargar /resumen-calendario y por
    un thread background cada N min (CALENDAR_SYNC_INTERVAL_MIN).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    days = int(request.args.get('dias', 90))
    conn = get_db()
    inserted = _sync_calendar_a_produccion_programada(conn, days_ahead=days)
    last = _get_last_sync(conn, 'calendar')
    return jsonify({
        'ok': True,
        'producciones_creadas': inserted,
        'last_run_at': last['last_run_at'] if last else None,
        'mensaje': f'{inserted} producciones nuevas importadas del calendario'
                   if inserted else 'El calendario ya estaba sincronizado'
    })


@bp.route('/api/programacion/checklist/resumen-calendario')
def checklist_resumen_calendario():
    """Vista panoramica: para cada produccion programada en proximos N dias,
    devuelve % de completitud del checklist + dias faltantes + items criticos
    pendientes.

    Auto-sincroniza eventos del calendario antes de listar para que las
    producciones nuevas del calendar aparezcan sin que el usuario tenga que
    hacer trigger manual. Usado por Planta + Gerencia.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    horizonte = int(request.args.get('dias', 60))
    conn = get_db(); c = conn.cursor()

    # Auto-sync calendario → produccion_programada (idempotente, falla silenciosa)
    sync_count = 0
    try:
        sync_count = _sync_calendar_a_produccion_programada(conn, days_ahead=max(horizonte, 90))
    except Exception:
        pass

    # Auto-sync masivo Shopify de productos pendientes en BACKGROUND.
    # No bloquea la respuesta — al refresh el usuario ya tiene fotos.
    try:
        from blueprints.inventario import _sync_shopify_pendientes_background
        _sync_shopify_pendientes_background(max_edad_horas=24, max_productos=50)
    except Exception:
        pass

    # Filtro legacy aplicado a cada subquery de conteo (etiquetas frontal/posterior/lateral
    # ya no cuentan porque la decoracion del envase las cubre). Se construye dinamicamente
    # para que cambiar TIPOS_LEGACY_OCULTOS arriba se propague aqui.
    if TIPOS_LEGACY_OCULTOS:
        legacy_sql = " AND item_tipo NOT IN (" + ",".join(["'" + t.replace("'", "''") + "'" for t in TIPOS_LEGACY_OCULTOS]) + ")"
    else:
        legacy_sql = ""
    try:
        rows = c.execute(f"""
            SELECT pp.id,
                   pp.producto                                       as producto_nombre,
                   pp.fecha_programada                               as fecha_planeada,
                   COALESCE(NULLIF(pp.cantidad_kg, 0),
                            COALESCE(pp.lotes, 1) * COALESCE(fh.lote_size_kg, 0)) as kg,
                   pp.estado                                         as estado_prod,
                   COALESCE(pp.origen, 'manual')                     as origen,
                   COALESCE(pp.inventario_descontado_at, '')         as descontado_at,
                   (julianday(pp.fecha_programada) - julianday('now')) as dias_faltan,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}) as total_items,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado IN ('verificado_ok','recibido','listo')) as completados,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado='pendiente') as pendientes,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado='solicitado') as solicitados,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado='en_transito') as en_transito,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado='recibido') as recibidos,
                   (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id{legacy_sql}
                       AND estado='no_aplica') as no_aplica
            FROM produccion_programada pp
            LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
            WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
              AND pp.fecha_programada >= date('now','-30 day')
              AND pp.fecha_programada <= date('now','+' || ? || ' day')
            ORDER BY pp.fecha_programada ASC
        """, (horizonte,)).fetchall()
        cols = [x[0] for x in c.description]
        out = []
        for r in rows:
            d = dict(zip(cols, r))
            total = d['total_items'] or 0
            comp = d['completados'] or 0
            d['porcentaje'] = round(comp / total * 100, 1) if total > 0 else 0
            d['semaforo'] = (
                'verde'    if d['porcentaje'] >= 90 else
                'amarillo' if d['porcentaje'] >= 50 else
                'rojo'
            )
            d['dias_faltan'] = int(d['dias_faltan']) if d['dias_faltan'] is not None else 0
            out.append(d)
        last_sync = _get_last_sync(conn, 'calendar')
        return jsonify({
            'producciones': out,
            'horizonte_dias': horizonte,
            'sync_calendario': {
                'producciones_nuevas': sync_count,
                'last_run_at': last_sync['last_run_at'] if last_sync else None,
                'last_error': last_sync['last_error'] if last_sync else None,
            },
        })
    except Exception as e:
        return jsonify({'error': str(e), 'producciones': []})


@bp.route('/api/programacion/disponibilidad-mp/<path:codigo_mp>')
def disponibilidad_mp_endpoint(codigo_mp):
    """Panorama completo de disponibilidad de un MP:
       stock + en_transito + solicitado - demanda_horizonte = neta.
    Querystring: ?dias=60 (default)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    dias = int(request.args.get('dias', 60))
    fecha_h = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
    conn = get_db(); c = conn.cursor()
    disp = _calcular_disponibilidad_mp(c, codigo_mp, fecha_horizonte=fecha_h)
    # Detalle de OCs en transito + SOLs pendientes
    try:
        ocs = c.execute("""
            SELECT oc.numero_oc, oc.estado, oc.proveedor,
                   (i.cantidad_g - COALESCE(i.cantidad_recibida_g,0)) as faltante_g,
                   oc.fecha_entrega_est
            FROM ordenes_compra_items i
            JOIN ordenes_compra oc ON oc.numero_oc=i.numero_oc
            WHERE i.codigo_mp=?
              AND oc.estado IN ('Borrador','Pendiente','Revisada','Aprobada',
                                'Autorizada','Parcial','Pagada')
              AND (i.cantidad_g - COALESCE(i.cantidad_recibida_g,0)) > 0
            ORDER BY oc.fecha DESC
        """, (codigo_mp,)).fetchall()
        disp['ocs_en_transito'] = [
            {'numero_oc': r[0], 'estado': r[1], 'proveedor': r[2],
             'cantidad_g': r[3], 'eta': r[4]} for r in ocs
        ]
    except Exception:
        disp['ocs_en_transito'] = []

    try:
        sols = c.execute("""
            SELECT s.numero, s.estado, s.fecha, si.cantidad_g, si.justificacion
            FROM solicitudes_compra_items si
            JOIN solicitudes_compra s ON s.numero=si.numero
            WHERE si.codigo_mp=?
              AND s.estado IN ('Pendiente','En revision','Aprobada')
              AND COALESCE(s.numero_oc,'')=''
            ORDER BY s.fecha DESC
        """, (codigo_mp,)).fetchall()
        disp['solicitudes_pendientes'] = [
            {'numero': r[0], 'estado': r[1], 'fecha': r[2],
             'cantidad_g': r[3], 'justificacion': r[4]} for r in sols
        ]
    except Exception:
        disp['solicitudes_pendientes'] = []

    # Producciones que demandan este MP
    try:
        prods = c.execute("""
            SELECT pp.id,
                   pp.producto                                          as producto_nombre,
                   pp.fecha_programada                                  as fecha_planeada,
                   COALESCE(pp.lotes, 1) * COALESCE(fh.lote_size_kg, 0) as kg,
                   fi.porcentaje,
                   ROUND(COALESCE(fi.cantidad_g_por_lote,0) * COALESCE(pp.lotes, 1)) as req_g
            FROM produccion_programada pp
            JOIN formula_items fi ON fi.producto_nombre = pp.producto
            LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
            WHERE fi.material_id = ?
              AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
              AND pp.fecha_programada >= date('now','-1 day')
              AND pp.fecha_programada <= ?
            ORDER BY pp.fecha_programada ASC
        """, (codigo_mp, fecha_h)).fetchall()
        disp['producciones_que_lo_usan'] = [
            {'produccion_id': r[0], 'producto': r[1], 'fecha': r[2],
             'kg': r[3], 'porcentaje': r[4], 'requerido_g': r[5]}
            for r in prods
        ]
    except Exception:
        disp['producciones_que_lo_usan'] = []

    disp['codigo_mp'] = codigo_mp
    disp['horizonte_dias'] = dias
    disp['fecha_horizonte'] = fecha_h
    return jsonify(disp)


@bp.route('/api/programacion/checklist/backfill', methods=['POST'])
def checklist_backfill():
    """Genera checklists para producciones de los ultimos 30 dias en
    adelante que aun no tienen items creados.

    Solo admin. Idempotente.
    """
    if 'compras_user' not in session or session.get('compras_user') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403

    # Wrapper externo: captura CUALQUIER excepcion (incluyendo get_db() o
    # imports rotos) para que devolvamos el traceback al frontend en JSON
    # en lugar de caer al @app.errorhandler(Exception) global de api/index.py
    # que solo dice "Error interno del servidor" sin pista del problema real.
    import traceback as _tb
    try:
        conn = get_db(); c = conn.cursor()
        rows = []
        try:
            rows = c.execute("""
                SELECT pp.id,
                       pp.producto                                          as producto_nombre,
                       pp.fecha_programada                                  as fecha_planeada,
                       COALESCE(NULLIF(pp.cantidad_kg, 0),
                                COALESCE(pp.lotes, 1) * COALESCE(fh.lote_size_kg, 0)) as kg
                FROM produccion_programada pp
                LEFT JOIN formula_headers fh
                       ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
                WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
                  AND pp.fecha_programada >= date('now','-30 day')
                  AND NOT EXISTS (SELECT 1 FROM produccion_checklist
                                  WHERE produccion_id=pp.id)
            """).fetchall()
        except Exception as e:
            return jsonify({
                'error': f'Falla al listar producciones pendientes de checklist: {e}',
                'fase': 'select_pendientes',
                'traceback': _tb.format_exc()[-1500:],
            }), 500

        # Procesar cada produccion en su propio try/except — si una falla, las
        # demas siguen. Asi el backfill no se aborta por un solo producto sin
        # formula completa.
        total_creados = 0
        producciones_procesadas = 0
        fallas = []
        for r in rows:
            try:
                items = _generar_checklist_produccion(
                    c, r[0], r[1], r[2], float(r[3] or 0),
                    generar_mps=True,
                    usuario=session.get('compras_user', 'sistema'))
                total_creados += items
                producciones_procesadas += 1
            except Exception as e:
                fallas.append({
                    'produccion_id': r[0],
                    'producto': r[1],
                    'fecha': r[2],
                    'kg': r[3],
                    'error': str(e),
                    'traceback': _tb.format_exc()[-800:],
                })
        try:
            conn.commit()
        except Exception:
            pass
        payload = {
            'ok': len(fallas) == 0,
            'producciones_procesadas': producciones_procesadas,
            'items_creados': total_creados,
            'producciones_pendientes': len(rows),
            'fallas': fallas,
            'mensaje': (f'{producciones_procesadas} producciones recibieron checklist '
                        f'({total_creados} items totales)') if not fallas else (
                        f'{producciones_procesadas}/{len(rows)} OK · '
                        f'{len(fallas)} fallaron — ver "fallas" en la respuesta'),
        }
        # Devolver 200 incluso con fallas parciales (el frontend ve el detalle).
        return jsonify(payload)
    except Exception as e:
        return jsonify({
            'error': f'Falla inesperada en backfill (fuera del bucle): {e}',
            'fase': 'wrapper_externo',
            'tipo': type(e).__name__,
            'traceback': _tb.format_exc()[-2000:],
        }), 500


# ════════════════════════════════════════════════════════════════════════
# CHECKLIST EDITABLE + SOLICITUDES PRODUCCION + TAREAS OPERATIVAS
# Sebastian (29-abr-2026): cada item del checklist se hace editable, con
# dropdown de maestro_mee, cantidad calculada automaticamente, y boton
# "Solicitar" que crea entrada en cola de Catalina. Catalina decide:
# inventario / OC / serigrafia / tampografia (genera tarea operativa).
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/checklist/mee-options', methods=['GET'])
def checklist_mee_options():
    """Devuelve materiales de maestro_mee filtrados por tipo del item.

    Querystring: ?tipo=envase_primario|tapa|etiqueta_frontal|etc
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    tipo = request.args.get('tipo', '')
    # Mapeo tipo_item -> categoria/keywords en maestro_mee
    keyword_map = {
        'envase_primario':    ['envase', 'frasco', 'bote', 'tubo', 'pote'],
        'envase_secundario':  ['caja', 'estuche', 'secundario'],
        'tapa':               ['tapa', 'dosificador', 'pump', 'gotero', 'spray'],
        'etiqueta_frontal':   ['etiqueta', 'label'],
        'etiqueta_posterior': ['etiqueta', 'label'],
        'etiqueta_lateral':   ['etiqueta', 'label'],
        'caja_exterior':      ['caja', 'corrugada', 'exterior'],
        'instructivo':        ['instructivo', 'inserto'],
    }
    keywords = keyword_map.get(tipo, [])
    conn = get_db(); c = conn.cursor()
    if keywords:
        # OR de LIKE por cada keyword
        like_clauses = " OR ".join(["LOWER(descripcion) LIKE ?" for _ in keywords])
        params = [f"%{k}%" for k in keywords]
        rows = c.execute(f"""
            SELECT codigo, descripcion, COALESCE(stock_actual,0), unidad,
                   COALESCE(proveedor,''), COALESCE(categoria,'')
            FROM maestro_mee
            WHERE COALESCE(estado,'Activo')='Activo'
              AND ({like_clauses})
            ORDER BY descripcion
        """, params).fetchall()
    else:
        rows = c.execute("""
            SELECT codigo, descripcion, COALESCE(stock_actual,0), unidad,
                   COALESCE(proveedor,''), COALESCE(categoria,'')
            FROM maestro_mee
            WHERE COALESCE(estado,'Activo')='Activo'
            ORDER BY descripcion
            LIMIT 200
        """).fetchall()
    return jsonify({
        'tipo': tipo,
        'options': [
            {'codigo': r[0], 'descripcion': r[1], 'stock': float(r[2] or 0),
             'unidad': r[3] or 'und', 'proveedor': r[4], 'categoria': r[5]}
            for r in rows
        ]
    })


@bp.route('/api/programacion/checklist/items/<int:item_id>/asignar-mee', methods=['POST'])
def checklist_item_asignar_mee(item_id):
    """Guarda el material MEE elegido para un item + cantidad calculada.

    Body: {mee_codigo, cantidad_unidades, decoracion_tipo (opcional)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    mee_codigo = (d.get('mee_codigo') or '').strip()
    cantidad = float(d.get('cantidad_unidades') or 0)
    decoracion = (d.get('decoracion_tipo') or '').strip()
    descripcion_actualizada = (d.get('descripcion') or '').strip()

    conn = get_db(); c = conn.cursor()
    # Si MEE existe, traer su descripcion para poblar el item
    desc_mee = ''
    if mee_codigo:
        rm = c.execute("SELECT descripcion FROM maestro_mee WHERE codigo=?", (mee_codigo,)).fetchone()
        desc_mee = rm[0] if rm else ''

    sets = ['mee_codigo_asignado=?', 'cantidad_unidades=?', 'actualizado_at=datetime(\'now\')']
    params = [mee_codigo, cantidad]
    if decoracion:
        sets.append('decoracion_tipo=?'); params.append(decoracion)
    if desc_mee:
        sets.append('codigo_mp=?'); params.append(mee_codigo)
    if descripcion_actualizada:
        sets.append('descripcion=?'); params.append(descripcion_actualizada)
    elif desc_mee:
        sets.append('descripcion=?'); params.append(desc_mee)
    params.append(item_id)
    c.execute(f"UPDATE produccion_checklist SET {', '.join(sets)} WHERE id=?", params)
    if c.rowcount == 0:
        return jsonify({'error': 'Item no encontrado'}), 404
    conn.commit()
    return jsonify({'ok': True, 'item_id': item_id, 'mee_codigo': mee_codigo,
                    'cantidad_unidades': cantidad, 'descripcion': desc_mee or descripcion_actualizada})


@bp.route('/api/programacion/checklist/items/<int:item_id>/solicitar-produccion', methods=['POST'])
def checklist_item_solicitar_produccion(item_id):
    """Genera una entrada en solicitudes_compra_anticipada (cola de Catalina) para el
    item del checklist. Catalina luego decide ruta (inventario/OC/serigrafia).

    Body opcional: {fecha_objetivo, observaciones}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    item = c.execute("""
        SELECT id, produccion_id, producto_nombre, item_tipo, descripcion,
               cantidad_requerida, cantidad_unidades, mee_codigo_asignado,
               decoracion_tipo, fecha_planeada, codigo_mp
        FROM produccion_checklist WHERE id=?
    """, (item_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Item no encontrado'}), 404

    cantidad = float(item[6] or 0) or float(item[5] or 0)
    fecha_obj = (d.get('fecha_objetivo') or item[9] or '').strip()
    observ = (d.get('observaciones') or '').strip()

    # Si ya tiene una solicitud_produccion_id activa, devolverla (idempotente)
    existing = c.execute(
        "SELECT id FROM solicitudes_compra_anticipada WHERE checklist_item_id=? AND estado IN ('pendiente','decidida')",
        (item_id,)
    ).fetchone()
    if existing:
        return jsonify({'ok': True, 'solicitud_id': existing[0], 'ya_existia': True})

    cur = c.execute("""
        INSERT INTO solicitudes_compra_anticipada
          (checklist_item_id, produccion_id, producto_nombre, tipo_item,
           mee_codigo, descripcion, cantidad_unidades, decoracion_tipo,
           fecha_objetivo, estado, solicitado_por, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)
    """, (item_id, item[1], item[2] or '', item[3] or '',
          item[7] or item[10] or '', item[4] or '', cantidad,
          item[8] or '', fecha_obj, user, observ))
    sol_id = cur.lastrowid

    # Actualizar el item: vincular + estado='solicitado'
    c.execute("""
        UPDATE produccion_checklist SET
          solicitud_produccion_id=?,
          estado='solicitado',
          fecha_solicitud=datetime('now'),
          actualizado_at=datetime('now')
        WHERE id=?
    """, (sol_id, item_id))
    conn.commit()
    return jsonify({'ok': True, 'solicitud_id': sol_id, 'item_id': item_id,
                    'mensaje': f'Solicitud {sol_id} enviada a Catalina'})


@bp.route('/api/compras/solicitudes-produccion', methods=['GET'])
def solicitudes_compra_anticipada_list():
    """Lista las solicitudes pendientes (queue de Catalina).

    Querystring: ?estado=pendiente|decidida|todas (default pendiente)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    estado = request.args.get('estado', 'pendiente')
    conn = get_db(); c = conn.cursor()
    where = ""
    params = ()
    if estado != 'todas':
        where = "WHERE sp.estado=?"
        params = (estado,)
    rows = c.execute(f"""
        SELECT sp.id, sp.producto_nombre, sp.tipo_item, sp.mee_codigo,
               sp.descripcion, sp.cantidad_unidades, sp.decoracion_tipo,
               sp.fecha_objetivo, sp.estado, sp.decision, sp.fecha_creacion,
               sp.solicitado_por, sp.observaciones,
               COALESCE(m.stock_actual, 0) as stock_actual,
               COALESCE(m.proveedor, '') as proveedor_default,
               sp.proveedor, sp.oc_numero, sp.tarea_operativa_id
        FROM solicitudes_compra_anticipada sp
        LEFT JOIN maestro_mee m ON m.codigo = sp.mee_codigo
        {where}
        ORDER BY
          CASE sp.estado WHEN 'pendiente' THEN 1 WHEN 'decidida' THEN 2 ELSE 3 END,
          sp.fecha_objetivo ASC, sp.fecha_creacion DESC
        LIMIT 300
    """, params).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # Sugerencia de ruta para cada solicitud
    for it in items:
        tipo = it.get('tipo_item') or ''
        cant = float(it.get('cantidad_unidades') or 0)
        stock = float(it.get('stock_actual') or 0)
        if tipo in ('etiqueta_frontal', 'etiqueta_posterior', 'etiqueta_lateral', 'instructivo'):
            it['ruta_sugerida'] = 'oc'  # etiquetas siempre OC
        elif it.get('decoracion_tipo') in ('serigrafia', 'tampografia'):
            it['ruta_sugerida'] = 'serigrafia' if it['decoracion_tipo']=='serigrafia' else 'tampografia'
        elif stock >= cant and stock > 0:
            it['ruta_sugerida'] = 'inventario'
        else:
            it['ruta_sugerida'] = 'oc'
    pendientes = sum(1 for x in items if x.get('estado')=='pendiente')
    return jsonify({'items': items, 'total': len(items), 'pendientes': pendientes})


# Alias grupales: cuando una tarea se asigna a un grupo (ej. "operarios"),
# expandir a la lista real de usernames. Los grupos pueden solaparse.
_GRUPOS_USUARIOS = {
    'operarios': ['luz', 'miguel', 'felipe', 'valentina'],  # planta operacion
    'jefes':     ['luz', 'daniela', 'hernando'],
    'compras':   ['catalina'],
    'gerencia':  ['sebastian', 'alejandro'],
    'rrhh':      ['evelin', 'gisseth'],
    'todos':     ['sebastian', 'alejandro', 'catalina', 'luz', 'daniela',
                  'hernando', 'miguel', 'felipe', 'valentina', 'mayra',
                  'evelin', 'gisseth', 'jefferson'],
}


def _resolver_emails_asignados(asignado_a_csv):
    """Convierte un CSV de usernames/grupos en lista de emails unicos.

    Ejemplo:
      'luz,operarios' → ['luz@..', 'miguel@..', 'felipe@..', 'valentina@..']
      (luz aparece en ambos, dedup automatico)

    Si un username no tiene email configurado en USER_EMAILS, simplemente
    se omite (no falla). Esto permite que la app funcione mientras
    Sebastian va llenando los EMAIL_USERS env vars en Render.
    """
    if not asignado_a_csv:
        return []
    try:
        from config import USER_EMAILS as _UE
    except Exception:
        return []
    raw = [t.strip().lower() for t in str(asignado_a_csv).split(',') if t.strip()]
    usernames = []
    for token in raw:
        if token in _GRUPOS_USUARIOS:
            usernames.extend(_GRUPOS_USUARIOS[token])
        else:
            usernames.append(token)
    # dedup preservando orden
    seen = set()
    emails = []
    for u in usernames:
        em = (_UE.get(u, '') or '').strip()
        if em and em.lower() not in seen:
            emails.append(em)
            seen.add(em.lower())
    return emails


def _notificar_tarea_operativa(tarea_id):
    """Envia email a los asignados de una tarea operativa recien creada.

    Lee la tarea (en su propia conexion para no chocar con el commit del
    caller), resuelve emails de los asignados via _resolver_emails_asignados,
    y dispara el envio en background thread (no bloquea la respuesta HTTP
    al usuario que decidio).

    Falla silenciosa: si no hay SMTP configurado, no hay emails resueltos,
    o falla el envio, simplemente loggea y sigue. La tarea ya esta en BD.
    """
    import threading
    def _worker():
        try:
            from config import DB_PATH
            import sqlite3 as _sql
            con = _sql.connect(DB_PATH, timeout=30)
            try:
                row = con.execute("""
                    SELECT id, titulo, descripcion, tipo, asignado_a,
                           fecha_objetivo, cantidad, mee_codigo,
                           producto_relacionado, creado_por
                    FROM tareas_operativas WHERE id=?
                """, (tarea_id,)).fetchone()
            finally:
                con.close()
            if not row:
                return
            (_id, titulo, descripcion, tipo, asignado_a, fecha_obj,
             cantidad, mee_codigo, producto, creado_por) = row
            # Push notif in-app a cada asignado (ANTES del email — feedback inmediato)
            try:
                from blueprints.notif import push_notif_multi
                lista = []
                if asignado_a:
                    raw = [t.strip().lower() for t in str(asignado_a).split(',') if t.strip()]
                    GROUP_ALIASES = {'operarios': ['mayerlin','camilo','milton','sebastian_murillo']}
                    for tok in raw:
                        if tok in GROUP_ALIASES:
                            lista.extend(GROUP_ALIASES[tok])
                        else:
                            lista.append(tok)
                if lista:
                    cuerpo = (descripcion or '')[:140]
                    if fecha_obj:
                        cuerpo += f' · 📅 {fecha_obj}'
                    push_notif_multi(
                        lista, 'tarea_asignada', f'Tarea: {titulo}',
                        body=cuerpo,
                        link='/inventarios#tareas',
                        remitente=(creado_por or 'sistema'),
                        importante=bool(fecha_obj)
                    )
            except Exception as _e:
                logger.warning('push_notif tarea_operativa fallo: %s', _e)
            emails = _resolver_emails_asignados(asignado_a)
            if not emails:
                return  # nadie con email configurado, no hay nada que enviar
            # Armar email HTML claro y accionable
            urgencia_color = '#dc2626' if fecha_obj else '#1e40af'
            html = f"""
            <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
              <div style="background:#0f172a;color:#fff;padding:18px 22px">
                <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px">Nueva tarea operativa · EOS Inventarios</div>
                <h2 style="margin:6px 0 0;font-size:18px">{_html_escape(titulo)}</h2>
              </div>
              <div style="padding:18px 22px;color:#1e293b;font-size:14px;line-height:1.55">
                <p style="margin:0 0 12px">{_html_escape(descripcion)}</p>
                <table style="border-collapse:collapse;font-size:13px;margin-top:14px">
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Cantidad</td><td style="font-weight:700">{int(cantidad or 0):,} und</td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Producto</td><td>{_html_escape(producto or '—')}</td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Material</td><td style="font-family:monospace">{_html_escape(mee_codigo or '—')}</td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Fecha objetivo</td><td style="color:{urgencia_color};font-weight:700">{_html_escape(fecha_obj or 'sin fecha')}</td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Tipo</td><td><code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:11px">{_html_escape(tipo or '')}</code></td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Asignada a</td><td>{_html_escape(asignado_a or '')}</td></tr>
                  <tr><td style="padding:4px 12px 4px 0;color:#64748b">Creada por</td><td>{_html_escape(creado_por or '')}</td></tr>
                </table>
                <div style="margin-top:18px;padding:12px 14px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:6px;color:#166534;font-size:13px">
                  Marca <b>Completar</b> en el modulo cuando termines:<br>
                  <a href="{APP_BASE_URL}/inventarios" style="color:#0f766e;font-weight:600">Planta → Programación → Tareas operativas</a>
                </div>
              </div>
              <div style="background:#f8fafc;padding:12px 22px;font-size:11px;color:#64748b;border-top:1px solid #e2e8f0">
                Esta notificacion se envio automaticamente. No respondas a este correo.
              </div>
            </div>
            """
            asunto = f"[EOS] Tarea pendiente: {titulo}"
            try:
                from notificaciones import SistemaNotificaciones
                import os as _os
                sn = SistemaNotificaciones(
                    email_remitente=_os.environ.get('EMAIL_REMITENTE', ''),
                    contraseña=_os.environ.get('EMAIL_PASSWORD', ''),
                    smtp_server=_os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
                    smtp_port=int(_os.environ.get('SMTP_PORT', '587')),
                )
                sn._enviar_email(asunto, html, destinatarios=emails)
            except Exception:
                import logging
                logging.getLogger('programacion').warning(
                    'notificacion tarea operativa #%s fallo', tarea_id, exc_info=True
                )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def _html_escape(s):
    """HTML-escape minimo para meter strings en templates de email."""
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


@bp.route('/api/compras/solicitudes-produccion/<int:sol_id>/decidir', methods=['POST'])
def solicitudes_compra_anticipada_decidir(sol_id):
    """Catalina decide ruta para una solicitud:
       inventario | oc | serigrafia | tampografia | etiqueta_adhesiva

    Body: {decision, proveedor?, fecha_objetivo?, observaciones?, asignado_a? (CSV)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    decision = (d.get('decision') or '').strip()
    if decision not in ('inventario', 'oc', 'serigrafia', 'tampografia', 'etiqueta_adhesiva'):
        return jsonify({'error': 'decision invalida'}), 400
    proveedor = (d.get('proveedor') or '').strip()
    fecha_obj = (d.get('fecha_objetivo') or '').strip()
    asignado_a = (d.get('asignado_a') or '').strip()
    obs = (d.get('observaciones') or '').strip()

    conn = get_db(); c = conn.cursor()
    sol = c.execute("""
        SELECT id, checklist_item_id, producto_nombre, tipo_item, mee_codigo,
               descripcion, cantidad_unidades, decoracion_tipo, fecha_objetivo
        FROM solicitudes_compra_anticipada WHERE id=?
    """, (sol_id,)).fetchone()
    if not sol:
        return jsonify({'error': 'Solicitud no encontrada'}), 404

    tarea_id = None
    oc_num = ''

    # Si la decision es 'inventario' Y hay decoracion (serigrafia/tampografia),
    # generar tarea operativa para sacar envases de bodega y mandarlos a decorar
    if decision in ('serigrafia', 'tampografia'):
        # Genera tarea operativa: sacar envases blancos de bodega para enviar
        titulo = f"Sacar {int(sol[6])} envases para {decision} - {sol[2]}"
        descripcion = (
            f"Sacar de bodega {int(sol[6])} unidades de {sol[5] or sol[4]} "
            f"para enviar a {decision} con proveedor {proveedor or 'por definir'}. "
            f"Producto destino: {sol[2]}. {obs}"
        )
        cur = c.execute("""
            INSERT INTO tareas_operativas
              (titulo, descripcion, tipo, producto_relacionado, mee_codigo,
               cantidad, asignado_a, fecha_objetivo, estado,
               origen_tipo, origen_id, creado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', 'solicitud_produccion', ?, ?)
        """, (titulo, descripcion,
              f'sacar_envases_{decision}',
              sol[2], sol[4] or '', sol[6],
              asignado_a or 'luz,operarios',
              fecha_obj or sol[8] or '',
              sol_id, user))
        tarea_id = cur.lastrowid
    elif decision == 'inventario':
        titulo = f"Sacar {int(sol[6])} de bodega - {sol[5] or sol[4]}"
        descripcion = (
            f"Producción {sol[2]} requiere {int(sol[6])} unidades de "
            f"{sol[5] or sol[4]}. Sacar de bodega y dejar listo. {obs}"
        )
        cur = c.execute("""
            INSERT INTO tareas_operativas
              (titulo, descripcion, tipo, producto_relacionado, mee_codigo,
               cantidad, asignado_a, fecha_objetivo, estado,
               origen_tipo, origen_id, creado_por)
            VALUES (?, ?, 'sacar_inventario', ?, ?, ?, ?, ?, 'pendiente',
                    'solicitud_produccion', ?, ?)
        """, (titulo, descripcion, sol[2], sol[4] or '', sol[6],
              asignado_a or 'luz,operarios',
              fecha_obj or sol[8] or '',
              sol_id, user))
        tarea_id = cur.lastrowid
    elif decision in ('oc', 'etiqueta_adhesiva'):
        # Auto-crear OC en estado Borrador con los datos de la solicitud,
        # linkeada bidireccionalmente con el item del checklist y la
        # solicitud anticipada. Asi Catalina solo entra a /compras a
        # ajustar precios y autorizarla — no tiene que recrear el item.
        # Cuando la OC se reciba en /recepcion, recibir_oc cierra el
        # item del checklist automaticamente via oc_numero.
        try:
            from datetime import datetime as _dt
            year = _dt.now().year
            row = c.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER)),0) "
                "FROM ordenes_compra WHERE numero_oc LIKE ?",
                (f'OC-{year}-%',)
            ).fetchone()
            seq = (row[0] or 0) + 1
            oc_num = f'OC-{year}-{seq:04d}'
            categoria = 'MEE'  # envases/etiquetas/decoracion siempre son MEE
            obs_oc = (
                f'Auto-generada desde Solicitud #{sol_id} (decision: {decision}). '
                f'Producto destino: {sol[2]}. '
                f'{obs}'
            ).strip()
            c.execute("""
                INSERT INTO ordenes_compra
                  (numero_oc, fecha, estado, proveedor, observaciones,
                   creado_por, fecha_entrega_est, categoria)
                VALUES (?, ?, 'Borrador', ?, ?, ?, ?, ?)
            """, (oc_num, _dt.now().isoformat(), proveedor or 'POR DEFINIR',
                  obs_oc, user, fecha_obj or sol[8] or '', categoria))
            # Item de la OC con la cantidad del checklist
            c.execute("""
                INSERT INTO ordenes_compra_items
                  (numero_oc, codigo_mp, nombre_mp, cantidad_g,
                   precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, 0, 0)
            """, (oc_num, sol[4] or '', sol[5] or sol[4] or '', sol[6] or 0))
            # Linkear bidireccionalmente
            c.execute(
                "UPDATE solicitudes_compra_anticipada SET oc_numero=? WHERE id=?",
                (oc_num, sol_id)
            )
            c.execute(
                "UPDATE produccion_checklist SET oc_numero=? WHERE id=?",
                (oc_num, sol[1])
            )
            # Crear proveedor si no existe (alimenta catalogo)
            if proveedor:
                exists = c.execute(
                    "SELECT 1 FROM proveedores WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?))",
                    (proveedor,)
                ).fetchone()
                if not exists:
                    try:
                        c.execute("""
                            INSERT INTO proveedores
                              (nombre, categoria, fecha_creacion, activo)
                            VALUES (?, ?, ?, 1)
                        """, (proveedor, categoria, _dt.now().isoformat()))
                    except Exception:
                        pass
            oc_num_creada = oc_num
            oc_num = oc_num_creada  # para el return
        except Exception as _e:
            # Si falla el auto-create, queda como antes (Catalina crea manual)
            oc_num = ''

    # Actualizar la solicitud
    c.execute("""
        UPDATE solicitudes_compra_anticipada SET
          estado='decidida', decision=?, decidido_por=?,
          fecha_decision=datetime('now'),
          proveedor=?, tarea_operativa_id=?, observaciones=?
        WHERE id=?
    """, (decision, user, proveedor, tarea_id, obs, sol_id))
    # Marcar el item del checklist:
    #   inventario  → en_transito (ya existe, esperando que el operario lo saque)
    #   oc/etiqueta_adhesiva → solicitado (con oc_numero linkeada para cierre auto)
    #   serigrafia/tampografia → solicitado (esperando tarea operativa)
    c.execute("""
        UPDATE produccion_checklist SET
          estado=CASE WHEN ? IN ('inventario') THEN 'en_transito'
                      ELSE 'solicitado' END,
          actualizado_at=datetime('now')
        WHERE id=?
    """, (decision, sol[1]))
    conn.commit()
    # Notificar a los asignados (background thread, falla silenciosa).
    # Esto cierra la queja "no me esta llegando la alerta" — antes la tarea
    # se creaba en BD pero nadie recibia email, solo aparecia en la pantalla
    # de Planta si alguien entraba a verla.
    if tarea_id:
        try:
            _notificar_tarea_operativa(tarea_id)
        except Exception:
            pass
    msg_extra = ''
    if tarea_id:
        msg_extra = f' (tarea operativa #{tarea_id} creada · email enviado a asignados)'
    elif oc_num:
        msg_extra = f' (OC {oc_num} creada en Borrador — Catalina ajusta precios y autoriza)'
    return jsonify({
        'ok': True, 'solicitud_id': sol_id, 'decision': decision,
        'tarea_operativa_id': tarea_id,
        'oc_numero': oc_num,
        'mensaje': f'Solicitud {sol_id} marcada como {decision}' + msg_extra,
    })


@bp.route('/api/tareas-operativas', methods=['GET'])
def tareas_operativas_list():
    """Lista de tareas operativas. Querystring:
       ?usuario=<username> (filtra por asignado_a)
       ?estado=pendiente|completada|todas (default pendiente+en_progreso)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario = (request.args.get('usuario') or '').strip().lower()
    estado_q = (request.args.get('estado') or '').strip()
    conn = get_db(); c = conn.cursor()
    where = []
    params = []
    if estado_q == 'todas':
        pass
    elif estado_q in ('pendiente', 'en_progreso', 'completada', 'cancelada'):
        where.append("estado=?"); params.append(estado_q)
    else:
        where.append("estado IN ('pendiente','en_progreso')")
    if usuario:
        where.append("(LOWER(asignado_a) LIKE ? OR asignado_a='')")
        params.append(f"%{usuario}%")
    sql = "SELECT * FROM tareas_operativas"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_objetivo ASC, fecha_creacion DESC LIMIT 300"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'tareas': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/tareas-operativas/<int:tarea_id>/completar', methods=['POST'])
def tareas_operativas_completar(tarea_id):
    """Operario marca la tarea como completada.

    Cierra la cadena causal completa: tarea operativa → solicitud anticipada
    → item del checklist. Asi cuando el operario marca "ya saque los envases",
    el item del checklist Pre-Produccion pasa a 'recibido' automaticamente y
    el % listo de la card del producto sube sin intervencion manual.

    Body opcional: {observaciones, cantidad_real (si difiere)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    obs = (d.get('observaciones') or '').strip()
    conn = get_db(); c = conn.cursor()
    cur = c.execute("""
        UPDATE tareas_operativas SET
          estado='completada',
          completado_por=?,
          fecha_completado=datetime('now'),
          observaciones_cierre=?
        WHERE id=? AND estado IN ('pendiente','en_progreso')
    """, (user, obs, tarea_id))
    if cur.rowcount == 0:
        return jsonify({'error': 'Tarea no encontrada o ya completada'}), 404
    # Marcar la solicitud_produccion origen como completada (si aplica)
    # y propagar al item del checklist como 'recibido'.
    sol_row = c.execute("""
        SELECT id, checklist_item_id FROM solicitudes_compra_anticipada
        WHERE tarea_operativa_id=?
    """, (tarea_id,)).fetchone()
    checklist_item_id = None
    if sol_row:
        sol_id, checklist_item_id = sol_row[0], sol_row[1]
        c.execute(
            "UPDATE solicitudes_compra_anticipada SET estado='completada' WHERE id=?",
            (sol_id,)
        )
        if checklist_item_id:
            c.execute("""
                UPDATE produccion_checklist SET
                  estado='recibido',
                  fecha_recibido=date('now'),
                  actualizado_at=datetime('now')
                WHERE id=?
            """, (checklist_item_id,))
    conn.commit()
    return jsonify({
        'ok': True,
        'tarea_id': tarea_id,
        'checklist_item_id': checklist_item_id,
        'mensaje': 'Tarea completada' + (
            ' · checklist actualizado' if checklist_item_id else ''
        ),
    })


@bp.route('/api/tareas-operativas', methods=['POST'])
def tareas_operativas_crear():
    """Crear una tarea operativa manualmente (para jefes / Catalina).

    Body: {titulo, descripcion, tipo, asignado_a, fecha_objetivo,
           producto_relacionado?, cantidad?, mee_codigo?}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'titulo requerido'}), 400
    conn = get_db(); c = conn.cursor()
    cur = c.execute("""
        INSERT INTO tareas_operativas
          (titulo, descripcion, tipo, producto_relacionado, mee_codigo,
           cantidad, asignado_a, fecha_objetivo, estado,
           origen_tipo, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', 'manual', ?)
    """, (
        titulo, (d.get('descripcion') or '').strip(),
        (d.get('tipo') or 'general').strip(),
        (d.get('producto_relacionado') or '').strip(),
        (d.get('mee_codigo') or '').strip(),
        float(d.get('cantidad') or 0),
        (d.get('asignado_a') or '').strip(),
        (d.get('fecha_objetivo') or '').strip(),
        user
    ))
    conn.commit()
    tarea_id = cur.lastrowid
    # Notificar a los asignados (background, falla silenciosa)
    try:
        _notificar_tarea_operativa(tarea_id)
    except Exception:
        pass
    return jsonify({'ok': True, 'tarea_id': tarea_id})
