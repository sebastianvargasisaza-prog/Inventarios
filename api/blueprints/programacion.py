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
import os, json, logging, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta, date
from database import get_db

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

    _today_str = str(__import__('datetime').date.today())

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

    today = __import__('datetime').date.today()

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
                prod_date = __import__('datetime').date.fromisoformat(prox_prod)
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

        projection.append({
            'producto': prod,
            'lote_kg': lote_kg,
            'vel_mes': round(vel_mes, 1),
            'vel_dia': round(vel_dia, 2),
            'stock_actual': stock_uds,
            'dias_cobertura': round(dias_cob, 0) if dias_cob < 999 else None,
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
    """List all future production events."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, producto, fecha_programada, lotes, estado, observaciones, creado_en
           FROM produccion_programada
           ORDER BY fecha_programada"""
    ).fetchall()
    return jsonify([{
        'id': r[0], 'producto': r[1], 'fecha': r[2],
        'lotes': r[3], 'estado': r[4], 'observaciones': r[5], 'creado_en': r[6]
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


@bp.route('/api/programacion/programar/<int:evento_id>/completar', methods=['POST'])
def prog_completar_evento(evento_id):
    """Mark a production event as completed."""
    conn = get_db()
    conn.execute(
        "UPDATE produccion_programada SET estado='completado' WHERE id=?",
        (evento_id,)
    )
    conn.commit()
    return jsonify({'ok': True, 'id': evento_id})


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


@bp.route('/api/programacion/generar-oc', methods=['POST'])
def prog_generar_oc():
    """
    Analiza faltantes de MP por producto y crea solicitudes de compra automáticas.
    Sólo crea SOL si no existe ya una pendiente para el mismo MP (dedup 7 días).
    """
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db()
    vel_data = _shopify_velocity(conn, days=60)
    mp_stock = _get_mp_stock(conn)
    formulas = _get_formulas(conn)
    cal = _fetch_calendar_events(days_ahead=90)

    if not formulas:
        return jsonify({'error': 'Sin fórmulas cargadas'}), 400

    china_mps_set = _get_china_mps(conn)
    projection, alerts = _project_stock(
        conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []),
        china_mps=china_mps_set
    )

    # Collect all missing MPs across products
    mp_deficit = {}  # codigo -> {nombre, deficit_g, productos}
    for prod in projection:
        if prod['mp_lista']:
            continue
        for mp in prod.get('mp_check', []):
            if mp['deficit_g'] > 0:
                cod = mp['material_id']
                if cod not in mp_deficit:
                    mp_deficit[cod] = {
                        'nombre': mp['nombre'],
                        'deficit_g': 0,
                        'productos': [],
                    }
                mp_deficit[cod]['deficit_g'] += mp['deficit_g']
                mp_deficit[cod]['productos'].append(prod['producto'])

    if not mp_deficit:
        return jsonify({'ok': True, 'mensaje': 'No hay déficits de MP — sin OC necesaria', 'creadas': []})

    # Check for existing pending solicitudes (dedup last 7 days)
    since_7d = (datetime.now() - timedelta(days=7)).isoformat()
    existing = conn.execute(
        "SELECT observaciones FROM solicitudes_compra WHERE estado='Pendiente' AND fecha >= ? AND categoria='Materia Prima'",
        (since_7d,)
    ).fetchall()
    existing_obs = ' '.join(r[0] or '' for r in existing).upper()

    # Generate SOL number
    year = datetime.now().strftime('%Y')
    last_n = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM solicitudes_compra WHERE numero LIKE ?",
        (f"SOL-{year}-%",)
    ).fetchone()[0] or 0
    sol_num = last_n + 1

    sol_numero = f"SOL-{year}-{sol_num:04d}"
    productos_str = ', '.join(set(p for v in mp_deficit.values() for p in v['productos']))
    obs = f"Auto-generada Centro Programación — Déficit MP para: {productos_str[:200]}"

    conn.execute("""INSERT INTO solicitudes_compra
        (numero, fecha, estado, solicitante, urgencia, observaciones, area, empresa, categoria, tipo)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (sol_numero, datetime.now().isoformat(), 'Pendiente',
         session.get('compras_user', 'Sistema'), 'Alta', obs,
         'Produccion', 'Espagiria', 'Materia Prima', 'Compra'))

    items_created = []
    for cod, info in mp_deficit.items():
        just = f"Déficit para producción de: {', '.join(info['productos'][:3])}"
        conn.execute("""INSERT INTO solicitudes_compra_items
            (numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion)
            VALUES (?,?,?,?,?,?)""",
            (sol_numero, cod, info['nombre'],
             info['deficit_g'], 'g', just))
        items_created.append({
            'codigo': cod,
            'nombre': info['nombre'],
            'deficit_g': round(info['deficit_g'], 1),
        })

    conn.commit()

    return jsonify({
        'ok': True,
        'solicitud': sol_numero,
        'n_items': len(items_created),
        'items': items_created,
        'mensaje': f'Solicitud {sol_numero} creada con {len(items_created)} MPs faltantes',
    })


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

    meses = min(int(request.args.get('meses', 2)), 12)
    days_ahead = meses * 31  # margen extra para cubrir mes completo

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

    # ── 2b. Fuente secundaria: produccion_programada (DB local) ──────────
    # Complementa cuando el calendario no tiene eventos o no hay SKUs en títulos
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

    for prod_ev in producciones:
        prod   = prod_ev['producto']
        kg_ev  = prod_ev['kg']
        mes    = prod_ev['mes']
        formula = formulas.get(prod, {})
        lote_kg = formula.get('lote_size_kg', 1)
        factor  = kg_ev / lote_kg if lote_kg > 0 else 1.0

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

    # ── 4. Cruzar con stock actual → déficit ────────────────────────────────
    def _lookup_stock(mid, nombre):
        """Busca stock por material_id primero, luego por nombre.
        Retorna -1 si el MP es ilimitado (producido en sitio: agua, etc.)."""
        if _is_unlimited_mp(nombre):
            return -1  # sentinel: always available, no purchase needed
        s = mp_stock.get(mid)
        if s is not None: return s
        s = mp_stock.get(mid.upper())
        if s is not None: return s
        s = mp_stock.get(nombre.upper())
        if s is not None: return s
        s = mp_stock.get(_norm_mp_name(nombre))
        if s is not None: return s
        return 0

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
            _qty = (f'{round(data["total_g"]/1000, 2)} kg'
                    if data['total_g'] >= 100 else f'{round(data["total_g"], 1)} g')
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

    return jsonify({
        'meses':           meses,
        'producciones':    producciones,
        'meses_unicos':    meses_unicos,
        'total_prods':     total_prods,
        'total_mps':       total_mps,
        'mps_deficit':     mps_deficit,
        'mps_ok_count':    len(mps_ok),
        'bulk_opps':       bulk_opps,
        'cal_error':       cal.get('error'),
        'generado_en':     _dt.datetime.now().isoformat(),
    })
