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
from config import ADMIN_USERS, APP_BASE_URL, CALIDAD_USERS, COMPRAS_USERS
from inventario_helpers import stock_mp_total, stock_mp_disponible
from audit_helpers import audit_log

# Bug latente preexistente fixed 2-may-2026: el blueprint usaba `log.warning()`
# y `logger.warning()` sin tener el logger definido. Cualquier call a un branch
# de error fallaba con NameError. Audit zero-error.
log = logging.getLogger('programacion')
logger = log  # alias compatible con call-sites históricos

bp = Blueprint('programacion', __name__)

CALENDAR_ID      = os.environ.get('CALENDAR_ID', '1c8aa3f1d9024d5eeead72447c0606f927cfd6ee6d1d2e5d28bf1b252959f396@group.calendar.google.com')
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
    """Parse iCal text and return list of {titulo, fecha, descripcion, id} dicts.

    Supports:
      - SUMMARY (titulo)
      - DESCRIPTION (descripcion, with line continuations)
      - DTSTART (start date)
      - UID (event id)
      - RRULE expansion: FREQ=DAILY/WEEKLY with INTERVAL and COUNT/UNTIL
        (covers our use case: recurrent batches every N days)
      - EXDATE (excluded dates)
      - Status: skip CANCELLED events
    """
    import re as _re
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    # Window also includes some past so /auditoria-calendar can see history
    window_start = today - timedelta(days=180)
    events = []

    # Unfold lines: iCal continuation = next line starts with space/tab
    unfolded_lines = []
    for raw_line in text.splitlines():
        if raw_line.startswith((' ', '\t')) and unfolded_lines:
            unfolded_lines[-1] += raw_line[1:]
        else:
            unfolded_lines.append(raw_line)
    text_unfolded = '\n'.join(unfolded_lines)

    def _unescape_ical(s):
        return s.replace(r'\n', '\n').replace(r'\,', ',').replace(r'\;', ';').replace(r'\\', '\\')

    # Split into VEVENT blocks
    for block in _re.split(r'BEGIN:VEVENT', text_unfolded)[1:]:
        summary = ''
        description = ''
        dt_str = ''
        uid = ''
        status = ''
        rrule = ''
        exdates = set()
        for line in block.splitlines():
            line = line.rstrip()
            if line.startswith('SUMMARY:'):
                summary = _unescape_ical(line[8:]).strip()
            elif line.startswith('DESCRIPTION:'):
                description = _unescape_ical(line[12:]).strip()
            elif line.startswith('DTSTART'):
                val = line.split(':', 1)[-1].strip()
                dt_str = val[:8]
            elif line.startswith('UID:'):
                uid = line[4:].strip()
            elif line.startswith('STATUS:'):
                status = line[7:].strip().upper()
            elif line.startswith('RRULE:'):
                rrule = line[6:].strip()
            elif line.startswith('EXDATE'):
                # EXDATE;VALUE=DATE:20260518 or EXDATE:20260518T...
                val = line.split(':', 1)[-1].strip()
                for d_str in val.split(','):
                    d_str = d_str.strip()[:8]
                    if len(d_str) == 8:
                        try:
                            exdates.add(date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8])))
                        except ValueError:
                            pass

        if not summary or len(dt_str) != 8 or status == 'CANCELLED':
            continue
        try:
            base_date = date(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]))
        except ValueError:
            continue

        # Generate occurrences
        occurrences = []
        if rrule:
            # Parse RRULE params
            rr = {}
            for part in rrule.split(';'):
                if '=' in part:
                    k, v = part.split('=', 1)
                    rr[k.strip().upper()] = v.strip()
            freq = rr.get('FREQ', '').upper()
            try:
                interval = int(rr.get('INTERVAL', '1'))
            except ValueError:
                interval = 1
            count = None
            if 'COUNT' in rr:
                try:
                    count = int(rr['COUNT'])
                except ValueError:
                    count = None
            until = None
            if 'UNTIL' in rr:
                u = rr['UNTIL'][:8]
                if len(u) == 8:
                    try:
                        until = date(int(u[:4]), int(u[4:6]), int(u[6:8]))
                    except ValueError:
                        until = None

            # Step in days
            if freq == 'DAILY':
                step_days = interval
            elif freq == 'WEEKLY':
                step_days = interval * 7
            elif freq == 'MONTHLY':
                step_days = interval * 30  # approx (good enough for our cadences)
            elif freq == 'YEARLY':
                step_days = interval * 365
            else:
                step_days = None

            if step_days:
                # Cap occurrences (safety: max 200 per series)
                max_occ = count if count is not None else 200
                cur = base_date
                for i in range(min(max_occ, 200)):
                    if until and cur > until:
                        break
                    if cur not in exdates:
                        occurrences.append(cur)
                    cur = cur + timedelta(days=step_days)
            else:
                occurrences = [base_date]
        else:
            occurrences = [base_date]

        # Filter by window and append
        for occ in occurrences:
            if window_start <= occ <= cutoff:
                events.append({
                    'titulo': summary,
                    'fecha': occ.isoformat(),
                    'descripcion': description,
                    'id': uid,
                })

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
            # Sebastián 1-may-2026 audit: ANTES era silencioso · si Calendar
            # cae nadie sabía. Ahora log.warning + tipo de error explícito.
            log = logging.getLogger('inventario.programacion')
            log.warning('iCal fetch fallo (%s): %s', type(e).__name__, e)
            return {'events': [], 'error': f'iCal error: {e}', 'source': 'ical'}

    # ── Option 2: Google Calendar API (requires GOOGLE_API_KEY) ──────────────
    if not GOOGLE_API_KEY:
        return {'events': [], 'error': 'Configura GCAL_ICAL_URL en Render para leer el calendario', 'source': 'none'}

    now = datetime.utcnow()
    # Sebastián 1-may-2026: 'lunes vacío' · cambiar time_min al LUNES de esta
    # semana (no a now) para incluir eventos de lun-mar-mié-jue cuando hoy es vie.
    lunes_semana = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    time_min = lunes_semana.strftime('%Y-%m-%dT%H:%M:%SZ')
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

    # Proveedor por MP · Sebastian 4-may-2026 (Catalina): normalizar al
    # primer "case canónico" para que "Agenquimicos" y "AGENQUIMICOS" no
    # caigan en grupos distintos al agrupar por proveedor.
    _prov_map = {}
    _prov_canonical = {}  # lowercase trimmed → primera variante observada
    try:
        for row in conn.execute(
            "SELECT codigo_mp, COALESCE(proveedor,'') FROM maestro_mps"
        ).fetchall():
            prov_raw = (row[1] or '').strip()
            if not prov_raw:
                _prov_map[row[0]] = ''
                continue
            key = prov_raw.lower()
            canonical = _prov_canonical.setdefault(key, prov_raw)
            _prov_map[row[0]] = canonical
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
    if 'compras_user' not in session:
        return jsonify({'ok': False, 'error': 'No autorizado'}), 401
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
    Acepta sesión 'compras_user' o ?clave=AUTO_PLAN_CRON_KEY (cron Render).
    Siempre retorna JSON; nunca lanza 500 HTML.

    Sebastián 1-may-2026 audit: antes era public · ahora requiere uno de los 2.
    """
    from blueprints.auto_plan import _validar_acceso_cron
    es_cron, _err = _validar_acceso_cron(request)
    if 'compras_user' not in session and not es_cron:
        return jsonify({'ok': False, 'error': 'No autorizado'}), 401
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
                    # ⚠ Audit zero-error 2-may-2026: `inventory_quantity` es ON HAND
                    # (incluye committed). Memoria de Sebastián: para MRP/forecast
                    # debe usarse AVAILABLE (= On hand - Committed). Fix completo
                    # requiere segunda API call a /inventory_levels.json con
                    # inventory_item_ids. Pendiente en ROADMAP. Por ahora se usa
                    # On hand y el modelo descuenta pipeline 7d como aproximación.
                    inv_qty_on_hand = int(variant.get('inventory_quantity', 0) or 0)
                    inv_item_id = variant.get('inventory_item_id')  # para fix futuro
                    all_variants.append({
                        'sku': sku_raw, 'titulo': title,
                        'inv_qty': inv_qty_on_hand,
                        'inv_item_id': inv_item_id,
                    })

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
    if 'compras_user' not in session:
        return jsonify({'ok': False, 'error': 'No autorizado'}), 401
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
    """Cancel a scheduled production event.

    Audit zero-error 2-may-2026: guard contra cancelar producciones que ya
    descontaron inventario. Si fue completada, redirigir a /revertir-completado
    que sí revierte stock. Cancelar una producción completada sin revertir
    dejaría stock fantasma (consumido pero sin razón) → drift de inventario.
    """
    if 'compras_user' not in session:
        return jsonify({'ok': False, 'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT estado, COALESCE(inventario_descontado_at,'') FROM produccion_programada WHERE id=?",
        (evento_id,)
    ).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Producción no encontrada'}), 404
    estado_actual = row[0] or ''
    descontado_at = row[1]
    if estado_actual == 'cancelado':
        return jsonify({'ok': True, 'id': evento_id, 'ya_cancelado': True})
    if estado_actual == 'completado' or descontado_at:
        return jsonify({
            'ok': False,
            'error': 'Producción ya completada · usar /revertir-completado para revertir descuento de inventario',
            'codigo': 'YA_COMPLETADA',
            'inventario_descontado_at': descontado_at or None,
        }), 409
    estado_anterior = estado_actual
    c.execute(
        "UPDATE produccion_programada SET estado='cancelado' WHERE id=?",
        (evento_id,)
    )
    try:
        audit_log(c, usuario=user, accion='CANCELAR_PRODUCCION',
                  tabla='produccion_programada', registro_id=evento_id,
                  antes={'estado': estado_anterior},
                  despues={'estado': 'cancelado'},
                  detalle=f"Canceló producción id={evento_id} (estaba {estado_anterior})")
    except Exception as e:
        log.warning('audit_log CANCELAR_PRODUCCION fallo: %s', e)
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
    marca la sala asignada como 'ocupada' y DESCUENTA INVENTARIO MP.

    Sebastian 5-may-2026 (Luis Enrique): "cuando carguen produccion de
    materia prima de una descuente". Antes el descuento estaba en
    /completar pero las producciones quedaban en envasado y nunca se
    completaban → MPs no salian del inventario. Ahora el descuento es
    al INICIAR (cuando el operario fisicamente saca MP de bodega).

    Comportamiento:
      1. Atomic claim de inventario_descontado_at (idempotencia race-safe)
      2. Calcula MPs desde formula_items (cantidad_g_por_lote * lotes,
         fallback a porcentaje * kg)
      3. Pre-check stock: si falta para alguna MP → 422 sin tocar nada
      4. INSERT movimientos tipo 'Salida' por lote (FEFO)
      5. Set inicio_real_at + sala='ocupada'
      6. Audit log INICIAR_PRODUCCION con detalle de MPs descontadas

    Si descuento falla → rollback completo, inicio_real_at NO se setea
    (la producción queda en estado 'pendiente_iniciar' lista para
    re-intentar tras corregir stock).

    Idempotente: si ya tiene inicio_real_at, retorna ok=True con el ts
    existente.

    Body opcional: {forzar_redescuento: true} para admin (re-iniciar
    producción cuyo descuento fue revertido manualmente).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    body = request.get_json(silent=True) or {}
    forzar = bool(body.get('forzar_redescuento'))
    if forzar and user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin puede forzar re-descuento'}), 403

    conn = get_db(); c = conn.cursor()
    pp = c.execute("""SELECT id, producto, area_id, inicio_real_at, fin_real_at,
                              COALESCE(inventario_descontado_at,'') as desc_at
                      FROM produccion_programada WHERE id=?""", (evento_id,)).fetchone()
    if not pp:
        return jsonify({'error': 'produccion no existe'}), 404
    if pp[3]:  # ya iniciada
        return jsonify({
            'ok': True, 'ya_iniciada': True, 'inicio_real_at': pp[3],
            'inventario_descontado_at': pp[5] or None,
        })
    if pp[4]:  # ya terminada
        return jsonify({'error': 'produccion ya terminada'}), 400

    # ── DESCONTAR INVENTARIO MP ATOMICAMENTE ──────────────────────────
    descuento = None
    try:
        descuento = _descontar_mp_produccion(c, evento_id, user, forzar=forzar)
    except _DescuentoError as e:
        try: conn.rollback()
        except Exception: pass
        codigo_http = {
            'SIN_STOCK': 422,
            'SIN_FORMULA': 422,
            'YA_DESCONTADO': 409,
            'PRODUCCION_NO_EXISTE': 404,
        }.get(e.codigo, 500)
        log.warning('iniciar_produccion bloqueado · codigo=%s evento_id=%s msg=%s',
                     e.codigo, evento_id, e)
        return jsonify({
            'ok': False,
            'error': str(e),
            'codigo': e.codigo,
            **e.payload,
        }), codigo_http

    # ── REGISTRAR INICIO + SALA OCUPADA ───────────────────────────────
    c.execute("UPDATE produccion_programada SET inicio_real_at=datetime('now') WHERE id=?",
              (evento_id,))
    sin_formula = bool(descuento.get('sin_formula'))
    nota_descuento = ('SIN FORMULA · sin descuento' if sin_formula
                       else f'MP descontada {descuento["total_g"]:.0f}g')
    if pp[2]:  # tiene sala asignada → marcar ocupada
        prev = c.execute("SELECT estado FROM areas_planta WHERE id=?", (pp[2],)).fetchone()
        c.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=?", (pp[2],))
        c.execute("""INSERT INTO area_eventos
            (area_id, tipo, estado_anterior, estado_nuevo, produccion_id, usuario, nota)
            VALUES (?,?,?,?,?,?,?)""",
            (pp[2], 'iniciar_prod', (prev[0] if prev else None), 'ocupada',
             evento_id, user, f'inicio: {pp[1]} · {nota_descuento}'))
    audit_log(
        c, usuario=user, accion='INICIAR_PRODUCCION',
        tabla='produccion_programada', registro_id=evento_id,
        despues={
            'producto': pp[1], 'area_id': pp[2],
            'inventario_descontado_at': descuento['inventario_descontado_at'],
            'mps_descontadas_count': len(descuento['mps_descontadas']),
            'total_g_descontado': descuento['total_g'],
            'sin_formula': sin_formula,
            'forzar': forzar,
        },
        detalle=(f"Inició producción {pp[1]} (id={evento_id}) · " +
                  (f"SIN formula valida — NO se descontó inventario"
                   if sin_formula
                   else f"descontó {len(descuento['mps_descontadas'])} MPs "
                        f"({descuento['total_g']:.0f}g)")),
    )
    conn.commit()
    return jsonify({
        'ok': True,
        'evento_id': evento_id,
        'inicio_real_at': c.execute(
            "SELECT inicio_real_at FROM produccion_programada WHERE id=?",
            (evento_id,)).fetchone()[0],
        'inventario_descontado_at': descuento['inventario_descontado_at'],
        'mps_descontadas': descuento['mps_descontadas'],
        'total_g_descontado': descuento['total_g'],
        'sin_formula': sin_formula,
        'warning': descuento.get('warning'),
    })


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
        # Sebastián 1-may-2026: guard contra sobrescribir 'limpiando'
        c.execute("""
            UPDATE areas_planta SET estado='sucia'
            WHERE id=? AND estado IN ('ocupada','libre')
        """, (pp[2],))
        c.execute("""INSERT INTO area_eventos
            (area_id, tipo, estado_anterior, estado_nuevo, produccion_id, usuario, nota)
            VALUES (?,?,?,?,?,?,?)""",
            (pp[2], 'terminar_prod', (prev[0] if prev else None), 'sucia',
             evento_id, user, f'fin: {pp[1]} → sala sucia, espera limpieza'))
    # Calcular cycle time real
    cycle = c.execute("""SELECT
        CAST((julianday(fin_real_at) - julianday(inicio_real_at)) * 24 * 60 AS INTEGER) as min
        FROM produccion_programada WHERE id=?""", (evento_id,)).fetchone()
    cycle_min = cycle[0] if cycle else None
    audit_log(c, usuario=user, accion='TERMINAR_PRODUCCION', tabla='produccion_programada',
              registro_id=evento_id,
              despues={'producto': pp[1], 'area_id': pp[2], 'cycle_time_min': cycle_min},
              detalle=f"Terminó producción {pp[1]} (id={evento_id})"
                      + (f" · cycle {cycle_min} min" if cycle_min else ""))
    conn.commit()
    return jsonify({'ok': True, 'evento_id': evento_id,
                    'cycle_time_min': cycle_min})


@bp.route('/api/planta/listo-producir/<path:producto>', methods=['GET'])
def planta_listo_producir(producto):
    """Semaforo de insumos para una produccion programada.

    Sebastian (30-abr-2026): "respuesta inmediata" — quiere ver de un
    vistazo si una produccion tiene todos los MPs disponibles antes
    de programarla. Antes era email "URGENTE confirmacion insumos".

    Query params:
        lotes: int (default 1) — para calcular requerimiento total
                (cantidad_mp = porcentaje * lote_size_kg * lotes * 1000g/kg)

    Devuelve para cada material:
        codigo_mp, nombre, requerido_g, disponible_g, status
        (✅ ok / ⚠ justo / ❌ deficit)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        lotes = int(request.args.get('lotes', 1))
    except (TypeError, ValueError):
        lotes = 1
    conn = get_db(); c = conn.cursor()

    # Buscar formula y lote_size
    fh = c.execute(
        "SELECT producto_nombre, lote_size_kg, unidad_base_g "
        "FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    if not fh:
        return jsonify({'error': 'producto no tiene formula registrada',
                        'items': []}), 404
    nombre_fh, lote_kg, unidad_g = fh
    # cantidad total en g = lote_kg * 1000 * lotes
    total_g = (lote_kg or 0) * 1000 * max(1, lotes)

    items = c.execute("""
        SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
               COALESCE(fi.cantidad_g_por_lote, 0) as cant_lote_g
        FROM formula_items fi
        WHERE UPPER(TRIM(fi.producto_nombre))=UPPER(TRIM(?))
        ORDER BY fi.porcentaje DESC
    """, (nombre_fh,)).fetchall()

    out = []
    deficit_count = 0; justo_count = 0
    for mat_id, mat_nom, pct, cant_lote_g in items:
        # requerido_g: preferir cantidad_g_por_lote si está, si no calcular % * total
        if cant_lote_g and cant_lote_g > 0:
            req_g = cant_lote_g * lotes
        else:
            req_g = (pct or 0) / 100.0 * total_g

        # Disponible en bodega · excluye CUARENTENA/VENCIDO/RECHAZADO
        # Audit zero-error 2-may-2026: SQL anterior usaba 'Ingreso'/'Consumo'
        # (no existen) y devolvía valores negativos siempre · semáforo roto.
        disp_g = stock_mp_disponible(c, mat_id)

        # Status
        if disp_g >= req_g:
            status = 'ok'
        elif disp_g >= req_g * 0.5:
            status = 'justo'; justo_count += 1
        else:
            status = 'deficit'; deficit_count += 1

        out.append({
            'codigo_mp': mat_id,
            'nombre': mat_nom,
            'porcentaje': pct,
            'requerido_g': round(req_g),
            'disponible_g': round(disp_g),
            'status': status,
            'faltante_g': max(0, round(req_g - disp_g)),
        })

    return jsonify({
        'producto': nombre_fh,
        'lote_size_kg': lote_kg,
        'lotes': lotes,
        'total_g': round(total_g),
        'items': out,
        'resumen': {
            'total': len(out),
            'ok': len(out) - justo_count - deficit_count,
            'justo': justo_count,
            'deficit': deficit_count,
            'listo': deficit_count == 0,
        }
    })


# ─── Actividades por operario en sala (turnos con timer) ──────────────────
@bp.route('/api/planta/areas/<int:area_id>/actividades', methods=['GET', 'POST'])
def planta_actividades_sala(area_id):
    """GET: lista actividades de la sala (filtro ?activas=1 → solo en curso).
    POST: inicia un turno de un operario en esta sala.
       body: operario_id (req), tipo (req), descripcion (opt), produccion_id (opt)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(force=True, silent=True) or {}
        try:
            op_id = int(d.get('operario_id') or 0)
        except (TypeError, ValueError):
            op_id = 0
        if not op_id:
            return jsonify({'error': 'operario_id requerido'}), 400
        tipo = (d.get('tipo') or 'produccion').strip().lower()
        if tipo not in ('produccion','dispensacion','envasado','acondicionamiento',
                        'conteo_ciclico','limpieza','mantenimiento','otro'):
            tipo = 'otro'
        # Verificar operario existe
        op_row = c.execute("SELECT nombre, apellido FROM operarios_planta WHERE id=? AND activo=1",
                           (op_id,)).fetchone()
        if not op_row:
            return jsonify({'error': 'operario no existe o inactivo'}), 400
        # Si ya hay un turno activo del mismo operario en cualquier sala, lo cerramos primero
        # (un operario no puede estar en 2 salas a la vez)
        previo = c.execute("""SELECT id, area_id FROM actividades_sala
                              WHERE operario_id=? AND fin_at IS NULL""",
                           (op_id,)).fetchone()
        cerrado_previo = None
        if previo:
            prev_id, prev_area = previo
            c.execute("""UPDATE actividades_sala
                SET fin_at=datetime('now'),
                    duracion_min=CAST((julianday(datetime('now'))-julianday(inicio_at))*24*60 AS INTEGER)
                WHERE id=?""", (prev_id,))
            cerrado_previo = {'actividad_id': prev_id, 'area_id': prev_area}
        # Insertar actividad nueva
        c.execute("""INSERT INTO actividades_sala
            (area_id, operario_id, tipo, descripcion, produccion_id, creado_por)
            VALUES (?,?,?,?,?,?)""",
            (area_id, op_id, tipo,
             (d.get('descripcion') or '').strip() or None,
             d.get('produccion_id') or None, user))
        new_id = c.lastrowid
        # Cambiar estado de la sala a 'ocupada' si no lo estaba
        c.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=? AND estado='libre'", (area_id,))
        # Log evento
        try:
            c.execute("""INSERT INTO area_eventos
                (area_id, tipo, estado_anterior, estado_nuevo, produccion_id, operario_id, usuario, nota)
                VALUES (?,?,?,?,?,?,?,?)""",
                (area_id, 'iniciar_prod', 'libre', 'ocupada',
                 d.get('produccion_id'), op_id, user,
                 f'turno {tipo} de {op_row[0]}'))
        except Exception:
            pass
        conn.commit()
        return jsonify({
            'ok': True,
            'actividad_id': new_id,
            'cerrado_previo': cerrado_previo,
            'operario': (op_row[0] + ' ' + (op_row[1] or '')).strip(),
        }), 201

    # GET — actividades de la sala
    solo_activas = request.args.get('activas') == '1'
    sql = """SELECT a.id, a.operario_id, a.tipo, a.descripcion, a.produccion_id,
                    a.inicio_at, a.fin_at, a.duracion_min, a.observaciones,
                    op.nombre, op.apellido,
                    pp.producto,
                    CAST((julianday('now')-julianday(a.inicio_at))*24*60 AS INTEGER) as min_corridos
             FROM actividades_sala a
             LEFT JOIN operarios_planta op ON op.id = a.operario_id
             LEFT JOIN produccion_programada pp ON pp.id = a.produccion_id
             WHERE a.area_id=?"""
    params = [area_id]
    if solo_activas:
        sql += " AND a.fin_at IS NULL"
    sql += " ORDER BY a.inicio_at DESC LIMIT 50"
    rows = c.execute(sql, params).fetchall()
    out = []
    for r in rows:
        out.append({
            'id': r[0], 'operario_id': r[1], 'tipo': r[2],
            'descripcion': r[3], 'produccion_id': r[4],
            'inicio_at': r[5], 'fin_at': r[6],
            'duracion_min': r[7] if r[6] else r[12],
            'en_curso': r[6] is None,
            'observaciones': r[8],
            'operario_nombre': ((r[9] or '') + ' ' + (r[10] or '')).strip(),
            'producto': r[11],
            'minutos_corridos': r[12] if not r[6] else None,
        })
    return jsonify({'actividades': out, 'area_id': area_id})


@bp.route('/api/planta/actividades/<int:act_id>/terminar', methods=['POST'])
def planta_actividad_terminar(act_id):
    """Cierra el turno de un operario. Calcula duracion_min."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json(force=True, silent=True) or {}
    obs = (d.get('observaciones') or '').strip() or None
    conn = get_db(); c = conn.cursor()
    row = c.execute("""SELECT id, area_id, operario_id, fin_at FROM actividades_sala
                       WHERE id=?""", (act_id,)).fetchone()
    if not row:
        return jsonify({'error': 'actividad no existe'}), 404
    if row[3]:
        return jsonify({'ok': True, 'ya_cerrada': True})
    c.execute("""UPDATE actividades_sala
        SET fin_at=datetime('now'),
            duracion_min=CAST((julianday(datetime('now'))-julianday(inicio_at))*24*60 AS INTEGER),
            observaciones=COALESCE(?, observaciones)
        WHERE id=?""", (obs, act_id))
    # Si no quedan actividades activas en la sala → marcar libre o sucia
    pendientes = c.execute(
        "SELECT COUNT(*) FROM actividades_sala WHERE area_id=? AND fin_at IS NULL",
        (row[1],)
    ).fetchone()[0]
    if pendientes == 0:
        # Si la sala estaba ocupada, pasarla a sucia (necesita limpieza)
        c.execute("""UPDATE areas_planta SET estado='sucia'
                     WHERE id=? AND estado='ocupada'""", (row[1],))
        try:
            c.execute("""INSERT INTO area_eventos
                (area_id, tipo, estado_anterior, estado_nuevo, operario_id, usuario, nota)
                VALUES (?,?,?,?,?,?,?)""",
                (row[1], 'terminar_prod', 'ocupada', 'sucia',
                 row[2], user, 'ultimo turno cerrado'))
        except Exception:
            pass
    conn.commit()
    cycle = c.execute("SELECT duracion_min FROM actividades_sala WHERE id=?", (act_id,)).fetchone()
    return jsonify({'ok': True, 'duracion_min': cycle[0] if cycle else None})


@bp.route('/api/planta/actividades/kpis', methods=['GET'])
def planta_actividades_kpis():
    """KPIs agregados de actividades para indicadores. Filtros:
       ?desde=YYYY-MM-DD  ?hasta=YYYY-MM-DD  (default: ultimos 30 dias)"""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    desde = request.args.get('desde') or ''
    hasta = request.args.get('hasta') or ''
    if not desde:
        desde = (date.today() - timedelta(days=30)).isoformat()
    if not hasta:
        hasta = date.today().isoformat()
    conn = get_db()
    # Total min por operario
    rows_op = conn.execute("""
        SELECT op.nombre, op.apellido,
               COUNT(*) as turnos,
               SUM(COALESCE(a.duracion_min, 0)) as min_total
        FROM actividades_sala a
        LEFT JOIN operarios_planta op ON op.id = a.operario_id
        WHERE a.fin_at IS NOT NULL
          AND DATE(a.inicio_at) >= ? AND DATE(a.inicio_at) <= ?
        GROUP BY a.operario_id
        ORDER BY min_total DESC
    """, (desde, hasta)).fetchall()
    por_operario = [{
        'operario': ((r[0] or '') + ' ' + (r[1] or '')).strip(),
        'turnos': r[2] or 0,
        'min_total': r[3] or 0,
        'horas': round((r[3] or 0)/60, 1),
    } for r in rows_op]
    # Total min por tipo
    rows_t = conn.execute("""
        SELECT tipo, COUNT(*) as turnos, SUM(COALESCE(duracion_min,0)) as mins
        FROM actividades_sala
        WHERE fin_at IS NOT NULL
          AND DATE(inicio_at) >= ? AND DATE(inicio_at) <= ?
        GROUP BY tipo
        ORDER BY mins DESC
    """, (desde, hasta)).fetchall()
    por_tipo = [{
        'tipo': r[0], 'turnos': r[1] or 0,
        'horas': round((r[2] or 0)/60, 1),
    } for r in rows_t]
    # Activas ahora
    activas = conn.execute(
        "SELECT COUNT(*) FROM actividades_sala WHERE fin_at IS NULL"
    ).fetchone()[0]
    return jsonify({
        'desde': desde, 'hasta': hasta,
        'por_operario': por_operario,
        'por_tipo': por_tipo,
        'turnos_activos_ahora': activas,
    })


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
    # Sebastián 1-may-2026: respeta selector de fecha + horizonte 7 días
    # si el día seleccionado está vacío, muestra próximos 7 días (no dejar
    # vacío al jefe cuando hoy es viernes y todo está programado para lunes)
    fecha_param = (request.args.get('fecha') or '').strip()[:10]
    try:
        fecha_sel = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else date.today()
    except Exception:
        fecha_sel = date.today()

    # ── AUTO-LIMPIEZA INDEPENDIENTE AL INICIO (Sebastián 1-may-2026) ──
    # 'sigue mostrando lunes todas, martes mezcla' → cancelar huérfanas SQL-first.
    # Cursor explícito + commit forzado + logs de diagnóstico.
    auto_canceladas_inicial = 0
    auto_cancel_detalle_inicial = []
    auto_clean_diag = {'cal_set_size': 0, 'db_rows_check': 0, 'matched': 0}
    _ac = conn.cursor()
    try:
        _f_inicio = fecha_sel.isoformat()
        _f_fin = (fecha_sel + timedelta(days=6)).isoformat()
        # Set de Calendar (fecha, producto_upper) en horizonte
        _productos_cal = set()
        try:
            from blueprints.auto_plan import (
                _calendar_events_cached as _cec,
                _match_producto_evento as _mpe,
            )
            cal_events = _cec(force_refresh=True) or []
            skus_aliases = {}
            for sku_n, alias_csv in _ac.execute("""
                SELECT producto_nombre, COALESCE(alias_calendar,'')
                FROM sku_planeacion_config
                WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
            """).fetchall():
                skus_aliases[sku_n] = alias_csv
            for ev in cal_events:
                f_ev = (ev.get('fecha') or '')[:10]
                if f_ev < _f_inicio or f_ev > _f_fin: continue
                producto_match = None; best = 0
                for prod_n, alias_csv in skus_aliases.items():
                    try:
                        s = _mpe(prod_n, alias_csv, ev.get('titulo'), ev.get('descripcion',''))
                        if s >= 50 and s > best:
                            best = s; producto_match = prod_n
                    except Exception:
                        continue
                if producto_match:
                    _productos_cal.add((f_ev, producto_match.upper()))
        except Exception as _e:
            logging.getLogger('programacion').warning(f'[centro-mando auto-clean] cal fetch falla: {_e}')
        auto_clean_diag['cal_set_size'] = len(_productos_cal)

        # Sebastián 1-may-2026 estricto Calendar-first: cancelar TODAS las
        # filas DB no iniciadas en horizonte. Calendar es la única fuente
        # de verdad. Si una fila DB no tiene inicio_real_at, es estale o
        # placeholder · debe desaparecer. Si necesita mostrarse, Calendar
        # debe tenerla.
        # Guard único: máximo 200 por GET.
        _db_rows = _ac.execute("""
            SELECT id, producto, date(fecha_programada)
            FROM produccion_programada
            WHERE date(fecha_programada) BETWEEN ? AND ?
              AND COALESCE(estado, 'programado') IN ('', 'programado', 'planeado')
              AND inicio_real_at IS NULL
            LIMIT 200
        """, (_f_inicio, _f_fin)).fetchall()
        auto_clean_diag['db_rows_check'] = len(_db_rows)
        for pid, prod, fecha in _db_rows:
            key = (fecha, (prod or '').upper())
            if _productos_cal and key in _productos_cal:
                # Tiene match Calendar exacto → mantener (Calendar la pre-asigna)
                auto_clean_diag['matched'] += 1
                continue
            # No tiene match O Calendar set vacío → cancelar
            # (si Calendar set está vacío puede ser que feed esté caído,
            # PERO también puede ser que Calendar simplemente no tenga
            # esa producción · eligir limpieza estricta)
            _ac.execute("""
                UPDATE produccion_programada
                  SET estado='cancelado',
                      observaciones = COALESCE(observaciones,'') ||
                        ' [auto-cancelado · estricto Calendar-first]'
                WHERE id=?
            """, (pid,))
            auto_canceladas_inicial += 1
            if len(auto_cancel_detalle_inicial) < 5:
                auto_cancel_detalle_inicial.append(f"{(prod or '?')[:30]} {fecha}")
        # FORZAR commit siempre
        conn.commit()
        logging.getLogger('programacion').info(
            f'[centro-mando auto-clean] cal_set={auto_clean_diag["cal_set_size"]} '
            f'db_rows={auto_clean_diag["db_rows_check"]} '
            f'matched={auto_clean_diag["matched"]} '
            f'canceladas={auto_canceladas_inicial}'
        )

        # ── AUTO-RESET SALAS STALE (Sebastián 1-may-2026: 'que quede
        # automático'). Si una sala está 'ocupada' pero NO hay producción
        # en_proceso/iniciado activa en ella → resetear a 'libre'.
        # No tocamos 'sucia' (requiere marcar limpia explícito) ni 'limpiando'.
        salas_reset = 0
        try:
            stale_rows = _ac.execute("""
                SELECT a.id, a.codigo FROM areas_planta a
                WHERE a.estado = 'ocupada'
                  AND a.activo = 1
                  AND NOT EXISTS (
                    SELECT 1 FROM produccion_programada pp
                    WHERE pp.area_id = a.id
                      AND COALESCE(pp.estado,'programado') IN ('en_proceso','iniciado')
                      AND pp.inicio_real_at IS NOT NULL
                      AND pp.fin_real_at IS NULL
                  )
            """).fetchall()
            for area_id, codigo in stale_rows:
                _ac.execute(
                    "UPDATE areas_planta SET estado='libre' WHERE id=? AND estado='ocupada'",
                    (area_id,)
                )
                salas_reset += 1
            if salas_reset:
                conn.commit()
                logging.getLogger('programacion').info(
                    f'[centro-mando auto-reset salas] {salas_reset} salas reset a libre'
                )
        except Exception as _e:
            logging.getLogger('programacion').warning(f'[centro-mando auto-reset salas] falla: {_e}')
        auto_clean_diag['salas_reset'] = salas_reset
    except Exception as _e:
        logging.getLogger('programacion').warning(f'[centro-mando auto-clean inicial] falla: {_e}')
        try: conn.rollback()
        except Exception as _r:
            logging.getLogger('programacion').debug('rollback no aplicable: %s', _r)
    hoy = fecha_sel.isoformat()

    # Areas con producciones activas (in progress: inicio_real_at NOT NULL,
    # fin_real_at NULL) + ultima producción para 'sucia · era X'
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
            'ultima_produccion': None,
        })
    area_by_id = {a['id']: a for a in areas}
    # Sebastián 1-may-2026: 'área sucia por fabricar tal'
    # Para cada sala, buscar la ÚLTIMA producción que ocupó/completó esa sala
    try:
        for r in conn.execute("""
            SELECT pp.area_id, pp.producto, pp.fin_real_at,
                   COALESCE(pp.estado, 'programado') as est
            FROM produccion_programada pp
            WHERE pp.area_id IS NOT NULL
              AND pp.fin_real_at IS NOT NULL
            ORDER BY pp.fin_real_at DESC
        """):
            aid = r[0]
            if aid in area_by_id and area_by_id[aid]['ultima_produccion'] is None:
                area_by_id[aid]['ultima_produccion'] = {
                    'producto': r[1], 'terminada_at': r[2], 'estado': r[3],
                }
    except Exception:
        pass
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

    # ── PRODUCCIONES DEL DÍA · Calendar-first (Sebastián 1-may-2026) ──
    # Unifica todo en el mapa: cards arriba muestran lo que toca HOY pero
    # aún no se ha iniciado · click ▶ los marca en proceso en su sala IA.
    # Si el día seleccionado está vacío → muestra próximos 7 días para
    # que el jefe siempre vea qué viene (no quedar en blanco un viernes).
    producciones_dia = []
    db_sin_calendar = []
    capacidad_warnings = []
    fechas_horizonte = [fecha_sel + timedelta(days=i) for i in range(7)]
    fechas_horizonte_iso = set(f.isoformat() for f in fechas_horizonte)

    # Helper IA preview operarios (afinidad ponderada · rotación determinística)
    import hashlib
    op_pool = [(r[0], (r[1] or '').strip(), (r[2] or '').strip().lower())
               for r in conn.execute("""
                    SELECT id, nombre || ' ' || COALESCE(apellido,''),
                           COALESCE(rol_predeterminado,'')
                    FROM operarios_planta
                    WHERE COALESCE(activo,1)=1 AND COALESCE(es_jefe_produccion,0)=0
                    ORDER BY id
               """).fetchall()]
    AFINIDAD_CM = {
        'dispensacion': {'dispensacion': 4, 'elaboracion': 1, 'todero': 2},
        'elaboracion':  {'dispensacion': 3, 'elaboracion': 4, 'todero': 2},
        'envasado':     {'envasado': 4, 'todero': 2},
        'acondicionamiento': {'acondicionamiento': 4, 'envasado': 2, 'todero': 2},
    }
    def _hash_cm(s):
        return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)
    def _ops_para(producto_n, fecha_iso):
        if not op_pool: return {}
        roles = ('dispensacion','elaboracion','envasado','acondicionamiento')
        usados = set()
        out = {}
        for rol in roles:
            cands = [(oid, nom, rp) for (oid, nom, rp) in op_pool if oid not in usados]
            if not cands:
                out[rol] = ''
                continue
            afin = AFINIDAD_CM.get(rol, {})
            weighted = [(afin.get(rp, 1) if rp else 1, oid, nom) for (oid, nom, rp) in cands]
            total = sum(w for w, _, _ in weighted)
            target = _hash_cm(f'{producto_n}|{fecha_iso}|{rol}') % max(total, 1)
            cum = 0
            chosen = weighted[0]
            for w, oid, nom in weighted:
                cum += w
                if target < cum:
                    chosen = (w, oid, nom); break
            out[rol] = chosen[2]
            usados.add(chosen[1])
        return out

    try:
        # 1) Filas DB del horizonte SOLO si están INICIADAS o COMPLETADAS.
        # Sebastián 1-may-2026 (estricto Calendar-first): 'se lleva todo lo
        # que hay los lunes sin importar las fechas'. Las filas DB no
        # iniciadas pueden tener fechas erróneas o productos antiguos →
        # ignorarlas completamente. Calendar es la única fuente para 'qué
        # toca'. Solo lo que el operario YA inició (con inicio_real_at) o
        # YA terminó persiste como card.
        rows_db = conn.execute("""
            SELECT pp.id, pp.producto, COALESCE(pp.cantidad_kg,0), pp.lotes,
                   pp.estado, pp.area_id, date(pp.fecha_programada) as f,
                   ap.codigo as area_cod, ap.nombre as area_nom,
                   o1.nombre || ' ' || COALESCE(o1.apellido,'') as op_disp,
                   o2.nombre || ' ' || COALESCE(o2.apellido,'') as op_elab,
                   o3.nombre || ' ' || COALESCE(o3.apellido,'') as op_env,
                   o4.nombre || ' ' || COALESCE(o4.apellido,'') as op_acon,
                   pp.inicio_real_at, pp.fin_real_at
            FROM produccion_programada pp
            LEFT JOIN areas_planta ap ON ap.id = pp.area_id
            LEFT JOIN operarios_planta o1 ON o1.id = pp.operario_dispensacion_id
            LEFT JOIN operarios_planta o2 ON o2.id = pp.operario_elaboracion_id
            LEFT JOIN operarios_planta o3 ON o3.id = pp.operario_envasado_id
            LEFT JOIN operarios_planta o4 ON o4.id = pp.operario_acondicionamiento_id
            WHERE date(pp.fecha_programada) BETWEEN ? AND ?
              AND COALESCE(pp.estado, 'programado') != 'cancelado'
              AND (pp.inicio_real_at IS NOT NULL
                   OR COALESCE(pp.estado, 'programado') IN ('en_proceso','iniciado','completado'))
            ORDER BY pp.fecha_programada, pp.id
        """, (fechas_horizonte[0].isoformat(), fechas_horizonte[-1].isoformat())).fetchall()
        productos_db_por_fecha = set()  # (fecha, producto_upper)
        for r in rows_db:
            (pid, prod_n, kg, lotes, estado, area_id, f_iso,
             area_cod, area_nom,
             op_disp, op_elab, op_env, op_acon, inicio, fin) = r
            productos_db_por_fecha.add((f_iso, (prod_n or '').upper()))
            estado = (estado or 'programado').strip()
            # Acción según estado
            if estado == 'completado':
                accion, accion_label = None, '✅ Completada'
            elif estado in ('en_proceso', 'iniciado'):
                accion, accion_label = 'terminar', '✓ Terminar'
            elif area_id and op_disp:
                accion, accion_label = 'iniciar', '▶ Iniciar'
            else:
                accion, accion_label = 'asignar_ia', '🤖 IA asignar'
            producciones_dia.append({
                'id': pid, 'producto': prod_n, 'kg': kg, 'lotes': lotes or 1,
                'estado': estado, 'fecha': f_iso,
                'area': {'codigo': area_cod or '', 'nombre': area_nom or ''},
                'operarios': {
                    'dispensacion': (op_disp or '').strip(),
                    'elaboracion': (op_elab or '').strip(),
                    'envasado': (op_env or '').strip(),
                    'acondicionamiento': (op_acon or '').strip(),
                },
                'accion': accion, 'accion_label': accion_label,
                'desde_calendar': False,
                'inicio_real_at': inicio, 'fin_real_at': fin,
            })

        # 2) Eventos Calendar del horizonte que no están en DB → preview con IA
        # Sebastián 1-may-2026: 'mala lectura · solo hay 2 producciones, no 7'
        # FIX: filtrar SOLO eventos que parecen producciones (Fabricación,
        # Producción, código SKU). Los Comité/Cita/Etapa/Ritual NO son
        # producciones aunque el matcher pueda encontrarles partial match.
        try:
            from blueprints.auto_plan import (
                _calendar_events_cached, _match_producto_evento, _parsear_kg_evento
            )
            import re as _re
            cal_events = _calendar_events_cached(force_refresh=False) or []
            skus_aliases = {}
            for sku_n, alias_csv in conn.execute("""
                SELECT producto_nombre, COALESCE(alias_calendar,'')
                FROM sku_planeacion_config
                WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
            """).fetchall():
                skus_aliases[sku_n] = alias_csv

            # Patrones que indican PRODUCCIÓN real (no reuniones/comités)
            PROD_PATTERNS = _re.compile(
                r'(fabric|produc|elabor|envas|maquila)',
                _re.IGNORECASE
            )
            # Patrones que indican NO-producción (Comité, Cita, etc.)
            NO_PROD_PATTERNS = _re.compile(
                r'^\s*(comité|comite|cita|reunión|reunion|etapa|ritual|kickoff|'
                r'inventario|rrhh|capacitación|capacitacion|ducha|fumigación|'
                r'fumigacion|comité|alerta|booster\s+tensor|programado\s*:|'
                r'generar.*actas|decisión|decision|lanzami)',
                _re.IGNORECASE
            )

            # Deduplicación por (fecha, producto_final) Calendar
            productos_calendar_por_fecha = set()

            for ev in cal_events:
                try:
                    f_ev = ev.get('fecha', '')[:10]
                    if f_ev not in fechas_horizonte_iso: continue
                except Exception:
                    continue
                titulo_orig = (ev.get('titulo') or '').strip()
                # FILTRO 1: rechazar eventos que claramente no son producciones
                if NO_PROD_PATTERNS.search(titulo_orig):
                    continue
                # FILTRO 2: aceptar solo si tiene match SKU O patrón producción
                tiene_match_sku = False
                producto_match = None
                best = 0
                for prod_n, alias_csv in skus_aliases.items():
                    try:
                        s = _match_producto_evento(prod_n, alias_csv, ev.get('titulo'), ev.get('descripcion',''))
                        if s >= 50 and s > best:
                            best = s; producto_match = prod_n
                    except Exception:
                        continue
                if producto_match:
                    producto_final = producto_match
                    tiene_match_sku = True
                else:
                    # Sin match SKU · solo aceptar si título indica fabricación
                    if not PROD_PATTERNS.search(titulo_orig):
                        continue  # ej. "Comité Mensual" no es producción
                    titulo = titulo_orig
                    titulo = _re.sub(r'\s*[-–]\s*Fab(rica|ric)?[a-z]*\s+\d.*$', '', titulo, flags=_re.IGNORECASE)
                    titulo = _re.sub(r'\s*\(.*?\)\s*$', '', titulo)
                    titulo = _re.sub(r'\s*\d+\s*kg.*$', '', titulo, flags=_re.IGNORECASE)
                    producto_final = titulo.strip().upper() or 'EVENTO SIN TÍTULO'
                # Skip si ya está en DB para esa fecha (no duplicar)
                if (f_ev, producto_final.upper()) in productos_db_por_fecha:
                    continue
                # DEDUP entre eventos Calendar del mismo día con mismo producto
                key_cal = (f_ev, producto_final.upper())
                if key_cal in productos_calendar_por_fecha:
                    continue
                productos_calendar_por_fecha.add(key_cal)
                kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion','')) or 0
                ops = _ops_para(producto_final, f_ev)
                producciones_dia.append({
                    'id': None, 'producto': producto_final,
                    'kg': kg, 'lotes': 1,
                    'estado': 'planeado', 'fecha': f_ev,
                    'area': {'codigo': '', 'nombre': ''},
                    'operarios': ops,
                    'accion': 'iniciar_calendar',
                    'accion_label': '▶ Iniciar (Calendar)',
                    'desde_calendar': True,
                    'tiene_match_sku': tiene_match_sku,
                    'titulo_calendar': titulo_orig[:120],
                    'payload_iniciar': {
                        'producto': producto_final, 'fecha': f_ev,
                        'kg': kg, 'titulo': titulo_orig[:200],
                    },
                })
        except Exception as _e:
            logging.getLogger('programacion').warning(f'[centro-mando] preview Calendar falla: {_e}')

        # Ordenar por fecha + estado (en_proceso primero, completado al final)
        def _orden_key(p):
            est_orden = {'en_proceso': 0, 'iniciado': 0, 'programado': 1,
                         'planeado': 2, 'completado': 3}
            return (p.get('fecha', ''), est_orden.get(p.get('estado', ''), 4))
        producciones_dia.sort(key=_orden_key)

        # ── SCHEDULING SECUENCIAL (Sebastián 1-may-2026) ──
        # 'capacidad simultánea 4 · si hay más, recomendar secuencial'
        # 4 operarios pueden llevar 4 producciones paralelas (cada uno en
        # un rol distinto). Días con > 4 prods necesitan ondas secuenciales.
        CAPACIDAD_PARALELA = 4
        DURACION_DEFAULT_MIN = 180  # 3h por producción (estándar)
        HORA_INICIO = 7  # 7am
        # Agrupar por fecha
        prods_por_fecha = {}
        for p in producciones_dia:
            f = p.get('fecha', '')
            if f: prods_por_fecha.setdefault(f, []).append(p)
        # Calcular wave + horario sugerido por cada producción
        capacidad_warnings = []
        for f, prods in prods_por_fecha.items():
            num = len(prods)
            for idx, p in enumerate(prods):
                # Estimar duración: 3h base, +1h si >50kg, +2h si >100kg
                kg = p.get('kg') or 0
                dur_min = DURACION_DEFAULT_MIN
                if kg > 100: dur_min = 300
                elif kg > 50: dur_min = 240
                wave = (idx // CAPACIDAD_PARALELA) + 1  # 1, 2, 3...
                slot_min = (wave - 1) * DURACION_DEFAULT_MIN
                slot_h = HORA_INICIO + slot_min // 60
                slot_m = slot_min % 60
                fin_h = slot_h + dur_min // 60
                fin_m = (slot_min + dur_min) % 60
                p['wave'] = wave
                p['slot_inicio_sugerido'] = f'{slot_h:02d}:{slot_m:02d}'
                p['slot_fin_sugerido'] = f'{fin_h:02d}:{fin_m:02d}'
                p['duracion_estimada_min'] = dur_min
            if num > CAPACIDAD_PARALELA:
                capacidad_warnings.append({
                    'fecha': f,
                    'num_producciones': num,
                    'capacidad': CAPACIDAD_PARALELA,
                    'ondas_secuenciales': (num + CAPACIDAD_PARALELA - 1) // CAPACIDAD_PARALELA,
                    'extras_secuenciales': num - CAPACIDAD_PARALELA,
                })

        # ── DIAGNÓSTICO: filas DB sin match en Calendar (orphans/stale)
        # Sebastián 1-may-2026: 'siento que deja todo como lunes, no sabe
        # discriminar junta todo' → detectar duplicados de auto-sync antiguo
        productos_calendar_por_fecha = set()  # (fecha, producto_upper)
        try:
            from blueprints.auto_plan import (
                _calendar_events_cached as _cec, _match_producto_evento as _mpe
            )
            cal_events_check = _cec(force_refresh=False) or []
            for ev in cal_events_check:
                try:
                    f_ev = ev.get('fecha', '')[:10]
                    if f_ev not in fechas_horizonte_iso: continue
                except Exception:
                    continue
                producto_match_d = None
                best_d = 0
                for prod_n, alias_csv in skus_aliases.items():
                    try:
                        s = _mpe(prod_n, alias_csv, ev.get('titulo'), ev.get('descripcion',''))
                        if s >= 50 and s > best_d:
                            best_d = s; producto_match_d = prod_n
                    except Exception:
                        continue
                if producto_match_d:
                    productos_calendar_por_fecha.add((f_ev, producto_match_d.upper()))
        except Exception:
            pass
        db_sin_calendar = []
        for p in producciones_dia:
            if p.get('desde_calendar'): continue  # estos vienen de Calendar
            if p.get('estado') in ('en_proceso','iniciado','completado'): continue  # ya iniciada
            key = (p.get('fecha',''), (p.get('producto','') or '').upper())
            if productos_calendar_por_fecha and key not in productos_calendar_por_fecha:
                db_sin_calendar.append({
                    'id': p.get('id'),
                    'producto': p.get('producto'),
                    'fecha': p.get('fecha'),
                    'kg': p.get('kg'),
                    'area_codigo': (p.get('area') or {}).get('codigo',''),
                })
    except Exception as _e:
        logging.getLogger('programacion').warning(f'[centro-mando] producciones_dia falla: {_e}')

    # Auto-limpieza ya se ejecutó al INICIO del endpoint (variables
    # auto_canceladas_inicial / auto_cancel_detalle_inicial) · garantiza
    # que producciones_dia construido arriba ya no incluye huérfanas
    auto_canceladas = auto_canceladas_inicial
    auto_cancel_detalle = auto_cancel_detalle_inicial

    return jsonify({
        'areas': areas,
        'kpis': {
            'producciones_activas_ahora': kpi_row[0] or 0,
            'terminadas_hoy': kpi_row[1] or 0,
            'cycle_time_promedio_min': int(kpi_row[2]) if kpi_row[2] else None,
            'salas_libres': salas_libres,
            'salas_sucias': salas_sucias,
            'salas_ocupadas': salas_ocupadas,
            'producciones_dia_total': len(producciones_dia),
            'producciones_dia_pendientes': sum(1 for p in producciones_dia
                                                  if p['estado'] in ('planeado','programado')),
            'auto_canceladas': auto_canceladas,
        },
        'producciones_dia': producciones_dia,
        'producciones_diag': {
            'db_sin_calendar': db_sin_calendar,
            'db_sin_calendar_count': len(db_sin_calendar),
            'auto_canceladas_esta_carga': auto_canceladas,
            'auto_cancel_detalle': auto_cancel_detalle[:5],
            'auto_clean_diag': auto_clean_diag,
            'capacidad_warnings': capacidad_warnings,
        },
        'eventos_recientes': eventos,
        'fecha': hoy,
    })


@bp.route('/api/planta/limpiar-db-sin-calendar', methods=['POST'])
def limpiar_db_sin_calendar():
    """Cancela filas produccion_programada que no tienen match en Calendar
    (en horizonte 7 días). Sebastián 1-may-2026: 'siento que deja todo como
    lunes · no sabe discriminar · junta todo'.

    Auto-sync antiguo dejó duplicados con fechas erróneas. Este endpoint
    los marca como 'cancelado' (NO delete · permite revertir si necesario).
    Solo afecta filas no iniciadas (estado in ('programado','planeado','')).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    body = request.json or {}
    fecha_param = (body.get('fecha') or '').strip()[:10]
    try:
        fecha_sel = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else date.today()
    except Exception:
        fecha_sel = date.today()
    fechas_horizonte = [fecha_sel + timedelta(days=i) for i in range(7)]
    fechas_iso = set(f.isoformat() for f in fechas_horizonte)

    conn = get_db(); c = conn.cursor()
    # 1) Construir set Calendar (fecha, producto_upper)
    productos_cal = set()
    try:
        from blueprints.auto_plan import _calendar_events_cached, _match_producto_evento
        cal_events = _calendar_events_cached(force_refresh=True) or []
        skus_aliases = {}
        for sku_n, alias_csv in c.execute("""
            SELECT producto_nombre, COALESCE(alias_calendar,'')
            FROM sku_planeacion_config
            WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
        """).fetchall():
            skus_aliases[sku_n] = alias_csv
        for ev in cal_events:
            try:
                f_ev = ev.get('fecha', '')[:10]
                if f_ev not in fechas_iso: continue
            except Exception:
                continue
            producto_match = None
            best = 0
            for prod_n, alias_csv in skus_aliases.items():
                try:
                    s = _match_producto_evento(prod_n, alias_csv, ev.get('titulo'), ev.get('descripcion',''))
                    if s >= 50 and s > best:
                        best = s; producto_match = prod_n
                except Exception:
                    continue
            if producto_match:
                productos_cal.add((f_ev, producto_match.upper()))
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Calendar fetch falla: {e}'}), 500

    # 2) DB rows en horizonte sin match Calendar (no iniciadas)
    rows = c.execute("""
        SELECT id, producto, date(fecha_programada) as f, COALESCE(estado,'')
        FROM produccion_programada
        WHERE date(fecha_programada) BETWEEN ? AND ?
          AND COALESCE(estado, 'programado') IN ('', 'programado', 'planeado')
    """, (fechas_horizonte[0].isoformat(), fechas_horizonte[-1].isoformat())).fetchall()

    a_cancelar = []
    for pid, prod, f, _est in rows:
        key = (f, (prod or '').upper())
        if productos_cal and key not in productos_cal:
            a_cancelar.append((pid, prod, f))

    if not a_cancelar:
        return jsonify({
            'ok': True,
            'mensaje': '✅ Sin filas DB huérfanas · todo está sincronizado con Calendar',
            'cancelados': 0,
            'productos_calendar_total': len(productos_cal),
        })

    # 3) Marcar como cancelado (no delete · easy revert)
    canceladas = 0
    for pid, prod, f in a_cancelar:
        try:
            c.execute("""
                UPDATE produccion_programada
                  SET estado='cancelado',
                      observaciones = COALESCE(observaciones,'') ||
                        ' [cancelado por limpieza · sin match Calendar · usuario=' || ? || ']'
                WHERE id=?
            """, (user, pid))
            canceladas += 1
        except Exception:
            continue
    conn.commit()
    return jsonify({
        'ok': True,
        'mensaje': f'🗑 {canceladas} filas DB marcadas cancelado · sin match en Calendar',
        'cancelados': canceladas,
        'detalle': [{'producto': p, 'fecha': f} for _, p, f in a_cancelar[:20]],
        'productos_calendar_total': len(productos_cal),
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


def _calcular_mp_consumo_produccion(c, evento_id):
    """Calcula MPs a consumir por una producción programada.

    Lee formula_items y aplica:
      - Preferimos cantidad_g_por_lote * lotes (formula con cantidades fijas)
      - Fallback: porcentaje * cantidad_kg * 1000 (formula con %)

    Returns: (mps_a_consumir, meta) donde:
      mps_a_consumir = [{codigo_mp, nombre, cantidad_g}, ...]
      meta = {producto, fecha, lotes, cantidad_kg_total}
    Returns ({}, None) si la producción no existe.
    """
    row = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
               COALESCE(pp.cantidad_kg, 0)         as cantidad_kg_explicita,
               COALESCE(fh.lote_size_kg, 0)        as lote_kg_formula
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh
               ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        WHERE pp.id=?
    """, (evento_id,)).fetchone()
    if not row:
        return [], None
    pid, producto, fecha, lotes, cant_kg_exp, lote_kg = row
    lotes = int(lotes or 1)
    cant_kg_total = float(cant_kg_exp or 0) or (lotes * float(lote_kg or 0))

    mps = []
    rows = c.execute("""
        SELECT material_id, material_nombre,
               COALESCE(porcentaje, 0)                as pct,
               COALESCE(cantidad_g_por_lote, 0)       as g_por_lote
        FROM formula_items
        WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
    """, (producto,)).fetchall()
    for cod, nom, pct, g_lote in rows:
        g_total = float(g_lote or 0) * lotes
        if g_total <= 0 and cant_kg_total > 0:
            g_total = (float(pct or 0) / 100.0) * cant_kg_total * 1000.0
        if g_total > 0:
            mps.append({
                'codigo_mp': cod or '',
                'nombre': nom or '',
                'cantidad_g': round(g_total, 2),
            })
    return mps, {
        'producto': producto, 'fecha': fecha, 'lotes': lotes,
        'cantidad_kg_total': cant_kg_total, 'pid': pid,
    }


class _DescuentoError(Exception):
    """Descuento MP fallido. .codigo: str. .payload: dict."""
    def __init__(self, mensaje, codigo='ERROR', payload=None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.payload = payload or {}


# Sebastian 5-may-2026 (audit zero-error dashboard): lista canonica de
# estados de lote que NO se pueden consumir en produccion. Usar UPPER()
# en comparaciones porque la DB tiene mezcla de mayusculas/capitalizadas
# (calidad.py escribe 'Cuarentena' Capitalizado, inventario.py escribe
# 'CUARENTENA' UPPERCASE). UPPER normaliza ambas variantes.
_ESTADOS_LOTE_NO_PRODUCIBLES = (
    'CUARENTENA', 'CUARENTENA_EXTENDIDA',
    'VENCIDO',
    'RECHAZADO',
    'AGOTADO',
    'BLOQUEADO',
)


def _validar_stock_para_produccion(c, mps_a_consumir):
    """Verifica que haya stock suficiente para descontar TODAS las MPs.

    Devuelve lista de faltantes. Lista vacía = OK para descontar.
    Cada faltante: {codigo_mp, nombre, requerido_g, disponible_g, falta_g}.
    Excluye lotes en CUARENTENA / CUARENTENA_EXTENDIDA / VENCIDO /
    RECHAZADO / AGOTADO / BLOQUEADO (case-insensitive).
    """
    placeholders = ','.join(['?'] * len(_ESTADOS_LOTE_NO_PRODUCIBLES))
    sql = f"""
        SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0)
        FROM movimientos
        WHERE material_id=?
          AND UPPER(COALESCE(estado_lote,'')) NOT IN ({placeholders})
    """
    faltantes = []
    for mp in mps_a_consumir:
        cod = mp['codigo_mp']
        if not cod:
            continue
        params = (cod,) + _ESTADOS_LOTE_NO_PRODUCIBLES
        r = c.execute(sql, params).fetchone()
        disp = float(r[0] or 0)
        if disp + 0.01 < float(mp['cantidad_g']):
            faltantes.append({
                'codigo_mp': cod,
                'nombre': mp['nombre'],
                'requerido_g': mp['cantidad_g'],
                'disponible_g': round(disp, 2),
                'falta_g': round(mp['cantidad_g'] - disp, 2),
            })
    return faltantes


def _descontar_mp_produccion(c, evento_id, user, forzar=False):
    """Helper compartido: claim atomico + descuenta MPs FEFO de una producción.

    Sebastian 5-may-2026 (Luis Enrique): "cuando carguen produccion de materia
    prima de una descuente". Antes el descuento estaba en /completar (paso
    final) pero los operarios no lo ejecutaban — productions quedaban en
    envasado y MPs nunca se descontaban del inventario. Ahora el descuento
    ocurre al INICIAR (cuando MP fisicamente sale de bodega).

    Args:
      c: cursor SQLite (caller controla la tx)
      evento_id: id de produccion_programada
      user: username del actor (audit)
      forzar: si True, ignora claim atomico (solo admin)

    Atomico: usa UPDATE-WHERE inventario_descontado_at='' para evitar
    descuento doble en race conditions.

    Levanta _DescuentoError si:
      - YA_DESCONTADO: producción ya descontada antes
      - SIN_STOCK: alguna MP no tiene stock suficiente
      - SIN_FORMULA: producto sin formula registrada (formula_items vacio)
      - PRODUCCION_NO_EXISTE

    Returns dict {ok, mps_descontadas:[...], inventario_descontado_at, total_g}.
    """
    from datetime import datetime as _dt
    fecha_iso = _dt.now().isoformat(timespec='seconds')

    mps_a_consumir, meta = _calcular_mp_consumo_produccion(c, evento_id)
    if meta is None:
        raise _DescuentoError('Producción no encontrada', 'PRODUCCION_NO_EXISTE')
    if not mps_a_consumir:
        # Formula vacía o sin %/g_por_lote: NO bloqueante · iniciar igual
        # con warning. NO marcamos inventario_descontado_at para permitir
        # re-intento si Tecnica completa la formula despues.
        log.warning(
            'iniciar_produccion sin formula valida: producto=%s evento_id=%s · '
            'inicio se permite pero NO se descuenta inventario',
            meta['producto'], evento_id,
        )
        return {
            'ok': True,
            'mps_descontadas': [],
            'inventario_descontado_at': None,
            'total_g': 0,
            'producto': meta['producto'],
            'sin_formula': True,
            'warning': (f"Producto '{meta['producto']}' sin formula valida "
                         f"(porcentaje y cantidad_g_por_lote ambos en 0/null). "
                         f"Inicio registrado pero NO se descontó inventario · "
                         f"revisa formula en /tecnica y usa /completar para "
                         f"descontar despues."),
        }

    # Pre-check stock ANTES del claim para abortar limpio sin tocar la fila.
    faltantes = _validar_stock_para_produccion(c, mps_a_consumir)
    if faltantes:
        raise _DescuentoError(
            f'Stock insuficiente para producir {meta["producto"]}: '
            f'{len(faltantes)} MP(s) sin stock',
            'SIN_STOCK',
            {'faltantes': faltantes, 'producto': meta['producto']},
        )

    # ATOMIC CLAIM
    if forzar:
        cur = c.execute(
            "UPDATE produccion_programada SET inventario_descontado_at=? WHERE id=?",
            (fecha_iso, evento_id),
        )
    else:
        cur = c.execute(
            "UPDATE produccion_programada SET inventario_descontado_at=? "
            "WHERE id=? AND COALESCE(inventario_descontado_at,'')=''",
            (fecha_iso, evento_id),
        )
    if cur.rowcount == 0:
        actual = c.execute(
            "SELECT inventario_descontado_at FROM produccion_programada WHERE id=?",
            (evento_id,),
        ).fetchone()
        actual_at = (actual[0] if actual else '') or ''
        raise _DescuentoError(
            f'Inventario ya fue descontado el {actual_at}',
            'YA_DESCONTADO',
            {'inventario_descontado_at': actual_at},
        )

    # FEFO real por lote
    obs_base = (f"Producción INICIADA: {meta['producto']} — {meta['fecha']} — "
                f"{meta['lotes']} lote(s) × {meta['cantidad_kg_total']:.0f}kg")
    descontados = []
    for mp in mps_a_consumir:
        distrib = _distribuir_fefo(c, mp['codigo_mp'], mp['cantidad_g'])
        mp['distribucion_fefo'] = []
        for d in distrib:
            lote_fragment = d['lote'] or '(sin lote — stock legacy)'
            obs_mp = (obs_base + f" | FEFO lote: {lote_fragment}" +
                       (f" (vence {d['fecha_vencimiento']})"
                        if d['fecha_vencimiento'] else ""))
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
        descontados.append(mp)

    return {
        'ok': True,
        'mps_descontadas': descontados,
        'inventario_descontado_at': fecha_iso,
        'total_g': round(sum(m['cantidad_g'] for m in descontados), 2),
        'producto': meta['producto'],
    }


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
    # Sebastian 5-may-2026 (audit zero-error): ANTES solo excluia
    # ('Vencido','Bloqueado','Rechazado') case-sensitive — NO excluia
    # CUARENTENA y NO matcheaba 'VENCIDO'/'CUARENTENA' en mayusculas.
    # Riesgo: FEFO podia consumir lotes en cuarentena o vencidos.
    # Fix: UPPER() + lista canonica _ESTADOS_LOTE_NO_PRODUCIBLES.
    placeholders = ','.join(['?'] * len(_ESTADOS_LOTE_NO_PRODUCIBLES))
    sql = f"""
        SELECT lote, fecha_vencimiento,
               SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_lote
        FROM movimientos
        WHERE material_id = ?
          AND COALESCE(lote, '') != ''
          AND UPPER(COALESCE(estado_lote, '')) NOT IN ({placeholders})
        GROUP BY lote, fecha_vencimiento
        HAVING stock_lote > 0
        ORDER BY COALESCE(fecha_vencimiento, '9999-12-31') ASC,
                 lote ASC
    """
    params = (codigo_mp,) + _ESTADOS_LOTE_NO_PRODUCIBLES
    rows = c.execute(sql, params).fetchall()

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


# ── Helper: descuento MEE al terminar envasado ────────────────────────────
# Sebastian (1-may-2026): "en produccion dicen envasado, para que coloquen
# cuanto fue y de alli mismo descuenta automaticamente envases y demas".
# Hoy el descuento ocurre al COMPLETAR producción usando cantidad planificada.
# Esta función mueve el descuento al TERMINAR envasado, usando la cantidad
# REAL envasada (proporcional al plan).
#
# Filosofía:
#   - Se descuentan SOLO los componentes que se usan físicamente al envasar:
#     envase_primario, envase_secundario, tapa, caja_exterior, etiquetas.
#   - Serigrafía/tampografía se descuentan en el evento de decoración (D-20),
#     no aquí (su movimiento se hace cuando el operario saca de bodega).
#   - Si unidades_envasadas < unidades_planeadas → descuenta proporcional
#     (la merma queda implícita: stock MEE = stock_actual - real_consumido).
#   - Marca consumido_at + consumido_contexto='envasado' en checklist para
#     que prog_completar_evento NO vuelva a descontar el mismo ítem.
TIPOS_MEE_AL_ENVASAR = (
    'envase_primario', 'envase_secundario', 'envase',
    'tapa',
    'caja_exterior', 'caja',
    'etiqueta_frontal', 'etiqueta_posterior', 'etiqueta_lateral', 'etiqueta',
    'etiqueta_adhesiva',
)


def _descontar_mee_envasado(c, produccion_id, lote, unidades_envasadas,
                             unidades_planeadas, user):
    """Descuenta MEE de envase/tapa/etiqueta al terminar envasado.

    Args:
      c: cursor SQLite
      produccion_id: int — produccion_programada.id (lote padre)
      lote: str — lote del envasado (para batch_ref en movimientos)
      unidades_envasadas: int — cantidad REAL envasada (registrada por operario)
      unidades_planeadas: int — cantidad planeada de envasado (de produccion_envasado)
      user: str — operador que termina el envasado

    Returns: lista de dicts con descontados, o [] si no aplica.
    """
    if not produccion_id or not unidades_envasadas or unidades_envasadas <= 0:
        return []

    # Ratio para cantidades 1:1 con unidades. Si planeadas no está, asume 100%.
    if unidades_planeadas and unidades_planeadas > 0:
        ratio = float(unidades_envasadas) / float(unidades_planeadas)
    else:
        ratio = 1.0

    # Construir whitelist de tipos en SQL
    placeholders = ','.join(['?'] * len(TIPOS_MEE_AL_ENVASAR))
    sql = f"""
        SELECT id, mee_codigo_asignado, descripcion, cantidad_unidades, item_tipo
        FROM produccion_checklist
        WHERE produccion_id = ?
          AND COALESCE(mee_codigo_asignado, '') != ''
          AND COALESCE(cantidad_unidades, 0) > 0
          AND COALESCE(consumido_at, '') = ''
          AND LOWER(COALESCE(item_tipo, '')) IN ({placeholders})
    """
    params = (produccion_id,) + tuple(t.lower() for t in TIPOS_MEE_AL_ENVASAR)
    try:
        items = c.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []  # tabla no existe → no descontar

    if not items:
        return []

    fecha_iso = datetime.now().isoformat(timespec='seconds')
    obs_base = (f"Envasado terminado: produccion #{produccion_id} "
                f"lote {lote or 'sin-lote'} — {unidades_envasadas}/"
                f"{unidades_planeadas or '?'} ud (ratio {ratio:.2f})")

    # Audit zero-error 2-may-2026: usar aplicar_movimiento_mee · INSERT
    # movimiento + UPDATE stock_actual atómicos · garantiza drift=0 +
    # clamp si stock_nuevo < 0 (no permite stock fantasma negativo).
    from inventario_helpers import aplicar_movimiento_mee
    descontados = []
    for item_id, mee_cod, desc, cant_plan, tipo_item in items:
        cant_plan_f = float(cant_plan or 0)
        cant_real = round(cant_plan_f * ratio, 0)
        if cant_real <= 0:
            continue
        try:
            aplicar_movimiento_mee(
                c.connection, mee_cod, 'Salida', cant_real,
                observaciones=obs_base, responsable=user,
                lote_ref=str(produccion_id), batch_ref=lote or '',
            )
            c.execute("""
                UPDATE produccion_checklist
                   SET consumido_at = ?,
                       consumido_por = ?,
                       cantidad_consumida_real = ?,
                       consumido_contexto = 'envasado',
                       actualizado_at = datetime('now')
                 WHERE id = ?
            """, (fecha_iso, user, cant_real, item_id))
            descontados.append({
                'codigo': mee_cod,
                'descripcion': desc or '',
                'tipo_item': tipo_item or '',
                'cantidad_planeada': cant_plan_f,
                'cantidad_real': cant_real,
                'merma': max(0, cant_plan_f - cant_real),
            })
        except sqlite3.OperationalError as e:
            # Si maestro_mee o movimientos_mee no existe, dejamos pasar
            log.warning(f'Descuento MEE skip {mee_cod}: {e}')
            continue

    return descontados


@bp.route('/api/programacion/programar/<int:evento_id>/completar', methods=['POST'])
def prog_completar_evento(evento_id):
    """Marca una produccion como completada Y descuenta inventario.

    Sebastian (29-abr-2026): "que todo descuente que el inventario este
    perfecto". Antes solo cambiaba estado — ahora:
      1. Calcula consumo de MPs desde formula_items: cantidad_g_por_lote * lotes
         (o si no hay cantidad_g_por_lote, usa porcentaje * cantidad_kg * 1000).
      2. Calcula consumo de MEEs desde produccion_checklist (items con
         mee_codigo_asignado en estado verificado_ok / recibido / listo).
         · Excluye items con consumido_at != NULL (ya descontados al envasar).
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

    # Sebastian 5-may-2026 (Luis Enrique): si ya descontó al INICIAR (flujo
    # nuevo · auto descuenta MP en /iniciar), permitimos que /completar siga
    # corriendo solo para MEE + estado=completado · NO devolvemos 409.
    # Solo bloqueamos si forzar=False AND aún hay que re-descontar MP — eso
    # solo ocurre si admin pide forzar (chequeado abajo). El skip de MP se
    # hace en el bloque ATOMIC CLAIM (rowcount=0 ya no aborta · solo skip).
    mp_ya_descontado = bool(descontado_at) and not forzar

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

    # ── 2. Calcular MEEs a consumir desde checklist (solo recibidos/verificados
    #       y NO consumidos previamente al envasar) ──
    # Sebastian (1-may-2026): los items envase/tapa/etiqueta se descuentan al
    # terminar envasado con cantidad REAL (helper _descontar_mee_envasado).
    # Aquí solo descontamos lo que NO se consumió aún (serigrafía/tampografía/
    # caja_master si vienen al final).
    mees_a_consumir = []
    mee_item_ids = []  # ids del checklist para marcar consumido_at después
    try:
        crows = c.execute("""
            SELECT id, mee_codigo_asignado, descripcion, cantidad_unidades, item_tipo
            FROM produccion_checklist
            WHERE produccion_id = ?
              AND COALESCE(mee_codigo_asignado,'') != ''
              AND COALESCE(cantidad_unidades, 0) > 0
              AND COALESCE(consumido_at, '') = ''
              AND estado IN ('verificado_ok','recibido','listo')
        """, (pid,)).fetchall()
        for item_id, mee_cod, desc, cant_ud, tipo_item in crows:
            mees_a_consumir.append({
                'item_id': item_id,
                'codigo': mee_cod, 'descripcion': desc or '',
                'cantidad_unidades': int(cant_ud or 0),
                'tipo_item': tipo_item or '',
            })
            mee_item_ids.append(item_id)
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
        # ATOMIC CLAIM (audit zero-error 2-may-2026 · CERO SESGO).
        # Sebastian 5-may-2026: skip si ya descontó al iniciar (no devolvemos
        # 409 · solo procesamos MEE + cierre).
        if mp_ya_descontado:
            claim_rowcount = 0  # ya descontado, skip MP loop
        elif forzar:
            claim_cur = c.execute("""
                UPDATE produccion_programada
                   SET inventario_descontado_at = ?
                 WHERE id = ?
            """, (fecha_iso, evento_id))
            claim_rowcount = claim_cur.rowcount
        else:
            claim_cur = c.execute("""
                UPDATE produccion_programada
                   SET inventario_descontado_at = ?
                 WHERE id = ?
                   AND COALESCE(inventario_descontado_at, '') = ''
            """, (fecha_iso, evento_id))
            claim_rowcount = claim_cur.rowcount
        if claim_rowcount == 0 and not mp_ya_descontado:
            # Race: otro request descontó al mismo tiempo · liberar tx + 409
            try: conn.rollback()
            except Exception: pass
            actual = c.execute(
                "SELECT inventario_descontado_at FROM produccion_programada WHERE id=?",
                (evento_id,)).fetchone()
            actual_at = actual[0] if actual else descontado_at
            return jsonify({
                'error': f'Inventario ya fue descontado el {actual_at}',
                'codigo': 'YA_DESCONTADO_RACE',
                'hint': 'Otro proceso descontó al mismo tiempo · idempotencia respetada',
                'inventario_descontado_at': actual_at,
            }), 409
        # MPs → FEFO REAL: distribuir el consumo entre lotes según fecha
        # de vencimiento (más cercano primero). Cada lote genera su propio
        # movimiento de Salida con cantidad específica. Si la suma de stock
        # por lote no alcanza, el remainder se registra sin lote (legacy).
        # Sebastian 5-may-2026: skip si ya descontó al iniciar.
        if not mp_ya_descontado:
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
        # MEEs → aplicar_movimiento_mee · drift=0 garantizado (audit zero-error)
        # lote_ref=produccion_id permite reversión limpia sin LIKE en obs.
        from inventario_helpers import aplicar_movimiento_mee as _aplicar_mee_inner
        for me in mees_a_consumir:
            try:
                _aplicar_mee_inner(
                    c.connection, me['codigo'], 'Salida', me['cantidad_unidades'],
                    observaciones=obs_base, responsable=user,
                    lote_ref=str(pid), batch_ref=str(fecha or ''),
                )
                # Marcar consumido en checklist (contexto='completar')
                if me.get('item_id'):
                    c.execute("""
                        UPDATE produccion_checklist
                           SET consumido_at = ?,
                               consumido_por = ?,
                               cantidad_consumida_real = ?,
                               consumido_contexto = 'completar',
                               actualizado_at = datetime('now')
                         WHERE id = ?
                    """, (fecha_iso, user, me['cantidad_unidades'], me['item_id']))
                descontados_mees.append(me)
            except sqlite3.OperationalError:
                # Si tabla mee no existe, seguimos
                continue
        # Actualizar produccion_programada · estado + observaciones
        # (inventario_descontado_at YA fue seteado por el ATOMIC CLAIM al inicio)
        c.execute("""
            UPDATE produccion_programada
               SET estado='completado',
                   observaciones = COALESCE(observaciones,'') ||
                                   ' | INVENTARIO DESCONTADO ' || ? || ' por ' || ?
             WHERE id=?
        """, (fecha_iso, user, pid))
        # Audit log INVIMA · dispensación es operación regulada GMP/BPM
        # (Resolución 2214/2021). Trazabilidad obligatoria: quién dispensó qué
        # producción y cuándo se descontó inventario.
        try:
            audit_log(c, usuario=user, accion='COMPLETAR_PRODUCCION',
                      tabla='produccion_programada', registro_id=pid,
                      despues={'producto': producto, 'lotes': lotes,
                                'fecha_programada': fecha,
                                'inventario_descontado_at': fecha_iso})
        except Exception as e:
            log.warning('audit_log COMPLETAR_PRODUCCION fallo: %s', e)

        # Sebastián 1-may-2026: "queden limpias el mismo día". Si la
        # producción tenía área asignada → marcar sucia + crear limpieza HOY
        # con operario rotando.
        limpieza_id = None
        try:
            row = c.execute("""
                SELECT pp.area_id, ap.codigo, pp.lotes
                FROM produccion_programada pp
                  LEFT JOIN areas_planta ap ON ap.id = pp.area_id
                WHERE pp.id=?
            """, (pid,)).fetchone()
            if row and row[0]:
                area_id_, area_codigo, lotes_n = row
                # Marcar sucia
                c.execute(
                    "UPDATE areas_planta SET estado='sucia' WHERE id=? AND estado='ocupada'",
                    (area_id_,)
                )
                # Crear limpieza mismo día
                limpieza_id = _crear_limpieza_post_produccion(
                    c, area_id_, area_codigo, fecha,
                    producto, f'{lotes_n}lt' if lotes_n else '', user
                )
        except Exception as _e:
            log.warning(f'[completar] limpieza post-prod falla: {_e}')

        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception as _r:
            logging.getLogger('programacion').debug('rollback no aplicable: %s', _r)
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
        'limpieza_auto_id': limpieza_id,
        'mensaje': (f"{producto} marcada completada. Descontados {len(descontados_mps)} MPs y "
                    f"{len(descontados_mees)} MEEs. " +
                    (f"🧹 Limpieza programada hoy (#{limpieza_id})" if limpieza_id else ""))
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

        # Reversión de MEEs: doble fuente
        #   1) movimientos por lote_ref = produccion_id (descuentos al envasar
        #      o al completar usan ese lote_ref desde 1-may-2026).
        #   2) Fallback legacy: observaciones LIKE 'Producción COMPLETADA%'
        # Sebastian (1-may-2026): el descuento puede ocurrir en envasado o en
        # completar, ambos quedan vinculados a produccion_id por lote_ref.
        try:
            # Primero por lote_ref (preciso, sin LIKE)
            rows_mee = c.execute("""
                SELECT id, mee_codigo, cantidad
                FROM movimientos_mee
                WHERE LOWER(tipo)='salida'
                  AND COALESCE(lote_ref,'') = ?
                  AND COALESCE(anulado,0) = 0
            """, (str(evento_id),)).fetchall()
            ids_revertidos = set(r[0] for r in rows_mee)
            # Luego fallback legacy (sin lote_ref) por observación
            rows_legacy = c.execute("""
                SELECT id, mee_codigo, cantidad
                FROM movimientos_mee
                WHERE LOWER(tipo)='salida'
                  AND COALESCE(lote_ref,'') = ''
                  AND observaciones LIKE ?
                  AND COALESCE(anulado,0) = 0
            """, (f"{obs_filtro}%",)).fetchall()
            for r in rows_legacy:
                if r[0] not in ids_revertidos:
                    rows_mee = list(rows_mee) + [r]
            # Audit zero-error 2-may-2026: usar aplicar_movimiento_mee para
            # la reversión · garantiza drift=0 (Entrada compensatoria atómica).
            #
            # IMPORTANTE: NO marcar el movimiento original como anulado.
            # Hacer AMBAS cosas (entrada compensatoria + anular original) era
            # un bug preexistente que provocaba drift = -cant en SUM(movs)
            # porque el calc excluye anulados pero stock_actual sí los suma.
            #
            # La entrada compensatoria YA es la "anulación lógica" · ambos
            # movimientos quedan en historial para auditoría completa
            # (el operador ve "Salida X · Reversión X" como pares en logs).
            from inventario_helpers import aplicar_movimiento_mee as _aplicar_mee_rev
            for mid, mee_cod, cant in rows_mee:
                _aplicar_mee_rev(
                    c.connection, mee_cod, 'Entrada', cant,
                    observaciones=f"REVERSIÓN producción completada — original mov_mee #{mid}",
                    responsable=user, lote_ref=str(evento_id),
                )
                revertidos_mees.append({'codigo': mee_cod, 'cantidad_unidades': cant})
            # Resetear flags consumido_at en el checklist para esta producción
            c.execute("""
                UPDATE produccion_checklist
                   SET consumido_at = NULL,
                       consumido_por = '',
                       cantidad_consumida_real = 0,
                       consumido_contexto = ''
                 WHERE produccion_id = ?
            """, (evento_id,))
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
        except Exception as _r:
            logging.getLogger('programacion').debug('rollback no aplicable: %s', _r)
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
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
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
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
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


# ─── Producciones con faltantes (vista simple para Luis Enrique) ─────────
# Sebastian 5-may-2026: jefe de producción quiere UN solo flujo.
#   1. Selector horizonte (semana, 15d, 1m, 2m, 3m, 6m, 1 año)
#   2. Tabla de producciones programadas en ese horizonte
#   3. Por cada producción: ver MP+MEE faltantes
#   4. Botón "Solicitar TODO faltante" → bulk OC por proveedor
#
# Reutiliza:
#   - produccion_programada (eventos programados)
#   - formula_items (MP por producto)
#   - sku_mee_config (MEE por producto)
#   - maestro_mps + mp_lead_time_config (proveedor sugerido MP)
#   - maestro_mee + mee_lead_time_config (proveedor sugerido MEE)
#
# Excluye producciones con inventario_descontado_at != NULL (ya consumieron).

@bp.route('/api/programacion/producciones-faltantes', methods=['GET'])
def producciones_faltantes():
    """Producciones programadas en horizonte + agregado de MP/MEE faltantes.

    Query params:
      dias: int 7-365 (default 60)

    Returns:
      {
        horizonte_dias: int,
        producciones: [
          {id, producto, fecha, lotes, cantidad_kg,
           mps_necesarias: [{codigo_mp, nombre, necesario_g}],
           mees_necesarios: [{codigo, descripcion, tipo, necesario_unidades}]
          }
        ],
        faltantes_mps: [
          {codigo_mp, nombre, necesario_total_g, stock_actual_g, faltante_g,
           proveedor_sugerido}
        ],
        faltantes_mees: [
          {codigo, descripcion, tipo, necesario_total_u, stock_actual_u,
           faltante_u, proveedor_sugerido}
        ],
        resumen: {n_producciones, n_mps_faltantes, n_mees_faltantes,
                  n_proveedores_unicos}
      }
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = max(7, min(int(request.args.get('dias', 60)), 365))
    except (ValueError, TypeError):
        dias = 60

    conn = get_db(); c = conn.cursor()
    from datetime import date, timedelta as _td
    hoy = date.today()
    cutoff = (hoy + _td(days=dias)).isoformat()

    # 1. Cargar producciones programadas pendientes (no descontadas) en horizonte
    # Sebastian 5-may-2026: incluir area asignada + arrancar desde lunes de
    # la semana actual (para que UI muestre Lun-Vie completos aunque ya haya
    # pasado el lunes). El cliente puede filtrar lo que sigue siendo
    # relevante en frontend.
    # Calcular lunes de la semana actual
    dow = hoy.weekday()  # 0=Lun, 6=Dom
    lunes_actual = (hoy - _td(days=dow)).isoformat()
    try:
        c.execute("""
            SELECT pp.id, pp.producto, pp.fecha_programada,
                   COALESCE(pp.lotes, 1), COALESCE(pp.cantidad_kg, 0),
                   COALESCE(fh.lote_size_kg, 0) as lote_size_kg,
                   COALESCE(pp.area_id, 0) as area_id,
                   COALESCE(ap.codigo, '') as area_codigo,
                   COALESCE(ap.nombre, '') as area_nombre,
                   COALESCE(LOWER(pp.estado), 'pendiente') as estado_norm,
                   COALESCE(pp.inicio_real_at, '') as inicio_real_at,
                   COALESCE(pp.fin_real_at, '') as fin_real_at
            FROM produccion_programada pp
            LEFT JOIN formula_headers fh
                   ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
            LEFT JOIN areas_planta ap ON ap.id = pp.area_id
            WHERE COALESCE(pp.inventario_descontado_at, '') = ''
              AND LOWER(COALESCE(pp.estado, '')) NOT IN ('cancelado', 'completado')
              AND pp.fecha_programada >= ?
              AND pp.fecha_programada <= ?
            ORDER BY pp.fecha_programada ASC
        """, (lunes_actual, cutoff))
        prod_rows = c.fetchall()
    except sqlite3.OperationalError:
        # Fallback si areas_planta no existe (esquema legacy)
        c.execute("""
            SELECT pp.id, pp.producto, pp.fecha_programada,
                   COALESCE(pp.lotes, 1), COALESCE(pp.cantidad_kg, 0),
                   COALESCE(fh.lote_size_kg, 0) as lote_size_kg,
                   0, '', '',
                   COALESCE(LOWER(pp.estado), 'pendiente'),
                   COALESCE(pp.inicio_real_at, ''),
                   COALESCE(pp.fin_real_at, '')
            FROM produccion_programada pp
            LEFT JOIN formula_headers fh
                   ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
            WHERE COALESCE(pp.inventario_descontado_at, '') = ''
              AND LOWER(COALESCE(pp.estado, '')) NOT IN ('cancelado', 'completado')
              AND pp.fecha_programada >= ?
              AND pp.fecha_programada <= ?
            ORDER BY pp.fecha_programada ASC
        """, (lunes_actual, cutoff))
        prod_rows = c.fetchall()

    # 2. Cargar formulas (codigo_mp -> [nombre, cantidad_g_por_lote, porcentaje])
    formulas = {}
    for r in c.execute("""
        SELECT producto_nombre, material_id, material_nombre,
               COALESCE(porcentaje, 0), COALESCE(cantidad_g_por_lote, 0)
        FROM formula_items
    """).fetchall():
        prod = (r[0] or '').strip().upper()
        formulas.setdefault(prod, []).append({
            'codigo_mp': r[1] or '',
            'nombre': r[2] or '',
            'porcentaje': float(r[3] or 0),
            'g_por_lote': float(r[4] or 0),
        })

    # 3. Cargar sku_mee_config (producto/sku -> [mee_codigo, cantidad_por_unidad, tipo])
    mee_por_producto = {}
    try:
        for r in c.execute("""
            SELECT s.sku_codigo, s.mee_codigo,
                   COALESCE(s.cantidad_por_unidad, 1),
                   COALESCE(s.componente_tipo, 'envase'),
                   COALESCE(m.descripcion, '') as descripcion
            FROM sku_mee_config s
            LEFT JOIN maestro_mee m ON m.codigo = s.mee_codigo
            WHERE COALESCE(s.aplica, 1) = 1
        """).fetchall():
            sku = (r[0] or '').strip().upper()
            mee_por_producto.setdefault(sku, []).append({
                'mee_codigo': r[1] or '',
                'cantidad_por_unidad': float(r[2] or 1),
                'tipo': r[3] or 'envase',
                'descripcion': r[4] or '',
            })
    except sqlite3.OperationalError:
        # Tabla no existe (esquema antiguo) · seguir sin MEE
        mee_por_producto = {}

    # 4. Cargar volumen unitario por producto (ml por unidad envasada)
    volumen_por_producto = {}
    try:
        for r in c.execute("""
            SELECT producto_nombre, COALESCE(volumen_ml, 0)
            FROM volumen_unitario_producto WHERE COALESCE(activo,1)=1
        """).fetchall():
            volumen_por_producto[(r[0] or '').strip().upper()] = float(r[1] or 0)
    except sqlite3.OperationalError:
        pass
    # Si no hay tabla volumen_unitario, intentar producto_presentaciones
    if not volumen_por_producto:
        try:
            for r in c.execute("""
                SELECT producto_nombre, MAX(COALESCE(volumen_ml, 0))
                FROM producto_presentaciones
                WHERE COALESCE(activo,1)=1
                GROUP BY producto_nombre
            """).fetchall():
                volumen_por_producto[(r[0] or '').strip().upper()] = float(r[1] or 0)
        except sqlite3.OperationalError:
            pass

    # 5. Cargar stock MP (canonical helper)
    stock_mp = _get_mp_stock(conn)

    # 6. Cargar stock MEE
    stock_mee = {}
    try:
        for r in c.execute(
            "SELECT codigo, COALESCE(stock_actual,0) FROM maestro_mee"
        ).fetchall():
            stock_mee[str(r[0] or '').strip().upper()] = float(r[1] or 0)
    except sqlite3.OperationalError:
        pass

    # 7. Cargar info MP (nombre canonico + proveedor sugerido)
    mp_info = {}
    try:
        for r in c.execute("""
            SELECT mm.codigo_mp,
                   COALESCE(mm.nombre_comercial, mm.nombre_inci, mm.codigo_mp) as nombre,
                   COALESCE(NULLIF(TRIM(mlt.proveedor_principal),''), mm.proveedor, '') as prov
            FROM maestro_mps mm
            LEFT JOIN mp_lead_time_config mlt ON mlt.material_id = mm.codigo_mp
            WHERE COALESCE(mm.activo, 1) = 1
        """).fetchall():
            mp_info[r[0]] = {'nombre': r[1] or r[0], 'proveedor': (r[2] or '').strip()}
    except sqlite3.OperationalError:
        pass

    # 8. Cargar info MEE (proveedor sugerido)
    mee_info = {}
    try:
        for r in c.execute("""
            SELECT mm.codigo,
                   COALESCE(mm.descripcion, mm.codigo) as descripcion,
                   COALESCE(cfg.proveedor_principal, mm.proveedor, '') as prov
            FROM maestro_mee mm
            LEFT JOIN mee_lead_time_config cfg ON cfg.mee_codigo = mm.codigo
        """).fetchall():
            mee_info[r[0]] = {
                'descripcion': r[1] or r[0],
                'proveedor': (r[2] or '').strip(),
            }
    except sqlite3.OperationalError:
        pass

    # 9. Por cada producción, calcular MP y MEE necesarios
    producciones_out = []
    consumo_mp_agregado = {}   # codigo_mp -> g_total
    consumo_mee_agregado = {}  # mee_codigo -> unidades_total
    for row in prod_rows:
        # Sebastian 5-may-2026: unpack soporta ambos esquemas (con/sin areas_planta)
        if len(row) >= 12:
            (pid, producto, fecha, lotes, cant_kg_explicita, lote_size,
             area_id, area_codigo, area_nombre,
             estado_norm, inicio_real_at, fin_real_at) = row
        else:
            pid, producto, fecha, lotes, cant_kg_explicita, lote_size = row[:6]
            area_id, area_codigo, area_nombre = 0, '', ''
            estado_norm, inicio_real_at, fin_real_at = 'pendiente', '', ''
        producto_norm = (producto or '').strip().upper()
        lotes = int(lotes or 1)
        cant_kg_total = float(cant_kg_explicita or 0) or (lotes * float(lote_size or 0))

        # MPs necesarias
        mps_nec = []
        for fi in formulas.get(producto_norm, []):
            g_total = float(fi['g_por_lote'] or 0) * lotes
            if g_total <= 0 and cant_kg_total > 0:
                g_total = (fi['porcentaje'] / 100.0) * cant_kg_total * 1000.0
            if g_total <= 0:
                continue
            mps_nec.append({
                'codigo_mp': fi['codigo_mp'],
                'nombre': fi['nombre'],
                'necesario_g': round(g_total, 2),
            })
            cod = (fi['codigo_mp'] or '').strip()
            if cod:
                consumo_mp_agregado[cod] = consumo_mp_agregado.get(cod, 0) + g_total

        # MEE necesarios · cantidad de unidades a envasar = cant_kg_total*1000 / volumen_ml
        unidades_envasadas = 0
        vol_ml = volumen_por_producto.get(producto_norm, 0)
        if vol_ml > 0 and cant_kg_total > 0:
            # Aproximación: 1g ≈ 1ml para productos cosméticos (densidad ~1)
            unidades_envasadas = int(round((cant_kg_total * 1000.0) / vol_ml))

        mees_nec = []
        for me in mee_por_producto.get(producto_norm, []):
            if unidades_envasadas <= 0:
                continue
            cant_total = unidades_envasadas * float(me['cantidad_por_unidad'] or 1)
            mees_nec.append({
                'codigo': me['mee_codigo'],
                'descripcion': me['descripcion'],
                'tipo': me['tipo'],
                'necesario_unidades': round(cant_total, 0),
            })
            cod_mee = (me['mee_codigo'] or '').strip().upper()
            if cod_mee:
                consumo_mee_agregado[cod_mee] = consumo_mee_agregado.get(cod_mee, 0) + cant_total

        producciones_out.append({
            'id': pid,
            'producto': producto,
            'fecha': fecha,
            'lotes': lotes,
            'cantidad_kg': cant_kg_total,
            'mps_necesarias': mps_nec,
            'mees_necesarios': mees_nec,
            'unidades_envasadas_estimadas': unidades_envasadas,
            # Sebastian 5-may-2026: campos para vista calendario por sala
            'area_id': area_id,
            'area_codigo': area_codigo or '',
            'area_nombre': area_nombre or '',
            'estado': estado_norm,
            'inicio_real_at': inicio_real_at or None,
            'fin_real_at': fin_real_at or None,
        })

    # 10. Calcular faltantes agregados
    faltantes_mps = []
    for cod, g_total in consumo_mp_agregado.items():
        info = mp_info.get(cod, {'nombre': cod, 'proveedor': ''})
        s_actual = float(stock_mp.get(cod, 0))
        if s_actual == 0:
            # Fallback: buscar por nombre canonico
            nom_up = (info.get('nombre') or '').upper()
            if nom_up in stock_mp:
                s_actual = float(stock_mp[nom_up])
        faltante = max(0.0, g_total - s_actual)
        if faltante > 0:
            faltantes_mps.append({
                'codigo_mp': cod,
                'nombre': info['nombre'],
                'necesario_total_g': round(g_total, 2),
                'stock_actual_g': round(s_actual, 2),
                'faltante_g': round(faltante, 2),
                'proveedor_sugerido': info['proveedor'],
            })
    faltantes_mps.sort(key=lambda x: -x['faltante_g'])

    faltantes_mees = []
    for cod, u_total in consumo_mee_agregado.items():
        info = mee_info.get(cod, {'descripcion': cod, 'proveedor': ''})
        s_actual = float(stock_mee.get(cod, 0))
        faltante = max(0.0, u_total - s_actual)
        if faltante > 0:
            faltantes_mees.append({
                'codigo': cod,
                'descripcion': info['descripcion'],
                'tipo': '',
                'necesario_total_u': round(u_total, 0),
                'stock_actual_u': round(s_actual, 0),
                'faltante_u': round(faltante, 0),
                'proveedor_sugerido': info['proveedor'],
            })
    faltantes_mees.sort(key=lambda x: -x['faltante_u'])

    # Proveedores únicos involucrados
    provs = {f['proveedor_sugerido'] for f in faltantes_mps if f['proveedor_sugerido']}
    provs |= {f['proveedor_sugerido'] for f in faltantes_mees if f['proveedor_sugerido']}

    return jsonify({
        'horizonte_dias': dias,
        'producciones': producciones_out,
        'faltantes_mps': faltantes_mps,
        'faltantes_mees': faltantes_mees,
        'resumen': {
            'n_producciones': len(producciones_out),
            'n_mps_faltantes': len(faltantes_mps),
            'n_mees_faltantes': len(faltantes_mees),
            'n_proveedores_unicos': len(provs),
        },
    })


@bp.route('/api/programacion/solicitar-faltantes-bulk', methods=['POST'])
def solicitar_faltantes_bulk():
    """Crea solicitudes_compra agrupadas por proveedor desde los faltantes
    detectados en /api/programacion/producciones-faltantes.

    Body:
      dias: int (default 60) · mismo horizonte usado para detectar faltantes
      urgencia: 'Alta' | 'Normal' | 'Baja' (default 'Alta')
      observaciones_extra: str (opcional)

    Returns:
      201 {ok, solicitudes_creadas: [{numero, proveedor, items_count, total_g}],
           total_proveedores, total_solicitudes}
      400 si no hay faltantes
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(COMPRAS_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Compras/Admin pueden generar solicitudes'}), 403

    body = request.get_json(silent=True) or {}
    try:
        dias = max(7, min(int(body.get('dias', 60)), 365))
    except (ValueError, TypeError):
        dias = 60
    urgencia = (body.get('urgencia') or 'Alta').strip()
    if urgencia not in ('Alta', 'Normal', 'Baja'):
        urgencia = 'Alta'
    obs_extra = (body.get('observaciones_extra') or '').strip()

    # Reutilizar el endpoint anterior llamandolo internamente
    from flask import current_app
    with current_app.test_request_context(
        f'/api/programacion/producciones-faltantes?dias={dias}'
    ):
        # Bypass auth check del helper interno
        from flask import session as _s
        _s['compras_user'] = user
        resp = producciones_faltantes()
    data = resp.get_json() if hasattr(resp, 'get_json') else (resp[0].get_json() if isinstance(resp, tuple) else {})
    faltantes_mps = data.get('faltantes_mps') or []
    faltantes_mees = data.get('faltantes_mees') or []
    if not faltantes_mps and not faltantes_mees:
        return jsonify({
            'ok': True,
            'mensaje': 'No hay faltantes en el horizonte · nada que solicitar',
            'solicitudes_creadas': [],
            'total_proveedores': 0,
            'total_solicitudes': 0,
        }), 200

    # Agrupar por proveedor (sin proveedor sugerido = grupo aparte)
    grupos = {}
    for f in faltantes_mps:
        prov = (f.get('proveedor_sugerido') or '').strip() or '__SIN_PROVEEDOR__'
        grupos.setdefault(prov, {'mps': [], 'mees': []})
        grupos[prov]['mps'].append(f)
    for f in faltantes_mees:
        prov = (f.get('proveedor_sugerido') or '').strip() or '__SIN_PROVEEDOR__'
        grupos.setdefault(prov, {'mps': [], 'mees': []})
        grupos[prov]['mees'].append(f)

    conn = get_db(); c = conn.cursor()
    creadas = []
    fecha_now = datetime.now().isoformat()
    obs_base_horizonte = f"Auto-generada Centro Programación · horizonte {dias}d"
    if obs_extra:
        obs_base_horizonte = obs_extra + ' · ' + obs_base_horizonte

    try:
        for prov, items in sorted(grupos.items()):
            mps_lst = items.get('mps', [])
            mees_lst = items.get('mees', [])
            if not mps_lst and not mees_lst:
                continue
            # Crear SOL-YYYY-XXXX
            c.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) "
                "FROM solicitudes_compra WHERE numero LIKE ?",
                (f"SOL-{datetime.now().strftime('%Y')}-%",),
            )
            num = (c.fetchone()[0] or 0) + 1
            numero = f"SOL-{datetime.now().strftime('%Y')}-{num:04d}"
            prov_label = prov if prov != '__SIN_PROVEEDOR__' else ''
            obs = obs_base_horizonte
            if prov_label:
                obs += f" · proveedor: {prov_label}"
            obs += (f" · {len(mps_lst)} MPs · {len(mees_lst)} MEEs")

            # Categoria · si solo hay MEEs y nada de MP, marcamos categoria='Empaque'
            categoria = 'Materia Prima'
            if not mps_lst and mees_lst:
                categoria = 'Empaque'

            c.execute("""
                INSERT INTO solicitudes_compra
                  (numero, fecha, estado, solicitante, urgencia, observaciones,
                   area, empresa, categoria, tipo)
                VALUES (?, ?, 'Pendiente', ?, ?, ?, 'Producción', 'Espagiria', ?, 'Compra')
            """, (numero, fecha_now, user, urgencia, obs, categoria))

            items_count = 0
            total_g_mps = 0.0
            for mp in mps_lst:
                try:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado, proveedor_sugerido)
                        VALUES (?, ?, ?, ?, 'g', ?, 0, ?)
                    """, (numero, mp['codigo_mp'], mp['nombre'],
                          mp['faltante_g'],
                          f"Falta para producción {dias}d · stock {mp['stock_actual_g']}g de {mp['necesario_total_g']}g necesarios",
                          prov_label))
                except sqlite3.OperationalError:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado)
                        VALUES (?, ?, ?, ?, 'g', ?, 0)
                    """, (numero, mp['codigo_mp'], mp['nombre'],
                          mp['faltante_g'],
                          f"Falta para producción {dias}d · stock {mp['stock_actual_g']}g de {mp['necesario_total_g']}g"))
                items_count += 1
                total_g_mps += float(mp.get('faltante_g') or 0)

            for me in mees_lst:
                # Items MEE · usar nombre_mp como descripcion + cantidad en unidades
                try:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado, proveedor_sugerido)
                        VALUES (?, ?, ?, ?, 'unidades', ?, 0, ?)
                    """, (numero, me['codigo'], me['descripcion'],
                          me['faltante_u'],
                          f"Falta para envasar producción {dias}d · stock {me['stock_actual_u']}u de {me['necesario_total_u']}u",
                          prov_label))
                except sqlite3.OperationalError:
                    c.execute("""
                        INSERT INTO solicitudes_compra_items
                          (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                           justificacion, valor_estimado)
                        VALUES (?, ?, ?, ?, 'unidades', ?, 0)
                    """, (numero, me['codigo'], me['descripcion'],
                          me['faltante_u'],
                          f"Falta para envasar {dias}d · stock {me['stock_actual_u']}u de {me['necesario_total_u']}u"))
                items_count += 1

            try:
                audit_log(
                    c, usuario=user, accion='SOLICITAR_FALTANTES_BULK',
                    tabla='solicitudes_compra', registro_id=numero,
                    despues={
                        'proveedor': prov_label or '(sin proveedor)',
                        'horizonte_dias': dias,
                        'urgencia': urgencia,
                        'mps_count': len(mps_lst),
                        'mees_count': len(mees_lst),
                        'items_count': items_count,
                    },
                    detalle=(f"Auto-bulk: {numero} · {prov_label or 'sin proveedor'} · "
                              f"{len(mps_lst)} MPs + {len(mees_lst)} MEEs"),
                )
            except Exception as _e:
                log.warning('audit_log SOLICITAR_FALTANTES_BULK fallo: %s', _e)

            creadas.append({
                'numero': numero,
                'proveedor': prov_label or '(sin proveedor)',
                'items_count': items_count,
                'mps_count': len(mps_lst),
                'mees_count': len(mees_lst),
                'total_g_mps': round(total_g_mps, 2),
            })

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        log.exception('solicitar_faltantes_bulk fallo: %s', e)
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'ok': True,
        'mensaje': f'Creadas {len(creadas)} solicitudes para {len(creadas)} proveedores',
        'solicitudes_creadas': creadas,
        'total_proveedores': len(creadas),
        'total_solicitudes': len(creadas),
        'horizonte_dias': dias,
    }), 201


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
            except Exception as _r:
                logging.getLogger('programacion').debug('rollback no aplicable: %s', _r)
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
        'MESA','LOTES','LOTE','MINI','MACRO','AND','THE','FOR',
        # Tokens de codigo de area que Alejandro escribe — no son SKUs
        'FAB1','FYE2','FYE3','ENV1','ENV2','PROD1','PROD2','PROD3','PROD4'
    }
    NON_FAB_KW = {
        'envasado', 'acondicionamiento', 'micro qc',
        'control de calidad', 'dispensado', 'etiquetado', 'llenado',
    }

    # Mapa codigo_corto_alejandro → codigo_real_db (areas_planta.codigo)
    # Sebastián 2-may-2026: "alejandro escribe [FAB1] o [FYE2] al inicio del
    # evento de Calendar y el sistema asigna sala automatica". Acepta tambien
    # los codigos reales (PROD1..PROD4) por si el equipo los usa directo.
    AREA_ALIAS = {
        'FAB1': 'PROD1', 'FYE2': 'PROD2', 'FYE3': 'PROD3', 'ENV2': 'PROD4',
        'ENV1': 'ENV1',
        'PROD1': 'PROD1', 'PROD2': 'PROD2', 'PROD3': 'PROD3', 'PROD4': 'PROD4',
    }
    # Mapa codigo_real_db → area_id (cargado una vez fuera del loop)
    codigo_a_areaid = {}
    try:
        for r in conn.execute(
            "SELECT id, codigo FROM areas_planta WHERE activo=1"
        ).fetchall():
            codigo_a_areaid[r[1]] = r[0]
    except Exception:
        pass

    def _skus(titulo):
        tokens = _re.findall(r'\b([A-Z][A-Z0-9]{1,}[A-Z0-9])\b', titulo.upper())
        return [t for t in tokens if t not in NOT_SKU]

    def _kg(titulo):
        m = _re.findall(r'~?(\d+(?:[,.]\d+)*)\s*kg', titulo, _re.IGNORECASE)
        if not m: return None
        try: return float(m[-1].replace(',', '.'))
        except Exception: return None

    def _area_from_titulo(titulo):
        """Extrae area_id del prefijo [CODIGO] del titulo del evento.

        Convención Alejandro (May 2026): el evento de Calendar empieza con
        un código entre corchetes, ej: '[FAB1] Gel Hidratante 50ml ~5kg' o
        '[FYE2] Blush Balm ~3kg'. Si lo encuentra, devuelve el area_id de
        areas_planta. Si no, None.
        """
        if not titulo:
            return None
        m = _re.match(r'\s*\[([A-Z0-9]{3,5})\]', titulo)
        if not m:
            return None
        codigo_corto = m.group(1).upper()
        codigo_real = AREA_ALIAS.get(codigo_corto)
        if not codigo_real:
            return None
        return codigo_a_areaid.get(codigo_real)

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
        # Extraer area del prefijo [CODIGO] (Alejandro convention).
        area_id_titulo = _area_from_titulo(titulo)
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
                    "SELECT id, COALESCE(cantidad_kg,0), area_id "
                    "FROM produccion_programada "
                    "WHERE producto=? AND fecha_programada=? LIMIT 1",
                    (prod, fecha_s)
                ).fetchone()
                if not exists:
                    # origen='calendar' para que planificacion_estrategica las
                    # filtre y no duplique con su lectura directa del calendar.
                    # area_id = del prefijo [CODIGO] si Alejandro lo puso, sino NULL.
                    cur_ins = conn.execute(
                        """INSERT INTO produccion_programada
                           (producto, fecha_programada, lotes, cantidad_kg,
                            estado, observaciones, origen, area_id)
                           VALUES (?, ?, ?, ?, 'programado', ?, 'calendar', ?)""",
                        (prod, fecha_s, lotes, cantidad_kg_calc,
                         f'[auto-sync calendar] {titulo[:200]}', area_id_titulo)
                    )
                    inserted += 1
                    # Sebastián 1-may-2026: "todo automático". Auto-asignar
                    # área + operarios INMEDIATAMENTE al insertar (no esperar
                    # cron 06:30). Si falla, sigue → cron lo intentará después.
                    # Si Alejandro ya puso [CODIGO] en titulo, NO sobrescribir
                    # con auto-asignador: respeta su decision.
                    try:
                        new_id = cur_ins.lastrowid
                        if (new_id and cantidad_kg_calc and cantidad_kg_calc > 0
                                and area_id_titulo is None):
                            _auto_asignar_produccion(conn.cursor(), new_id, 'auto-sync-calendar')
                    except Exception:
                        pass
                else:
                    # Backfill cantidad_kg si falta.
                    if (exists[1] or 0) <= 0 and cantidad_kg_calc > 0:
                        conn.execute(
                            "UPDATE produccion_programada SET cantidad_kg=? WHERE id=?",
                            (cantidad_kg_calc, exists[0])
                        )
                    # Backfill area_id: si Alejandro acaba de meter [CODIGO]
                    # en un evento que ya existe en DB sin area, actualizamos.
                    # Si DB ya tiene area distinta, NO la pisamos (alguien la
                    # asignó manualmente en la UI — gana lo manual).
                    if area_id_titulo is not None and (exists[2] is None):
                        conn.execute(
                            "UPDATE produccion_programada SET area_id=? WHERE id=?",
                            (area_id_titulo, exists[0])
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
    #
    # Audit zero-error 2-may-2026 (CERO SESGO):
    # GUARD CRÍTICO · NO cancelar producciones que ya iniciaron o ya
    # descontaron inventario. Si Sebastián borra un evento del Calendar
    # MIENTRAS la producción está en curso, hacerla 'cancelado' aquí
    # corromperia el estado y crearía drift de inventario. En ese caso,
    # hay que dejarla activa y registrar la acción en audit_log para que
    # alguien revise manualmente (probablemente fue un error en Calendar).
    archived = 0
    skipped_in_progress = []
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
        # Filas activas con origen='calendar' que NO estan en el calendar actual.
        # IMPORTANTE: capturar inicio_real_at + inventario_descontado_at para
        # decidir si es seguro cancelar (no corromper inventario en curso).
        candidatos = conn.execute(
            """SELECT id, producto, fecha_programada,
                      COALESCE(inicio_real_at,'') as inicio,
                      COALESCE(inventario_descontado_at,'') as descontado
               FROM produccion_programada
               WHERE origen='calendar'
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                 AND fecha_programada >= date('now','-1 day')"""
        ).fetchall()
        huerfanos = []
        for r in candidatos:
            id_, prod, fecha, inicio, descontado = r
            if (prod, fecha) in keys_calendar:
                continue  # sigue en calendar, no es huérfano
            # GUARD: si ya inició o ya descontó inventario, NO cancelar
            if inicio or descontado:
                skipped_in_progress.append({
                    'id': id_, 'producto': prod, 'fecha': fecha,
                    'inicio_real_at': inicio or None,
                    'inventario_descontado_at': descontado or None,
                })
                continue
            huerfanos.append(id_)
        if huerfanos:
            placeholders = ','.join(['?'] * len(huerfanos))
            conn.execute(
                f"UPDATE produccion_programada SET estado='cancelado', "
                f"observaciones=COALESCE(observaciones,'') || ' [auto-cancelado: ya no esta en calendar]' "
                f"WHERE id IN ({placeholders})",
                huerfanos
            )
            archived = len(huerfanos)
            # Audit log · cada cancelación auto debe quedar trazada
            try:
                from audit_helpers import audit_log as _audit_log
                cur = conn.cursor()
                for prod_id in huerfanos:
                    _audit_log(cur, usuario='sistema_calendar_sync',
                               accion='AUTO_CANCELAR_PRODUCCION',
                               tabla='produccion_programada',
                               registro_id=prod_id,
                               despues={'estado': 'cancelado',
                                         'razon': 'evento ya no existe en calendar'},
                               detalle=f"Sync calendar auto-canceló producción id={prod_id}")
            except Exception:
                pass
            conn.commit()
        # Audit log para producciones que se SALTARON cancelar (en curso)
        if skipped_in_progress:
            try:
                from audit_helpers import audit_log as _audit_log
                cur = conn.cursor()
                for sk in skipped_in_progress:
                    _audit_log(cur, usuario='sistema_calendar_sync',
                               accion='SYNC_CALENDAR_SKIP_EN_CURSO',
                               tabla='produccion_programada',
                               registro_id=sk['id'],
                               detalle=(f"Producción {sk['producto']} ({sk['fecha']}) "
                                         f"removida del calendar pero está EN CURSO "
                                         f"(inicio={sk['inicio_real_at']}, "
                                         f"descontado={sk['inventario_descontado_at']}). "
                                         f"NO se canceló · revisar manualmente."))
                conn.commit()
            except Exception:
                pass
    except Exception:
        archived = 0
        skipped_in_progress = []

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
                        try:
                            from audit_helpers import audit_log as _al
                            _al(c, usuario=session.get('compras_user', 'sistema'),
                                accion='CREAR_PROVEEDOR', tabla='proveedores',
                                registro_id=c.lastrowid,
                                despues={'nombre': proveedor[:200],
                                          'categoria': categoria,
                                          'origen': 'auto_planta_oc'},
                                detalle=f"Auto-creado desde planta al generar OC")
                        except Exception:
                            pass
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
       ?contexto=planta|mias|todas (Sebastian 29-abr-2026: el caso
        "Cargar influencers" salia en /planta porque era una tarea
        chat_asignacion para Jeferson — la asignacion era grupal).
        - planta: solo tareas fisicas de planta (excluye chat_asignacion)
        - mias: solo asignadas al usuario actual
        - todas (default): backward-compatible
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    me = (session.get('compras_user', '') or '').strip().lower()
    usuario = (request.args.get('usuario') or '').strip().lower()
    estado_q = (request.args.get('estado') or '').strip()
    contexto = (request.args.get('contexto') or '').strip().lower()
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
    if contexto == 'planta':
        # Solo tipos fisicos de planta. chat_asignacion es generica entre
        # cualquier par de usuarios y NO pertenece al flujo de planta.
        where.append("(tipo IN ('sacar_envases_serigrafia','sacar_envases_tampografia','sacar_inventario','envasado','etiquetado','recoleccion_mee','recoleccion_mp','dispensacion','limpieza_sala','cambio_lote','muestreo','revision_visual') "
                     "OR origen_tipo IN ('solicitud_produccion','sol_anticipada'))")
        where.append("COALESCE(origen_tipo,'') != 'chat'")
    elif contexto == 'mias':
        # Solo las asignadas a mi (csv split o match exacto). origen_tipo
        # 'chat' tambien aplica — son tareas que me asignaron en chat.
        where.append("(',' || LOWER(REPLACE(COALESCE(asignado_a,''),' ','')) || ',') LIKE ?")
        params.append(f"%,{me},%")
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


# ════════════════════════════════════════════════════════════════════════
# PLANTA INTELIGENTE — FASE 0: Presentaciones por SKU
# ════════════════════════════════════════════════════════════════════════
# Sebastian + Alejandro (30-abr-2026): los productos tienen multiples
# presentaciones (suero 30/15/10mL, contornos 15/10mL, maxlash 4.5mL,
# blush balm 6g). Sin esto, "produzcamos suero para 2 meses" es ambiguo.
# Esta tabla se llena via UI o bulk import. NO toca formula_headers.

# Catalogo de categorias estandar con sus presentaciones default segun el
# brief de Alejandro (30-abr-2026). Sirve como sugerencia al crear.
PRESENTACIONES_DEFAULT_POR_CATEGORIA = {
    'limpiador': [
        {'codigo': 'lmp_150ml', 'etiqueta': 'Limpiador 150 mL', 'volumen_ml': 150,
         'envase_codigo': '', 'notas': 'Plástico tapa rosca blanco'}
    ],
    'hidratante': [
        {'codigo': 'hid_50ml', 'etiqueta': 'Hidratante 50 mL airless', 'volumen_ml': 50,
         'envase_codigo': '', 'notas': 'Plástico airless'}
    ],
    'suero': [
        {'codigo': 'sue_30ml', 'etiqueta': 'Suero 30 mL', 'volumen_ml': 30,
         'envase_codigo': '', 'notas': ''},
        {'codigo': 'sue_15ml', 'etiqueta': 'Suero 15 mL', 'volumen_ml': 15,
         'envase_codigo': '', 'notas': ''},
        {'codigo': 'sue_10ml', 'etiqueta': 'Suero 10 mL', 'volumen_ml': 10,
         'envase_codigo': '', 'notas': ''},
    ],
    'contorno_ojos': [
        {'codigo': 'co_15ml', 'etiqueta': 'Contorno 15 mL (multipéptidos/retinal)', 'volumen_ml': 15,
         'envase_codigo': '', 'notas': 'Multipéptidos y retinal'},
        {'codigo': 'co_10ml', 'etiqueta': 'Contorno 10 mL (cafeína)', 'volumen_ml': 10,
         'envase_codigo': '', 'notas': 'Cafeína'},
    ],
    'maxlash': [
        {'codigo': 'mx_45ml', 'etiqueta': 'Maxlash 4.5 mL', 'volumen_ml': 4.5,
         'envase_codigo': '', 'notas': 'Suero cejas y pestañas'}
    ],
    'blush_balm': [
        {'codigo': 'bb_6g', 'etiqueta': 'Blush Balm 6 g', 'volumen_ml': None,
         'envase_codigo': '', 'notas': 'Peso 6g'}
    ],
}


@bp.route('/api/planta/presentaciones', methods=['GET'])
def planta_presentaciones_list():
    """Lista presentaciones registradas. Querystring opcional:
       ?producto=<nombre> filtra por producto exacto
       ?categoria=<cat> filtra por categoria
       ?activos=1 (default) solo activos
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    where = []
    params = []
    if request.args.get('producto'):
        where.append('producto_nombre = ?')
        params.append(request.args.get('producto').strip())
    if request.args.get('categoria'):
        where.append('categoria = ?')
        params.append(request.args.get('categoria').strip())
    if request.args.get('activos', '1') == '1':
        where.append('activo = 1')
    sql = "SELECT * FROM producto_presentaciones"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY producto_nombre, COALESCE(volumen_ml, 999) DESC, etiqueta LIMIT 2000"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # Resumen por producto
    productos = {}
    for it in items:
        pn = it['producto_nombre'] or '(sin asignar)'
        productos.setdefault(pn, []).append(it)
    return jsonify({
        'presentaciones': items,
        'total': len(items),
        'por_producto': productos,
        'plantillas_default': PRESENTACIONES_DEFAULT_POR_CATEGORIA,
    })


@bp.route('/api/planta/presentaciones', methods=['POST'])
def planta_presentaciones_crear():
    """Crear presentacion individual.
    Body: {producto_nombre*, categoria, presentacion_codigo*, etiqueta*,
           volumen_ml, peso_g, envase_codigo, factor_g_por_unidad,
           sku_shopify, es_default, notas}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    producto = (d.get('producto_nombre') or '').strip()
    pcode = (d.get('presentacion_codigo') or '').strip()
    etiqueta = (d.get('etiqueta') or '').strip()
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if not pcode:
        return jsonify({'error': 'presentacion_codigo requerido'}), 400
    if not etiqueta:
        return jsonify({'error': 'etiqueta requerida'}), 400
    conn = get_db(); c = conn.cursor()
    try:
        cur = c.execute("""
            INSERT INTO producto_presentaciones
              (producto_nombre, categoria, presentacion_codigo, etiqueta,
               volumen_ml, peso_g, envase_codigo, factor_g_por_unidad,
               sku_shopify, es_default, activo, notas, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))
        """, (
            producto,
            (d.get('categoria') or '').strip() or None,
            pcode, etiqueta,
            d.get('volumen_ml'),
            d.get('peso_g'),
            (d.get('envase_codigo') or '').strip() or None,
            d.get('factor_g_por_unidad'),
            (d.get('sku_shopify') or '').strip() or None,
            1 if d.get('es_default') else 0,
            (d.get('notas') or '').strip() or None,
        ))
        conn.commit()
        return jsonify({'ok': True, 'id': cur.lastrowid})
    except sqlite3.IntegrityError as e:
        return jsonify({'error': f'Presentación ya existe para este producto: {e}'}), 409


@bp.route('/api/planta/presentaciones/<int:pid>', methods=['PUT', 'DELETE'])
def planta_presentaciones_detail(pid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'DELETE':
        # Soft delete (activo=0). No borramos para preservar referencias historicas.
        c.execute("UPDATE producto_presentaciones SET activo=0, actualizado_en=datetime('now') WHERE id=?", (pid,))
        conn.commit()
        return jsonify({'ok': True})
    # PUT
    d = request.json or {}
    campos = []
    params = []
    for col in ('etiqueta', 'categoria', 'volumen_ml', 'peso_g', 'envase_codigo',
                'factor_g_por_unidad', 'sku_shopify', 'es_default', 'notas'):
        if col in d:
            campos.append(f'{col} = ?')
            v = d[col]
            if col in ('volumen_ml', 'peso_g', 'factor_g_por_unidad'):
                v = float(v) if v not in (None, '') else None
            elif col == 'es_default':
                v = 1 if v else 0
            elif isinstance(v, str):
                v = v.strip() or None
            params.append(v)
    if not campos:
        return jsonify({'error': 'Sin cambios'}), 400
    campos.append("actualizado_en = datetime('now')")
    params.append(pid)
    c.execute(f"UPDATE producto_presentaciones SET {', '.join(campos)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok': True, 'updated': c.rowcount})


@bp.route('/api/planta/presentaciones/bulk-categoria', methods=['POST'])
def planta_presentaciones_bulk_categoria():
    """Aplica las plantillas default de una categoria a un producto especifico.
    Util para arrancar rapido — Alejandro elige producto + categoria y se
    crean las N presentaciones default.
    Body: {producto_nombre*, categoria*}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    producto = (d.get('producto_nombre') or '').strip()
    categoria = (d.get('categoria') or '').strip().lower()
    if not producto or not categoria:
        return jsonify({'error': 'producto_nombre y categoria requeridos'}), 400
    plantillas = PRESENTACIONES_DEFAULT_POR_CATEGORIA.get(categoria)
    if not plantillas:
        return jsonify({
            'error': f'Categoria "{categoria}" no reconocida',
            'categorias_validas': list(PRESENTACIONES_DEFAULT_POR_CATEGORIA.keys())
        }), 400
    conn = get_db(); c = conn.cursor()
    creadas = []
    for p in plantillas:
        try:
            cur = c.execute("""
                INSERT INTO producto_presentaciones
                  (producto_nombre, categoria, presentacion_codigo, etiqueta,
                   volumen_ml, envase_codigo, es_default, activo, notas, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))
            """, (
                producto, categoria, p['codigo'], p['etiqueta'],
                p['volumen_ml'], p.get('envase_codigo') or None,
                1 if len(plantillas) == 1 else 0,
                p.get('notas') or None,
            ))
            creadas.append({'id': cur.lastrowid, 'codigo': p['codigo']})
        except sqlite3.IntegrityError:
            # Ya existia — saltar silenciosamente
            pass
    conn.commit()
    return jsonify({'ok': True, 'creadas': creadas, 'total': len(creadas)})


@bp.route('/api/planta/presentaciones/productos-disponibles', methods=['GET'])
def planta_presentaciones_productos_disponibles():
    """Lista productos de formula_headers + cuántas presentaciones tienen ya."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT fh.producto_nombre,
               fh.lote_size_kg,
               (SELECT COUNT(*) FROM producto_presentaciones pp
                WHERE pp.producto_nombre = fh.producto_nombre AND pp.activo=1) AS n_presentaciones
        FROM formula_headers fh
        ORDER BY fh.producto_nombre
    """).fetchall()
    items = []
    for r in rows:
        items.append({
            'producto_nombre': r[0],
            'lote_size_kg': r[1],
            'n_presentaciones': r[2] or 0,
        })
    return jsonify({'productos': items, 'total': len(items)})


# ════════════════════════════════════════════════════════════════════════
# PLANTA INTELIGENTE — FASE 1: Catálogo de equipos + sugerencia de área
# ════════════════════════════════════════════════════════════════════════
# Sebastian + Alejandro (30-abr-2026): el Excel "LISTADO MAESTRO DE EQUIPOS
# 2026" tiene 104 equipos en 9 areas reales. La migracion 63 los importa.
# Aqui exponemos endpoints para listar, ver y sugerir area al programar
# producciones (cruce capacidad-de-tanque vs tamaño-de-lote).

@bp.route('/api/planta/equipos', methods=['GET'])
def planta_equipos_list():
    """Lista todos los equipos. Querystring opcional:
       ?area=<codigo>  filtra por area
       ?tipo=<tipo>    filtra por tipo (tanque, envasadora, etc.)
       ?con_capacidad=1 solo equipos con capacidad_litros NOT NULL
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    where = ['activo=1']
    params = []
    if request.args.get('area'):
        where.append('area_codigo = ?')
        params.append(request.args.get('area').strip())
    if request.args.get('tipo'):
        where.append('tipo = ?')
        params.append(request.args.get('tipo').strip())
    if request.args.get('con_capacidad') == '1':
        where.append('capacidad_litros IS NOT NULL')
    sql = "SELECT * FROM equipos_planta WHERE " + " AND ".join(where) + " ORDER BY area_codigo, COALESCE(capacidad_litros, 0) DESC, nombre"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # Resumen por área + por tipo
    por_area = {}
    por_tipo = {}
    for it in items:
        a = it.get('area_codigo') or '—'
        t = it.get('tipo') or 'otro'
        por_area.setdefault(a, []).append(it)
        por_tipo[t] = por_tipo.get(t, 0) + 1
    return jsonify({
        'equipos': items,
        'total': len(items),
        'por_area': por_area,
        'por_tipo': por_tipo,
    })


@bp.route('/api/planta/equipos/<int:eq_id>', methods=['GET', 'PUT', 'DELETE'])
def planta_equipos_detail(eq_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        r = c.execute("SELECT * FROM equipos_planta WHERE id=?", (eq_id,)).fetchone()
        if not r:
            return jsonify({'error': 'No existe'}), 404
        cols = [d[0] for d in c.description]
        return jsonify({'equipo': dict(zip(cols, r))})
    if request.method == 'DELETE':
        c.execute("UPDATE equipos_planta SET activo=0, actualizado_en=datetime('now') WHERE id=?", (eq_id,))
        conn.commit()
        return jsonify({'ok': True})
    # PUT
    d = request.json or {}
    campos = []
    params = []
    for col in ('nombre', 'area_codigo', 'tipo', 'capacidad_raw',
                'capacidad_litros', 'capacidad_kg', 'estado_operacional',
                'notas'):
        if col in d:
            campos.append(f'{col} = ?')
            v = d[col]
            if col in ('capacidad_litros', 'capacidad_kg'):
                v = float(v) if v not in (None, '') else None
            elif isinstance(v, str):
                v = v.strip() or None
            params.append(v)
    if not campos:
        return jsonify({'error': 'Sin cambios'}), 400
    campos.append("actualizado_en = datetime('now')")
    params.append(eq_id)
    c.execute(f"UPDATE equipos_planta SET {', '.join(campos)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/planta/areas/v2', methods=['GET'])
def planta_areas_v2():
    """Listado de areas con equipos asignados. Mas rico que /api/planta/areas."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT a.codigo, a.nombre, a.tipo, a.estado, a.activo,
               a.requiere_limpieza_profunda,
               a.ultima_limpieza_profunda,
               a.puede_producir, a.puede_envasar,
               (SELECT COUNT(*) FROM equipos_planta WHERE area_codigo=a.codigo AND activo=1) AS n_equipos,
               (SELECT MAX(capacidad_litros) FROM equipos_planta
                  WHERE area_codigo=a.codigo AND activo=1 AND tipo='tanque') AS max_tanque_l,
               (SELECT MIN(capacidad_litros) FROM equipos_planta
                  WHERE area_codigo=a.codigo AND activo=1 AND tipo='tanque'
                    AND capacidad_litros IS NOT NULL) AS min_tanque_l
        FROM areas_planta a
        WHERE a.activo=1
        ORDER BY a.orden, a.codigo
    """).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'areas': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/planta/sugerir-area', methods=['POST'])
def planta_sugerir_area():
    """Sugerencia inteligente de área para una producción.

    Body: {producto_nombre*, lote_kg*, presentacion_codigo?}

    Lógica (Sebastian + Alejandro, 30-abr-2026):
      1. Filtrar areas con puede_producir=1 que tengan al menos 1 tanque
         con capacidad >= lote_kg * 1.2 (margen 20%, asumiendo densidad ~1).
      2. De las que pasan, preferir el tanque MAS PEQUEÑO que aguante
         (eficiencia: no usar tanque 400L para lote de 30L).
      3. Score adicional:
         + estado='libre' (sin produccion en curso)
         + cercania al envasado (FAB1->ENV1, FAB2/3->ENV2)
         + ultima_limpieza_profunda reciente (<7 dias)
      4. Devolver lista ordenada con score y razon.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    producto = (d.get('producto_nombre') or '').strip()
    lote_kg = float(d.get('lote_kg') or 0)
    if not producto or lote_kg <= 0:
        return jsonify({'error': 'producto_nombre y lote_kg requeridos'}), 400
    conn = get_db(); c = conn.cursor()

    # Margen de 20% sobre el lote (densidad cercana a agua = 1 g/mL = 1 kg/L)
    capacidad_min_litros = lote_kg * 1.2

    # Buscar tanques candidatos (con capacidad suficiente)
    tanques = c.execute("""
        SELECT id, codigo, nombre, area_codigo, capacidad_litros
        FROM equipos_planta
        WHERE activo=1 AND tipo IN ('tanque','marmita','olla')
          AND capacidad_litros IS NOT NULL
          AND capacidad_litros >= ?
        ORDER BY capacidad_litros ASC
    """, (capacidad_min_litros,)).fetchall()

    # Agrupar por area y tomar el mas pequeño que aguante
    por_area = {}
    for t in tanques:
        a = t[3]
        if a not in por_area or t[4] < por_area[a]['capacidad_litros']:
            por_area[a] = {
                'tanque_id': t[0],
                'tanque_codigo': t[1],
                'tanque_nombre': t[2],
                'capacidad_litros': t[4],
            }

    # Cargar info de areas candidatas
    sugerencias = []
    for area_codigo, tanque_info in por_area.items():
        area_row = c.execute("""
            SELECT codigo, nombre, estado, puede_producir, puede_envasar,
                   requiere_limpieza_profunda, ultima_limpieza_profunda
            FROM areas_planta WHERE codigo=? AND activo=1
        """, (area_codigo,)).fetchone()
        if not area_row:
            continue
        if not area_row[3]:  # puede_producir
            continue
        score = 0
        razones = []
        # Eficiencia: tanque pequeño que aguanta
        utilizacion = (lote_kg / tanque_info['capacidad_litros']) * 100
        score += 50 if utilizacion >= 50 else 30
        razones.append(f"Tanque {tanque_info['capacidad_litros']:.0f}L · uso {utilizacion:.0f}%")
        # Estado libre
        if area_row[2] == 'libre':
            score += 20
            razones.append('Sala libre')
        elif area_row[2] == 'ocupada':
            score -= 10
            razones.append('Sala ocupada')
        # Cercania a envasado (regla suave Fab1->Env1, Fab2/3->Env2)
        env_cercano = ''
        if area_codigo in ('FAB1', 'PROD1'):
            env_cercano = 'ENV1'
        elif area_codigo in ('FAB2', 'PROD2', 'FAB3', 'PROD3'):
            env_cercano = 'ENV2'
        # Limpieza reciente
        if area_row[5]:  # requiere limpieza profunda
            if area_row[6]:
                from datetime import datetime as _dt
                try:
                    last = _dt.fromisoformat((area_row[6] or '').split('.')[0])
                    dias = (_dt.now() - last).days
                    if dias <= 7:
                        score += 10
                        razones.append(f"Limpieza profunda hace {dias}d")
                    elif dias > 14:
                        score -= 15
                        razones.append(f"⚠ Limpieza profunda hace {dias}d (>14d)")
                except Exception:
                    pass
            else:
                score -= 5
                razones.append('Sin registro de limpieza profunda')
        sugerencias.append({
            'area_codigo': area_codigo,
            'area_nombre': area_row[1],
            'tanque': tanque_info,
            'estado_actual': area_row[2],
            'envasado_sugerido': env_cercano,
            'utilizacion_pct': round(utilizacion, 1),
            'score': score,
            'razones': razones,
        })

    sugerencias.sort(key=lambda x: x['score'], reverse=True)

    return jsonify({
        'producto_nombre': producto,
        'lote_kg': lote_kg,
        'capacidad_minima_litros': capacidad_min_litros,
        'sugerencias': sugerencias,
        'recomendada': sugerencias[0] if sugerencias else None,
        'mensaje': (
            f'No hay área con tanque ≥ {capacidad_min_litros:.0f}L disponible. '
            f'Considera dividir el lote o revisar el catálogo de equipos.'
            if not sugerencias else
            f'{len(sugerencias)} área(s) candidata(s). '
            f'Recomendada: {sugerencias[0]["area_nombre"]} '
            f'({sugerencias[0]["tanque"]["capacidad_litros"]:.0f}L).'
        ),
    })


# ════════════════════════════════════════════════════════════════════════
# AUTO-ASIGNACIÓN IA · área + envasado + operarios + limpieza mismo día
# ════════════════════════════════════════════════════════════════════════
# Sebastián (1-may-2026): "TODOS rotan, queden limpias el mismo día, IA
# que sepa qué usar — si producción 200kg debe decir producción donde está
# marmita 250 litros, si lo haces automático sería maravilloso".


def _siguiente_operario_rotando(c, rol, candidatos_ids):
    """Round-robin estricto entre los operarios candidatos.

    Lee rotacion_operarios_state[rol], devuelve el próximo en la lista.
    Si el último estaba al final → vuelve al primero.
    Si el último ya no está en candidatos (operario inactivo) → primero.
    """
    if not candidatos_ids:
        return None
    try:
        row = c.execute(
            "SELECT ultimo_operario_id FROM rotacion_operarios_state WHERE rol=?",
            (rol,)
        ).fetchone()
        ultimo = row[0] if row else None
    except Exception:
        ultimo = None
    if not ultimo or ultimo not in candidatos_ids:
        return candidatos_ids[0]
    try:
        idx = candidatos_ids.index(ultimo)
        return candidatos_ids[(idx + 1) % len(candidatos_ids)]
    except ValueError:
        return candidatos_ids[0]


def _registrar_rotacion(c, rol, operario_id, user='auto-ia'):
    """Persiste la asignación para que la próxima iteración rote al siguiente."""
    try:
        c.execute("""
            INSERT INTO rotacion_operarios_state (rol, ultimo_operario_id, ultimo_asignado_at, actualizado_por)
            VALUES (?, ?, datetime('now'), ?)
            ON CONFLICT(rol) DO UPDATE SET
              ultimo_operario_id=excluded.ultimo_operario_id,
              ultimo_asignado_at=datetime('now'),
              actualizado_por=excluded.actualizado_por
        """, (rol, operario_id, user))
    except Exception:
        # Fallback si SQLite vieja sin ON CONFLICT
        c.execute(
            "UPDATE rotacion_operarios_state SET ultimo_operario_id=?, ultimo_asignado_at=datetime('now'), actualizado_por=? WHERE rol=?",
            (operario_id, user, rol)
        )


def _operarios_libres_en_dia(c, fecha_iso):
    """Operarios que NO están ya asignados a otra producción ese día.
    Sebastián 1-may-2026: excluye jefes de producción (Luis Enrique no rota)."""
    rows = c.execute("""
        SELECT id, nombre, COALESCE(apellido,''), rol_predeterminado
        FROM operarios_planta
        WHERE COALESCE(activo,1)=1
          AND COALESCE(es_jefe_produccion,0)=0
        ORDER BY id
    """).fetchall()
    todos = [(r[0], (r[1]+' '+r[2]).strip(), r[3] or '') for r in rows]
    # Excluir operarios ya asignados ese día
    ocupados_rows = c.execute("""
        SELECT operario_dispensacion_id, operario_elaboracion_id,
               operario_envasado_id, operario_acondicionamiento_id
        FROM produccion_programada
        WHERE date(fecha_programada) = ?
          AND COALESCE(estado, 'programado') != 'cancelado'
    """, (fecha_iso,)).fetchall()
    ocupados = set()
    for r in ocupados_rows:
        for x in r:
            if x: ocupados.add(x)
    return [(oid, nom, rol) for (oid, nom, rol) in todos if oid not in ocupados], todos


def _auto_asignar_operarios(c, produccion_id, fecha_iso, user='auto-ia'):
    """Asigna 4 roles ponderando preferencias + AVOID double-booking del día.
    Sebastián 1-may-2026 (round 2): 'mismo operario en 4 producciones distintas
    el mismo día' es físicamente imposible · ahora la IA evita asignar operarios
    que YA están en otras producciones del mismo día (por rol).

    Lógica:
    1. Pool = 4 operarios activos no-jefe
    2. Carga global: operarios_ya_usados_por_rol[rol] = set(op_ids) de OTRAS
       producciones del mismo día
    3. Para cada rol, intenta primero: pool - usados_en_esta_prod - globalmente_usados_para_rol
    4. Si vacío, fallback: pool - usados_en_esta_prod (acepta double-book)
    5. Aplica afinidad ponderada para escoger el final
    """
    import hashlib
    # Pool = operarios activos NO jefes. Se trae también fija_en_dispensacion
    # para enforzar la regla dura del CEO (Mayerlin SOLO dispensa).
    todos_rows = c.execute("""
        SELECT id, COALESCE(rol_predeterminado, ''),
               COALESCE(fija_en_dispensacion, 0)
        FROM operarios_planta
        WHERE COALESCE(activo, 1) = 1
          AND COALESCE(es_jefe_produccion, 0) = 0
        ORDER BY id
    """).fetchall()
    pool = [(r[0], (r[1] or '').strip().lower(), bool(r[2])) for r in todos_rows]
    if not pool:
        return None

    # Producto+fecha para hash determinístico
    prod_row = c.execute(
        "SELECT producto FROM produccion_programada WHERE id=?",
        (produccion_id,)
    ).fetchone()
    producto = (prod_row[0] or '') if prod_row else ''

    # ── Global day load: operarios ya asignados en OTRAS producciones del día
    # Sebastián 1-may-2026: evita 'Camilo en 4 producciones · Lunes'
    globalmente_usados = {
        'dispensacion': set(),
        'elaboracion': set(),
        'envasado': set(),
        'acondicionamiento': set(),
    }
    try:
        otras_rows = c.execute("""
            SELECT operario_dispensacion_id, operario_elaboracion_id,
                   operario_envasado_id, operario_acondicionamiento_id
            FROM produccion_programada
            WHERE date(fecha_programada) = ?
              AND id != ?
              AND COALESCE(estado, 'programado') NOT IN ('cancelado','completado')
        """, (fecha_iso, produccion_id)).fetchall()
        for r in otras_rows:
            if r[0]: globalmente_usados['dispensacion'].add(r[0])
            if r[1]: globalmente_usados['elaboracion'].add(r[1])
            if r[2]: globalmente_usados['envasado'].add(r[2])
            if r[3]: globalmente_usados['acondicionamiento'].add(r[3])
    except Exception as _e:
        log = logging.getLogger('inventario.programacion')
        log.warning('global day load fallo prod=%s fecha=%s: %s',
                    produccion_id, fecha_iso, _e)

    # Sebastián 1-may-2026 audit: leer AFINIDAD de tabla rol_afinidad_config
    # (migración 81). Antes hardcoded duplicado entre auto_plan.py y este archivo.
    try:
        from blueprints.auto_plan import _cargar_afinidad
        AFINIDAD = _cargar_afinidad(c)
    except Exception as _e:
        log = logging.getLogger('inventario.programacion')
        log.warning('_cargar_afinidad fallback hardcoded: %s', _e)
        AFINIDAD = {
            'dispensacion': {'dispensacion': 4, 'elaboracion': 1, 'envasado': 1,
                              'acondicionamiento': 1, 'todero': 2},
            'elaboracion':  {'dispensacion': 1, 'elaboracion': 4, 'envasado': 1,
                              'acondicionamiento': 1, 'todero': 2},
            'envasado':     {'envasado': 4, 'dispensacion': 1, 'elaboracion': 1,
                              'acondicionamiento': 1, 'todero': 2},
            'acondicionamiento': {'acondicionamiento': 4, 'envasado': 2, 'dispensacion': 1,
                                    'elaboracion': 1, 'todero': 2},
        }

    def _hash_rot(rol):
        s = f'{producto}|{fecha_iso}|{rol}'
        return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)

    # Pre-segmentación: fijos vs móviles
    pool_fijos = [(oid, rp) for (oid, rp, fija) in pool if fija]
    pool_moviles = [(oid, rp) for (oid, rp, fija) in pool if not fija]

    asignaciones = {}
    usados = set()
    for rol in ('dispensacion', 'elaboracion', 'envasado', 'acondicionamiento'):
        # Regla dura: roles ≠ dispensación NUNCA reciben operarios fija_en_dispensacion
        if rol == 'dispensacion':
            base_pool = pool_moviles + pool_fijos  # móviles primero, fijos como respaldo
            preferido_fijo = [c for c in pool_fijos if c[0] not in usados]
        else:
            base_pool = pool_moviles
            preferido_fijo = []

        # Para dispensación con fijo disponible: forzar fijo (rotación entre fijos por hash)
        if rol == 'dispensacion' and preferido_fijo:
            idx = _hash_rot(rol) % len(preferido_fijo)
            elegido = preferido_fijo[idx][0]
            asignaciones[rol] = elegido
            usados.add(elegido)
            globalmente_usados.get(rol, set()).add(elegido)
            _registrar_rotacion(c, rol, elegido, user)
            continue

        # 1ra preferencia: NO en esta producción Y NO en otras producciones (mismo rol)
        candidatos_strict = [
            (oid, rp) for (oid, rp) in base_pool
            if oid not in usados and oid not in globalmente_usados.get(rol, set())
        ]
        # Fallback 1: solo NO en esta producción
        candidatos_fallback = [(oid, rp) for (oid, rp) in base_pool if oid not in usados]
        # Fallback 2 (último recurso): base_pool completo
        candidatos = candidatos_strict or candidatos_fallback or base_pool
        if not candidatos:
            # Sin base_pool (caso pool=todos fijos y rol≠disp) → registrar warning,
            # NO romper la regla dura. Producción queda con NULL en este rol.
            log = logging.getLogger('inventario.programacion')
            log.warning('rol %s sin candidatos en prod=%s fecha=%s (todos fijos?)',
                        rol, produccion_id, fecha_iso)
            continue
        afin = AFINIDAD.get(rol, {})
        weighted = [(afin.get(rp, 1) if rp else 1, oid) for (oid, rp) in candidatos]
        total = sum(w for w, _ in weighted)
        if total <= 0:
            elegido = candidatos[_hash_rot(rol) % len(candidatos)][0]
        else:
            target = _hash_rot(rol) % total
            cumulative = 0
            elegido = weighted[0][1]
            for w, oid in weighted:
                cumulative += w
                if target < cumulative:
                    elegido = oid
                    break
        asignaciones[rol] = elegido
        usados.add(elegido)
        globalmente_usados.get(rol, set()).add(elegido)
        _registrar_rotacion(c, rol, elegido, user)

    # UPDATE produccion_programada
    c.execute("""
        UPDATE produccion_programada SET
          operario_dispensacion_id = COALESCE(?, operario_dispensacion_id),
          operario_elaboracion_id = COALESCE(?, operario_elaboracion_id),
          operario_envasado_id = COALESCE(?, operario_envasado_id),
          operario_acondicionamiento_id = COALESCE(?, operario_acondicionamiento_id)
        WHERE id = ?
    """, (asignaciones.get('dispensacion'),
          asignaciones.get('elaboracion'),
          asignaciones.get('envasado'),
          asignaciones.get('acondicionamiento'),
          produccion_id))
    return asignaciones


def _seleccionar_area_optima(c, lote_kg, fecha_iso, excluir_sucias=True):
    """IA: elige el ÁREA con tanque más chico que aguante el lote (eficiencia).

    Sebastián 1-may-2026: "si producción 200 kilos debe decir producción
    donde está marmita 250 litros".

    Returns: {area_codigo, area_id, tanque_codigo, capacidad_litros, score, razon}
              o None si nada candidato (incluye lote_kg<=0).
    """
    # Guard: lote inválido → no se puede seleccionar área (Sebastián test)
    try:
        lote_kg = float(lote_kg)
    except (TypeError, ValueError):
        return None
    if lote_kg <= 0:
        return None
    capacidad_min = lote_kg * 1.2  # 20% headroom

    # Tanques candidatos (suficiente capacidad)
    tanques = c.execute("""
        SELECT t.id, t.codigo, t.nombre, t.area_codigo, t.capacidad_litros,
               a.id as area_id, a.estado, a.requiere_limpieza_profunda,
               a.puede_producir
        FROM equipos_planta t
          LEFT JOIN areas_planta a ON a.codigo = t.area_codigo
        WHERE t.activo = 1
          AND t.tipo IN ('tanque','marmita','olla')
          AND t.capacidad_litros IS NOT NULL
          AND t.capacidad_litros >= ?
          AND COALESCE(a.activo, 1) = 1
          AND COALESCE(a.puede_producir, 0) = 1
        ORDER BY t.capacidad_litros ASC
    """, (capacidad_min,)).fetchall()

    # Producciones ya programadas en otras áreas ese día
    areas_ocupadas_hoy = set()
    try:
        rows = c.execute("""
            SELECT DISTINCT pp.area_id
            FROM produccion_programada pp
            WHERE date(pp.fecha_programada) = ?
              AND pp.area_id IS NOT NULL
              AND COALESCE(pp.estado, 'programado') NOT IN ('cancelado','completado')
        """, (fecha_iso,)).fetchall()
        areas_ocupadas_hoy = {r[0] for r in rows}
    except Exception:
        pass

    candidatos = []
    seen_area = set()
    for t in tanques:
        if t[3] in seen_area:
            continue  # ya tomamos el tanque más chico de esta área
        seen_area.add(t[3])
        if not t[5]:  # area_id None
            continue
        estado_area = t[6] or 'libre'
        if excluir_sucias and estado_area == 'sucia':
            continue
        # Evitar misma área el mismo día (otro lote)
        if t[5] in areas_ocupadas_hoy:
            continue
        utilizacion = (lote_kg / t[4]) * 100
        score = 0
        razones = []
        if utilizacion >= 60:
            score += 60
            razones.append(f"Tanque {t[4]:.0f}L · uso {utilizacion:.0f}% (eficiente)")
        elif utilizacion >= 30:
            score += 40
            razones.append(f"Tanque {t[4]:.0f}L · uso {utilizacion:.0f}%")
        else:
            score += 20
            razones.append(f"Tanque {t[4]:.0f}L · uso {utilizacion:.0f}% (sub-utilizado)")
        if estado_area == 'libre':
            score += 30
            razones.append('Sala libre')
        elif estado_area == 'limpiando':
            score += 10
            razones.append('Sala en limpieza · disponible al terminar')

        candidatos.append({
            'area_codigo': t[3],
            'area_id': t[5],
            'tanque_codigo': t[1],
            'tanque_nombre': t[2],
            'capacidad_litros': t[4],
            'estado_area': estado_area,
            'utilizacion_pct': round(utilizacion, 1),
            'score': score,
            'razones': razones,
        })

    candidatos.sort(key=lambda x: x['score'], reverse=True)
    return candidatos[0] if candidatos else None


def _envasado_sugerido(area_codigo):
    """Mapeo FAB → ENV (Sebastián + Alejandro)."""
    if area_codigo in ('FAB1', 'PROD1'):
        return 'ENV1'
    if area_codigo in ('FAB2', 'PROD2', 'FAB3', 'PROD3', 'FAB_FLOAT'):
        return 'ENV2'
    return None


def _crear_limpieza_post_produccion(c, area_id, area_codigo, fecha_produccion,
                                       producto, lote, user='auto-ia'):
    """Sebastián 1-may-2026: 'queden limpias el mismo día'.
    Crea entrada en limpieza_profunda_calendario para HOY (la fecha de la
    producción) para que mañana el área esté disponible.
    """
    if not area_codigo:
        return None
    # Verificar si ya hay limpieza creada para esta área+fecha
    try:
        existe = c.execute("""
            SELECT id FROM limpieza_profunda_calendario
            WHERE area_codigo = ? AND date(fecha) = ?
              AND estado IN ('pendiente','asignada','en_proceso')
            LIMIT 1
        """, (area_codigo, fecha_produccion)).fetchone()
        if existe:
            return existe[0]
    except Exception:
        pass

    # Asignar operario rotando (excluye jefes · Sebastián 1-may-2026)
    operarios = c.execute("""
        SELECT id FROM operarios_planta
        WHERE COALESCE(activo,1)=1
          AND COALESCE(es_jefe_produccion,0)=0
        ORDER BY id
    """).fetchall()
    pool = [r[0] for r in operarios]
    if not pool:
        return None
    op_id = _siguiente_operario_rotando(c, 'limpieza', pool)
    _registrar_rotacion(c, 'limpieza', op_id, user)

    # Lookup nombre operario
    op_nombre = ''
    if op_id:
        row = c.execute(
            "SELECT nombre || ' ' || COALESCE(apellido,'') FROM operarios_planta WHERE id=?",
            (op_id,)
        ).fetchone()
        if row: op_nombre = (row[0] or '').strip()

    razon = f'Auto post-producción {producto} (lote {lote or "—"}) · limpieza mismo día'
    try:
        c.execute("""
            INSERT INTO limpieza_profunda_calendario
              (fecha, area_codigo, asignado_a, estado, generado_por, razon_asignacion)
            VALUES (?, ?, ?, 'asignada', ?, ?)
        """, (fecha_produccion, area_codigo, op_nombre, user, razon))
        return c.lastrowid
    except Exception as e:
        log.warning(f'Crear limpieza auto fallo: {e}')
        return None


def _auto_asignar_produccion(c, produccion_id, user='auto-ia'):
    """Pipeline completo de auto-asignación IA para una producción:
      1. Selecciona área óptima por lote_kg (tanque más chico que aguante)
      2. Asigna área de envasado correspondiente
      3. Asigna operarios rotando (4 roles, todos rotan)
      4. Logs en auto_asignacion_log
    """
    prod = c.execute("""
        SELECT id, producto, fecha_programada, lotes,
               COALESCE(cantidad_kg, 0), area_id,
               operario_dispensacion_id, operario_elaboracion_id,
               operario_envasado_id, operario_acondicionamiento_id
        FROM produccion_programada
        WHERE id = ?
    """, (produccion_id,)).fetchone()
    if not prod:
        return {'ok': False, 'error': 'Producción no existe'}

    fecha_iso = prod[2][:10] if prod[2] else None
    lote_kg = float(prod[4] or 0)
    if lote_kg <= 0:
        # Inferir desde fórmula
        try:
            row = c.execute("""
                SELECT COALESCE(lote_size_kg,0) FROM formula_headers
                WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
            """, (prod[1],)).fetchone()
            if row:
                lote_kg = float(row[0] or 0) * int(prod[3] or 1)
        except Exception:
            pass
    if lote_kg <= 0:
        return {'ok': False, 'error': 'lote_kg desconocido (revisa fórmula)'}

    resultado = {'ok': True, 'produccion_id': produccion_id, 'cambios': []}

    # 1) Área óptima (si no la tiene)
    if not prod[5]:
        area = _seleccionar_area_optima(c, lote_kg, fecha_iso)
        if not area:
            # Reintentar incluyendo sucias (con limpieza inmediata)
            area = _seleccionar_area_optima(c, lote_kg, fecha_iso, excluir_sucias=False)
            if not area:
                return {'ok': False, 'error': f'Sin área disponible para {lote_kg:.0f}kg ese día'}
            else:
                resultado['cambios'].append('⚠️ Asignada área sucia, requiere limpieza primero')

        env_codigo = _envasado_sugerido(area['area_codigo'])
        env_id = None
        if env_codigo:
            row = c.execute("SELECT id FROM areas_planta WHERE codigo=?", (env_codigo,)).fetchone()
            if row: env_id = row[0]

        # Persistir área producción + área envasado (col agregada migración 76)
        try:
            c.execute(
                "UPDATE produccion_programada SET area_id=?, area_envasado_id=? WHERE id=?",
                (area['area_id'], env_id, produccion_id)
            )
        except sqlite3.OperationalError:
            # Fallback si col area_envasado_id aún no migrada
            c.execute("UPDATE produccion_programada SET area_id=? WHERE id=?",
                      (area['area_id'], produccion_id))

        resultado['area'] = area
        resultado['area_envasado'] = {'codigo': env_codigo, 'id': env_id}
        resultado['cambios'].append(
            f"Área asignada: {area['area_codigo']} (tanque {area['tanque_codigo']} · "
            f"{area['capacidad_litros']:.0f}L · uso {area['utilizacion_pct']}%)"
            + (f" → envasado {env_codigo}" if env_codigo else "")
        )

    # 2) Operarios rotando
    # Sebastián 1-may-2026: detectar asignaciones malas (jefes asignados,
    # duplicados intra-producción) y forzar reasignación limpia.
    sin_ops = not (prod[6] or prod[7] or prod[8] or prod[9])
    necesita_reasignar = sin_ops
    if not sin_ops:
        ops_actuales = [o for o in (prod[6], prod[7], prod[8], prod[9]) if o]
        # Hay duplicados?
        if len(ops_actuales) != len(set(ops_actuales)):
            necesita_reasignar = True
            resultado['cambios'].append('⚠️ Reasignando: operarios duplicados detectados')
        else:
            # Hay algún jefe entre los asignados?
            jefes_asignados = c.execute(
                f"SELECT id FROM operarios_planta WHERE id IN ({','.join(['?']*len(ops_actuales))}) AND COALESCE(es_jefe_produccion,0)=1",
                ops_actuales
            ).fetchall()
            if jefes_asignados:
                necesita_reasignar = True
                resultado['cambios'].append('⚠️ Reasignando: jefe asignado como operario (Luis Enrique no rota)')
        if necesita_reasignar:
            # NULL los operarios para que _auto_asignar_operarios los repueble
            c.execute("""
                UPDATE produccion_programada SET
                  operario_dispensacion_id = NULL,
                  operario_elaboracion_id = NULL,
                  operario_envasado_id = NULL,
                  operario_acondicionamiento_id = NULL
                WHERE id = ?
            """, (produccion_id,))
    if necesita_reasignar:
        asigns = _auto_asignar_operarios(c, produccion_id, fecha_iso, user)
        if asigns:
            # Lookup nombres
            ids = [v for v in asigns.values() if v]
            nombres_map = {}
            if ids:
                placeholders = ','.join(['?'] * len(ids))
                rows = c.execute(
                    f"SELECT id, nombre || ' ' || COALESCE(apellido,'') FROM operarios_planta WHERE id IN ({placeholders})",
                    ids
                ).fetchall()
                nombres_map = {r[0]: (r[1] or '').strip() for r in rows}
            asigns_nom = {rol: nombres_map.get(oid, f'#{oid}') for rol, oid in asigns.items()}
            resultado['operarios'] = asigns_nom
            resultado['cambios'].append(
                'Operarios asignados (rotación): ' +
                ' · '.join(f'{k}: {v}' for k, v in asigns_nom.items())
            )

    # 3) Log
    try:
        import json as _json
        c.execute("""
            INSERT INTO auto_asignacion_log
              (produccion_id, ejecutado_por, area_asignada, tanque_asignado,
               area_envasado_asignada, operarios_json, score, razon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            produccion_id, user,
            resultado.get('area', {}).get('area_codigo'),
            resultado.get('area', {}).get('tanque_codigo'),
            resultado.get('area_envasado', {}).get('codigo'),
            _json.dumps(resultado.get('operarios', {})),
            resultado.get('area', {}).get('score'),
            ' | '.join(resultado.get('cambios', [])),
        ))
    except Exception:
        pass

    return resultado


@bp.route('/api/planta/estado-salas-vivo', methods=['GET'])
def estado_salas_vivo():
    """Estado live de las áreas de producción + envasado.
    Sebastián 1-may-2026: vista en vivo de qué pasa en planta hoy.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    fecha_hoy = datetime.now().date()
    fecha_man = fecha_hoy + timedelta(days=1)

    salas = c.execute("""
        SELECT a.id, a.codigo, a.nombre, a.tipo, a.estado,
               a.requiere_limpieza_profunda, a.ultima_limpieza_profunda,
               a.puede_producir, a.puede_envasar
        FROM areas_planta a
        WHERE a.activo=1 AND a.tipo='produccion'
        ORDER BY a.orden, a.codigo
    """).fetchall()

    out = []
    for s in salas:
        sala = {
            'id': s[0], 'codigo': s[1], 'nombre': s[2],
            'estado': s[4] or 'libre',
            'requiere_limpieza_profunda': bool(s[5]),
            'ultima_limpieza_profunda': s[6],
            'puede_producir': bool(s[7]),
            'puede_envasar': bool(s[8]),
        }
        # Producción actual o próxima
        prod = c.execute("""
            SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
                   COALESCE(pp.cantidad_kg,0), pp.estado,
                   o1.nombre as op_disp, o2.nombre as op_elab,
                   o3.nombre as op_env
            FROM produccion_programada pp
              LEFT JOIN operarios_planta o1 ON o1.id = pp.operario_dispensacion_id
              LEFT JOIN operarios_planta o2 ON o2.id = pp.operario_elaboracion_id
              LEFT JOIN operarios_planta o3 ON o3.id = pp.operario_envasado_id
            WHERE pp.area_id = ?
              AND date(pp.fecha_programada) >= ?
              AND date(pp.fecha_programada) <= ?
              AND COALESCE(pp.estado, 'programado') NOT IN ('completado', 'cancelado')
            ORDER BY pp.fecha_programada ASC LIMIT 1
        """, (s[0], fecha_hoy.isoformat(), fecha_man.isoformat())).fetchall()
        if prod:
            p = prod[0]
            sala['produccion'] = {
                'id': p[0], 'producto': p[1], 'fecha': p[2][:10] if p[2] else '',
                'lotes': p[3], 'kg': p[4], 'estado': p[5],
                'op_dispensacion': p[6] or '',
                'op_elaboracion': p[7] or '',
                'op_envasado': p[8] or '',
            }
        else:
            sala['produccion'] = None
        # Limpieza pendiente
        try:
            limp = c.execute("""
                SELECT id, fecha, asignado_a, estado, razon_asignacion
                FROM limpieza_profunda_calendario
                WHERE area_codigo = ?
                  AND date(fecha) >= ?
                  AND estado IN ('pendiente','asignada','en_proceso')
                ORDER BY fecha ASC LIMIT 1
            """, (s[1], fecha_hoy.isoformat())).fetchone()
            if limp:
                sala['limpieza_pendiente'] = {
                    'id': limp[0], 'fecha': limp[1], 'asignado_a': limp[2] or '',
                    'estado': limp[3], 'razon': limp[4] or '',
                }
            else:
                sala['limpieza_pendiente'] = None
        except Exception:
            sala['limpieza_pendiente'] = None
        # Tanque más grande de la sala (info)
        try:
            tan = c.execute("""
                SELECT codigo, nombre, capacidad_litros
                FROM equipos_planta
                WHERE area_codigo=? AND activo=1
                  AND tipo IN ('tanque','marmita','olla')
                ORDER BY capacidad_litros DESC LIMIT 1
            """, (s[1],)).fetchone()
            if tan:
                sala['tanque_principal'] = {
                    'codigo': tan[0], 'nombre': tan[1], 'litros': tan[2]
                }
        except Exception:
            pass
        out.append(sala)

    return jsonify({
        'fecha_hoy': fecha_hoy.isoformat(),
        'salas': out,
        'total': len(out),
        'libres': sum(1 for s in out if s['estado'] == 'libre'),
        'ocupadas': sum(1 for s in out if s['estado'] == 'ocupada'),
        'sucias': sum(1 for s in out if s['estado'] == 'sucia'),
        'limpiando': sum(1 for s in out if s['estado'] == 'limpiando'),
    })


@bp.route('/api/planta/auto-asignar/<int:prod_id>', methods=['POST'])
def auto_asignar_endpoint(prod_id):
    """Auto-asigna área + envasado + operarios para 1 producción específica."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', 'manual')
    conn = get_db(); c = conn.cursor()
    try:
        resultado = _auto_asignar_produccion(c, prod_id, user)
        if resultado.get('ok'):
            conn.commit()
        return jsonify(resultado)
    except Exception as e:
        try: conn.rollback()
        except Exception as _r:
            logging.getLogger('programacion').debug('rollback no aplicable: %s', _r)
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/planta/auto-asignar-pendientes', methods=['POST'])
def auto_asignar_pendientes():
    """Recorre producciones próximos N días sin área/operarios y auto-asigna.

    Sebastián 1-may-2026: "haz todo automático".
    Acepta sesión o ?clave=AUTO_PLAN_CRON_KEY para uso interno.
    Body opcional: {dias: 7}
    """
    clave_cron = request.args.get('clave', '') or (request.json or {}).get('clave', '')
    clave_esperada = os.environ.get('AUTO_PLAN_CRON_KEY', '')
    es_cron = bool(clave_esperada and clave_cron == clave_esperada)
    if not es_cron and 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    user = 'cron-auto-asignar' if es_cron else session.get('compras_user', 'manual')
    d = request.json or {}
    dias = int(d.get('dias', 7))
    conn = get_db(); c = conn.cursor()
    fecha_hoy = datetime.now().date()
    fecha_max = fecha_hoy + timedelta(days=dias)

    pendientes = c.execute("""
        SELECT id FROM produccion_programada
        WHERE date(fecha_programada) >= ?
          AND date(fecha_programada) <= ?
          AND COALESCE(estado, 'programado') NOT IN ('completado', 'cancelado')
          AND (area_id IS NULL
               OR (operario_dispensacion_id IS NULL
                   AND operario_elaboracion_id IS NULL
                   AND operario_envasado_id IS NULL))
        ORDER BY fecha_programada ASC
    """, (fecha_hoy.isoformat(), fecha_max.isoformat())).fetchall()

    procesadas = []
    errores = []
    for (prod_id,) in pendientes:
        res = _auto_asignar_produccion(c, prod_id, user)
        if res.get('ok'):
            procesadas.append({'id': prod_id, 'cambios': res.get('cambios', [])})
        else:
            errores.append({'id': prod_id, 'error': res.get('error')})

    conn.commit()
    return jsonify({
        'ok': True,
        'fecha_hoy': fecha_hoy.isoformat(),
        'horizonte_dias': dias,
        'pendientes_evaluadas': len(pendientes),
        'procesadas': procesadas,
        'errores': errores,
        'mensaje': f'✅ {len(procesadas)} producciones auto-asignadas, {len(errores)} con error',
    })


# ════════════════════════════════════════════════════════════════════════
# PLANTA INTELIGENTE — FASE 2: Motor de Gates (Pre-Flight Checks)
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "programado un producto dice donde como, le dice
# inteligentemente area sucia confirmar limpieza confirmar tal y tal cosa".
# Antes de iniciar produccion, se corren N validaciones automaticas y se
# devuelve qué falta. Cada gate tiene status (ok/warn/blocker), mensaje y
# accion sugerida.

def _gate_sala_asignada(produccion, conn):
    """Gate: la producción tiene un área asignada."""
    if not produccion['area_id']:
        return {
            'gate': 'sala_asignada',
            'status': 'blocker',
            'titulo': 'Sala sin asignar',
            'mensaje': 'Esta producción no tiene un área asignada. Usa "Sugerir área" o asigna manualmente.',
            'accion': 'asignar_area',
        }
    area = conn.execute(
        "SELECT codigo, nombre, estado, puede_producir, activo FROM areas_planta WHERE id=?",
        (produccion['area_id'],)
    ).fetchone()
    if not area:
        return {'gate': 'sala_asignada', 'status': 'blocker',
                'titulo': 'Sala inválida', 'mensaje': f'area_id={produccion["area_id"]} no existe',
                'accion': 'asignar_area'}
    if not area[4]:
        return {'gate': 'sala_asignada', 'status': 'blocker',
                'titulo': 'Sala desactivada',
                'mensaje': f'{area[1]} está desactivada en areas_planta',
                'accion': 'asignar_area'}
    if not area[3]:
        return {'gate': 'sala_asignada', 'status': 'warn',
                'titulo': 'Sala no es de producción',
                'mensaje': f'{area[1]} no tiene puede_producir=1 (es área de apoyo)',
                'accion': None}
    return {
        'gate': 'sala_asignada',
        'status': 'ok',
        'titulo': f'Sala: {area[1]}',
        'mensaje': f'Estado actual: {area[2]}',
        'accion': None,
        'meta': {'area_codigo': area[0], 'area_nombre': area[1], 'estado': area[2]},
    }


def _gate_sala_libre(produccion, conn):
    """Gate: la sala no está ocupada por OTRA producción en curso."""
    if not produccion['area_id']:
        return None  # Sin sala no aplica este check
    area = conn.execute(
        "SELECT codigo, nombre, estado FROM areas_planta WHERE id=?",
        (produccion['area_id'],)
    ).fetchone()
    if not area:
        return None
    estado = area[2] or 'libre'
    if estado == 'libre':
        return {'gate': 'sala_libre', 'status': 'ok',
                'titulo': 'Sala libre', 'mensaje': 'Sin producción en curso',
                'accion': None}
    if estado == 'mantenimiento':
        return {'gate': 'sala_libre', 'status': 'blocker',
                'titulo': 'Sala en mantenimiento',
                'mensaje': f'{area[1]} marcada en mantenimiento — espera o cambia de sala',
                'accion': 'cambiar_estado'}
    if estado == 'ocupada':
        # Buscar qué producción tiene en curso
        otra = conn.execute("""
            SELECT id, producto FROM produccion_programada
            WHERE area_id=? AND id != ? AND estado IN ('en_proceso','pendiente')
              AND inicio_real_at IS NOT NULL AND fin_real_at IS NULL
            LIMIT 1
        """, (produccion['area_id'], produccion['id'])).fetchone()
        if otra:
            return {'gate': 'sala_libre', 'status': 'blocker',
                    'titulo': 'Sala ocupada',
                    'mensaje': f'Producción en curso: {otra[1]} (id {otra[0]})',
                    'accion': 'esperar_o_cambiar'}
    return {'gate': 'sala_libre', 'status': 'warn',
            'titulo': f'Estado sala: {estado}',
            'mensaje': 'Verifica el estado antes de iniciar',
            'accion': None}


def _gate_arrastre_pigmento(produccion, conn):
    """Gate: detecta arrastre de producto con pigmento al siguiente producto claro.
    Sebastian (30-abr-2026): pigmento → claro = limpieza profunda obligatoria."""
    if not produccion.get('area_id'):
        return None
    # Producto actual: ¿tiene perfil de riesgo?
    perfil_actual = conn.execute("""
        SELECT tiene_pigmento, color_descripcion, riesgo_arrastre_pct
        FROM producto_perfil_riesgo
        WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
    """, (produccion['producto'],)).fetchone()
    pigmento_actual = bool(perfil_actual[0]) if perfil_actual else False

    # Última producción en la misma sala antes de ESTA
    prev = conn.execute("""
        SELECT pp.producto, pp.fecha_programada
        FROM produccion_programada pp
        WHERE pp.area_id = ?
          AND pp.id != ?
          AND pp.fecha_programada < COALESCE(?, date('now', '+1 days'))
          AND pp.estado IN ('completado','en_proceso')
        ORDER BY pp.fecha_programada DESC LIMIT 1
    """, (produccion['area_id'], produccion['id'], produccion.get('fecha_programada'))).fetchone()
    if not prev:
        return None
    perfil_prev = conn.execute("""
        SELECT tiene_pigmento, color_descripcion, riesgo_arrastre_pct
        FROM producto_perfil_riesgo
        WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
    """, (prev[0],)).fetchone()
    if not perfil_prev:
        return None
    pigmento_prev = bool(perfil_prev[0])
    riesgo_prev = perfil_prev[2] or 0

    # Caso crítico: previo tenía pigmento Y actual no
    if pigmento_prev and not pigmento_actual and riesgo_prev >= 50:
        return {'gate': 'arrastre_pigmento', 'status': 'blocker',
                'titulo': '🎨 Riesgo de arrastre',
                'mensaje': f'Producto previo "{prev[0]}" tiene pigmento ({perfil_prev[1] or ""}). Limpieza profunda obligatoria antes de iniciar.',
                'accion': 'confirmar_limpieza',
                'meta': {'producto_previo': prev[0], 'fecha_previo': prev[1], 'riesgo_pct': riesgo_prev}}
    if pigmento_prev and not pigmento_actual and riesgo_prev >= 25:
        return {'gate': 'arrastre_pigmento', 'status': 'warn',
                'titulo': '🎨 Posible arrastre',
                'mensaje': f'Producto previo "{prev[0]}" pudo dejar residuo. Confirmar limpieza intermedia.',
                'accion': 'confirmar_limpieza'}
    return None


def _gate_sala_limpia(produccion, conn):
    """Gate: la sala tuvo limpieza profunda en los últimos 7 días.
    Sebastian (30-abr-2026): "area sucia confirmar limpieza"."""
    if not produccion['area_id']:
        return None
    area = conn.execute("""
        SELECT codigo, nombre, requiere_limpieza_profunda, ultima_limpieza_profunda
        FROM areas_planta WHERE id=?
    """, (produccion['area_id'],)).fetchone()
    if not area or not area[2]:
        # No requiere limpieza profunda → ok
        return {'gate': 'sala_limpia', 'status': 'ok',
                'titulo': 'Limpieza N/A',
                'mensaje': 'Esta área no requiere limpieza profunda registrada',
                'accion': None}
    # Buscar último evento de limpieza en area_eventos
    last_evt = conn.execute("""
        SELECT ts FROM area_eventos
        WHERE area_id=? AND tipo IN ('fin_limpieza','inicio_limpieza')
        ORDER BY ts DESC LIMIT 1
    """, (produccion['area_id'],)).fetchone()
    last_iso = (last_evt[0] if last_evt else None) or area[3]
    if not last_iso:
        return {'gate': 'sala_limpia', 'status': 'warn',
                'titulo': 'Sin registro de limpieza profunda',
                'mensaje': 'No hay evidencia de limpieza profunda — confirma antes de iniciar',
                'accion': 'confirmar_limpieza'}
    try:
        from datetime import datetime as _dt
        last_dt = _dt.fromisoformat((last_iso or '').replace('Z', '').split('.')[0].replace('T', ' ').strip())
        dias = (_dt.now() - last_dt).days
    except Exception:
        return {'gate': 'sala_limpia', 'status': 'warn',
                'titulo': 'Fecha de limpieza inválida',
                'mensaje': last_iso, 'accion': 'confirmar_limpieza'}
    if dias <= 7:
        return {'gate': 'sala_limpia', 'status': 'ok',
                'titulo': f'Limpieza hace {dias}d',
                'mensaje': f'Última limpieza profunda: {last_iso[:16]}',
                'accion': None}
    if dias <= 14:
        return {'gate': 'sala_limpia', 'status': 'warn',
                'titulo': f'Limpieza hace {dias}d (>7d)',
                'mensaje': 'Considera una limpieza profunda antes de iniciar',
                'accion': 'confirmar_limpieza'}
    return {'gate': 'sala_limpia', 'status': 'blocker',
            'titulo': f'Limpieza hace {dias}d (>14d)',
            'mensaje': 'Limpieza profunda obligatoria antes de iniciar',
            'accion': 'confirmar_limpieza'}


def _gate_mp_disponibles(produccion, conn):
    """Gate: hay suficientes MP para el lote.
    Reusa la lógica de listo-producir."""
    producto = produccion['producto']
    lotes = produccion['lotes'] or 1
    fh = conn.execute(
        "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    if not fh:
        return {'gate': 'mp_disponibles', 'status': 'warn',
                'titulo': 'Producto sin fórmula',
                'mensaje': f'"{producto}" no tiene fórmula registrada',
                'accion': 'crear_formula'}
    items = conn.execute("""
        SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
               COALESCE(fi.cantidad_g_por_lote, 0) as cant_lote_g
        FROM formula_items fi
        WHERE UPPER(TRIM(fi.producto_nombre))=UPPER(TRIM(?))
    """, (producto,)).fetchall()
    if not items:
        return {'gate': 'mp_disponibles', 'status': 'warn',
                'titulo': 'Fórmula sin items',
                'mensaje': 'La fórmula no tiene materiales registrados',
                'accion': 'completar_formula'}
    deficit = []
    justo = []
    for mat_id, mat_nom, pct, cant_lote_g in items:
        req_g = (cant_lote_g or 0) * lotes if cant_lote_g else (pct or 0) / 100.0 * (fh[0] or 0) * 1000 * lotes
        # Audit zero-error 2-may-2026: usar helper canónico · excluye cuarentena
        disp_g = stock_mp_disponible(conn, mat_id)
        if disp_g < req_g:
            if disp_g >= req_g * 0.5:
                justo.append({'codigo': mat_id, 'nombre': mat_nom,
                              'requerido_g': round(req_g), 'disponible_g': round(disp_g)})
            else:
                deficit.append({'codigo': mat_id, 'nombre': mat_nom,
                                'requerido_g': round(req_g), 'disponible_g': round(disp_g),
                                'faltante_g': round(req_g - disp_g)})
    if deficit:
        return {'gate': 'mp_disponibles', 'status': 'blocker',
                'titulo': f'Faltan {len(deficit)} MP',
                'mensaje': f'{len(deficit)} materiales en déficit · ' + ', '.join(d['nombre'] for d in deficit[:3]),
                'accion': 'crear_tareas_compra',
                'meta': {'deficit': deficit, 'justo': justo}}
    if justo:
        return {'gate': 'mp_disponibles', 'status': 'warn',
                'titulo': f'{len(justo)} MP justos',
                'mensaje': f'{len(justo)} materiales con stock <100% del requerido (≥50%)',
                'accion': None,
                'meta': {'justo': justo}}
    return {'gate': 'mp_disponibles', 'status': 'ok',
            'titulo': 'MP suficientes',
            'mensaje': f'{len(items)} materiales disponibles',
            'accion': None}


def _gate_envases_listos(produccion, conn):
    """Gate: hay envases (MEE) suficientes para la presentación elegida."""
    producto = produccion['producto']
    # Buscar presentaciones del producto
    pres = conn.execute("""
        SELECT presentacion_codigo, etiqueta, envase_codigo, factor_g_por_unidad
        FROM producto_presentaciones
        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND activo=1
    """, (producto,)).fetchall()
    if not pres:
        return {'gate': 'envases_listos', 'status': 'warn',
                'titulo': 'Sin presentaciones',
                'mensaje': f'"{producto}" no tiene presentaciones definidas (Fase 0)',
                'accion': 'definir_presentaciones'}
    # Para esta version: si hay presentación con envase_codigo, buscar stock en maestro_mee
    items_pres = []
    falta_envase = []
    for p_code, etiqueta, env_code, factor in pres:
        if not env_code:
            items_pres.append({'presentacion': etiqueta, 'envase': None,
                               'mensaje': 'Sin código de envase asignado'})
            continue
        # Buscar stock en maestro_mee
        mee = conn.execute(
            "SELECT stock_actual, nombre FROM maestro_mee WHERE codigo=?", (env_code,)
        ).fetchone()
        stock = (mee[0] if mee else 0) or 0
        nombre_mee = (mee[1] if mee else '') or env_code
        items_pres.append({'presentacion': etiqueta, 'envase': env_code,
                           'envase_nombre': nombre_mee, 'stock': stock})
        if stock <= 0:
            falta_envase.append(f'{etiqueta} ({env_code})')
    if falta_envase:
        return {'gate': 'envases_listos', 'status': 'warn',
                'titulo': f'Stock 0 en {len(falta_envase)} envase(s)',
                'mensaje': ', '.join(falta_envase[:3]),
                'accion': 'verificar_stock_mee',
                'meta': {'items': items_pres}}
    return {'gate': 'envases_listos', 'status': 'ok',
            'titulo': f'{len(pres)} presentación(es) OK',
            'mensaje': 'Envases con stock disponible',
            'accion': None,
            'meta': {'items': items_pres}}


def _gate_operarios(produccion, conn):
    """Gate: hay operarios asignados (al menos elaboración)."""
    asignados = []
    if produccion['operario_dispensacion_id']:
        asignados.append('dispensación')
    if produccion['operario_elaboracion_id']:
        asignados.append('elaboración')
    if produccion['operario_envasado_id']:
        asignados.append('envasado')
    if produccion['operario_acondicionamiento_id']:
        asignados.append('acondicionamiento')
    if not asignados:
        return {'gate': 'operarios', 'status': 'blocker',
                'titulo': 'Sin operarios asignados',
                'mensaje': 'Asigna al menos un operario por fase',
                'accion': 'asignar_operarios'}
    if 'elaboración' not in asignados:
        return {'gate': 'operarios', 'status': 'warn',
                'titulo': f'{len(asignados)}/4 fases con operario',
                'mensaje': 'Falta operario para elaboración',
                'accion': 'asignar_operarios'}
    return {'gate': 'operarios', 'status': 'ok',
            'titulo': f'{len(asignados)}/4 fases asignadas',
            'mensaje': ', '.join(asignados),
            'accion': None}


@bp.route('/api/planta/preflight/<int:produccion_id>', methods=['GET'])
def planta_preflight(produccion_id):
    """Motor de gates pre-flight.

    Sebastian (30-abr-2026): "programado un producto dice donde como,
    le dice inteligentemente area sucia confirmar limpieza confirmar
    tal y tal cosa". Devuelve checks ordenados (blockers primero) con
    status (ok/warn/blocker), mensaje y acción sugerida.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    pp = c.execute("""
        SELECT id, producto, fecha_programada, lotes, estado, area_id,
               operario_dispensacion_id, operario_elaboracion_id,
               operario_envasado_id, operario_acondicionamiento_id,
               inicio_real_at, fin_real_at, cantidad_kg
        FROM produccion_programada WHERE id=?
    """, (produccion_id,)).fetchone()
    if not pp:
        return jsonify({'error': 'Producción no existe'}), 404
    cols = ['id', 'producto', 'fecha_programada', 'lotes', 'estado', 'area_id',
            'operario_dispensacion_id', 'operario_elaboracion_id',
            'operario_envasado_id', 'operario_acondicionamiento_id',
            'inicio_real_at', 'fin_real_at', 'cantidad_kg']
    produccion = dict(zip(cols, pp))

    gates = []
    for fn in (_gate_sala_asignada, _gate_sala_libre, _gate_arrastre_pigmento,
               _gate_sala_limpia, _gate_mp_disponibles, _gate_envases_listos,
               _gate_operarios):
        try:
            g = fn(produccion, c)
            if g:
                gates.append(g)
        except Exception as e:
            gates.append({'gate': fn.__name__, 'status': 'warn',
                          'titulo': 'Error en check', 'mensaje': str(e), 'accion': None})

    # Resumen general
    n_block = sum(1 for g in gates if g['status'] == 'blocker')
    n_warn  = sum(1 for g in gates if g['status'] == 'warn')
    n_ok    = sum(1 for g in gates if g['status'] == 'ok')
    if n_block:
        listo = False
        veredicto = f'⛔ NO PUEDE INICIAR — {n_block} bloqueante(s)'
    elif n_warn:
        listo = True
        veredicto = f'⚠ Puede iniciar con precaución — {n_warn} advertencia(s)'
    else:
        listo = True
        veredicto = '✅ Listo para iniciar'
    # Ordenar: blockers primero, luego warns, luego ok
    orden = {'blocker': 0, 'warn': 1, 'ok': 2}
    gates.sort(key=lambda g: orden.get(g['status'], 3))

    return jsonify({
        'produccion_id': produccion_id,
        'producto': produccion['producto'],
        'estado': produccion['estado'],
        'lotes': produccion['lotes'],
        'fecha_programada': produccion['fecha_programada'],
        'gates': gates,
        'resumen': {'ok': n_ok, 'warn': n_warn, 'blocker': n_block, 'total': len(gates)},
        'listo': listo,
        'veredicto': veredicto,
    })


# ════════════════════════════════════════════════════════════════════════
# PLANTA INTELIGENTE — FASE 3: Triggers automáticos
# ════════════════════════════════════════════════════════════════════════
# Sebastian + Alejandro (30-abr-2026):
#  D. Envasado iniciado → muestra micro automática (deadline 5 días)
#  F. Resultado micro ok → entra a cola de liberación 1-2/día
#  C. Scheduler limpieza profunda L-Ma-J-V rotando 9 áreas

@bp.route('/api/planta/envasado/iniciar', methods=['POST'])
def planta_envasado_iniciar():
    """Operario marca el inicio de envasado. Triggers automáticos:
       1. Crea registro produccion_envasado
       2. Crea muestra micro pendiente con deadline = ahora + 5 días
       3. Crea entrada en cola_liberacion estado='esperando_micro'

    Body: {produccion_id*, lote*, presentacion_id?, presentacion_etiqueta?,
           unidades_planeadas?, envase_codigo?}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    prod_id = d.get('produccion_id')
    lote = (d.get('lote') or '').strip()
    if not prod_id or not lote:
        return jsonify({'error': 'produccion_id y lote requeridos'}), 400
    conn = get_db(); c = conn.cursor()
    pp = c.execute(
        "SELECT producto FROM produccion_programada WHERE id=?", (prod_id,)
    ).fetchone()
    if not pp:
        return jsonify({'error': 'Producción no existe'}), 404
    producto = pp[0]
    pres_etiqueta = (d.get('presentacion_etiqueta') or '').strip()
    pres_id = d.get('presentacion_id')
    if pres_id and not pres_etiqueta:
        pr = c.execute(
            "SELECT etiqueta, envase_codigo FROM producto_presentaciones WHERE id=?",
            (pres_id,)
        ).fetchone()
        if pr:
            pres_etiqueta = pr[0]
            if not d.get('envase_codigo'):
                d['envase_codigo'] = pr[1]
    # 1) Crear envasado
    cur = c.execute("""
        INSERT INTO produccion_envasado
          (produccion_id, producto_nombre, lote, presentacion_id,
           presentacion_etiqueta, unidades_planeadas, envase_codigo,
           iniciado_por, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'en_proceso')
    """, (prod_id, producto, lote, pres_id, pres_etiqueta or None,
          d.get('unidades_planeadas'),
          (d.get('envase_codigo') or None),
          user))
    envasado_id = cur.lastrowid
    # 2) Crear muestra micro pendiente con deadline 5 días
    deadline = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    # Insertamos un registro "marcador" (sin valor todavía) por cada microorganismo
    # estandar — pero para no inflar la BD, creamos UN solo marcador con
    # microorganismo='pendiente' que CC actualiza luego con cada análisis.
    try:
        cur2 = c.execute("""
            INSERT INTO calidad_micro_resultados
              (lote, producto, microorganismo, valor, estado, fecha_analisis,
               envasado_id, deadline_resultado)
            VALUES (?, ?, 'pendiente_recoleccion', NULL, 'pendiente', ?, ?, ?)
        """, (lote, producto, fecha_hoy, envasado_id, deadline))
        muestra_id = cur2.lastrowid
        c.execute("UPDATE produccion_envasado SET muestra_micro_id=? WHERE id=?",
                  (muestra_id, envasado_id))
    except Exception as e:
        # Si la columna no existe (esquema viejo), silenciar — el envasado igual
        # se crea, solo no se linkea muestra micro.
        muestra_id = None
    # 3) Cola de liberación
    c.execute("""
        INSERT INTO cola_liberacion
          (envasado_id, producto_nombre, lote, presentacion_etiqueta,
           unidades, fecha_envasado, fecha_min_liberacion, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'esperando_micro')
    """, (envasado_id, producto, lote, pres_etiqueta or None,
          d.get('unidades_planeadas'), fecha_hoy, deadline))
    audit_log(c, usuario=user, accion='INICIAR_ENVASADO', tabla='produccion_envasado',
              registro_id=envasado_id,
              despues={'producto': producto, 'lote': lote,
                       'presentacion': pres_etiqueta,
                       'unidades_planeadas': d.get('unidades_planeadas'),
                       'envase_codigo': d.get('envase_codigo')},
              detalle=f"Inició envasado lote {lote} ({producto})"
                      + (f" · {pres_etiqueta}" if pres_etiqueta else ""))
    conn.commit()
    return jsonify({
        'ok': True,
        'envasado_id': envasado_id,
        'muestra_micro_id': muestra_id,
        'deadline_resultado': deadline,
        'mensaje': f'Envasado iniciado. Muestra micro pendiente — deadline {deadline} (5 días).',
    })


@bp.route('/api/planta/envasado/<int:envasado_id>/terminar', methods=['POST'])
def planta_envasado_terminar(envasado_id):
    """Operario marca fin de envasado. Body: {unidades_envasadas, notas}.

    Sebastian (1-may-2026): "que coloquen cuanto fue y de alli mismo
    descuente automaticamente envases y demas del inventario". Al terminar
    envasado se descuentan envase/tapa/etiqueta del checklist usando la
    cantidad real envasada (proporcional al plan).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    cur = c.execute("""
        UPDATE produccion_envasado SET
          estado='terminado',
          terminado_at=datetime('now'),
          terminado_por=?,
          unidades_envasadas=COALESCE(?, unidades_envasadas),
          notas=COALESCE(?, notas)
        WHERE id=? AND estado='en_proceso'
    """, (user, d.get('unidades_envasadas'), d.get('notas'), envasado_id))
    if cur.rowcount == 0:
        return jsonify({'error': 'Envasado no encontrado o ya terminado'}), 404
    # Actualizar unidades en cola_liberacion si llegan
    if d.get('unidades_envasadas') is not None:
        c.execute(
            "UPDATE cola_liberacion SET unidades=? WHERE envasado_id=?",
            (d.get('unidades_envasadas'), envasado_id)
        )

    # ── Descuento MEE proporcional al envasado real (envase/tapa/etiqueta) ──
    descontados_mees = []
    try:
        env_row = c.execute("""
            SELECT produccion_id, lote, unidades_planeadas, unidades_envasadas
            FROM produccion_envasado WHERE id = ?
        """, (envasado_id,)).fetchone()
        if env_row:
            prod_id, lote_env, ud_plan, ud_env = env_row
            ud_env = int(ud_env or 0)
            if prod_id and ud_env > 0:
                descontados_mees = _descontar_mee_envasado(
                    c, prod_id, lote_env or '', ud_env,
                    int(ud_plan or 0), user
                )
    except Exception as e:
        log.warning(f'Descuento MEE envasado fallo (envasado_id={envasado_id}): {e}')

    audit_log(c, usuario=user, accion='TERMINAR_ENVASADO', tabla='produccion_envasado',
              registro_id=envasado_id,
              despues={'unidades_envasadas': d.get('unidades_envasadas'),
                       'notas': d.get('notas'),
                       'mees_descontados': len(descontados_mees)},
              detalle=f"Terminó envasado id={envasado_id}"
                      + (f" · {d.get('unidades_envasadas')} unidades" if d.get('unidades_envasadas') else ""))
    conn.commit()
    return jsonify({
        'ok': True,
        'envasado_id': envasado_id,
        'mees_descontados': descontados_mees,
        'total_mees': len(descontados_mees),
    })


@bp.route('/api/planta/cola-liberacion', methods=['GET'])
def planta_cola_liberacion():
    """Lista la cola de liberación. Querystring:
       ?estado=esperando_micro|listo_revisar|liberado|rechazado|todas (default activas)"""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    estado = (request.args.get('estado') or '').strip()
    conn = get_db(); c = conn.cursor()
    where = []
    params = []
    if estado in ('esperando_micro', 'listo_revisar', 'liberado', 'rechazado', 'reanalisis'):
        where.append("estado=?"); params.append(estado)
    elif estado != 'todas':
        # default: solo activas (no liberadas/rechazadas)
        where.append("estado IN ('esperando_micro','listo_revisar','reanalisis')")
    sql = "SELECT * FROM cola_liberacion"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_min_liberacion ASC, id ASC LIMIT 1000"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # Marcar listos_revisar los que ya pasaron deadline (auto-promoción)
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    for it in items:
        if it['estado'] == 'esperando_micro' and (it.get('fecha_min_liberacion') or '') <= fecha_hoy:
            c.execute(
                "UPDATE cola_liberacion SET estado='listo_revisar' WHERE id=?",
                (it['id'],)
            )
            it['estado'] = 'listo_revisar'
            it['_auto_promovido'] = True
    conn.commit()
    return jsonify({
        'items': items,
        'total': len(items),
        'listos_hoy': sum(1 for it in items if it['estado'] == 'listo_revisar'),
        'esperando': sum(1 for it in items if it['estado'] == 'esperando_micro'),
    })


@bp.route('/api/planta/cola-liberacion/<int:item_id>/disposicion', methods=['POST'])
def planta_cola_liberacion_disposicion(item_id):
    """QC/Alejandro decide la disposición del lote tras revisar el resultado micro.

    Decisión INVIMA crítica (Resolución 2214/2021 art. 10): liberación de
    producto terminado solo por Calidad/Admin con motivo si rechaza.

    Body: {disposicion: 'aprobado'|'rechazado'|'reanalizar', notas?}"""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin puede liberar lotes'}), 403
    d = request.json or {}
    disposicion = (d.get('disposicion') or '').strip()
    notas = (d.get('notas') or '').strip()
    if disposicion not in ('aprobado', 'rechazado', 'reanalizar'):
        return jsonify({'error': 'disposicion debe ser aprobado/rechazado/reanalizar'}), 400
    if disposicion == 'rechazado' and len(notas) < 10:
        return jsonify({'error': 'notas (≥10 chars) requeridas para rechazar lote'}), 400
    estado_nuevo = {
        'aprobado': 'liberado',
        'rechazado': 'rechazado',
        'reanalizar': 'reanalisis',
    }[disposicion]
    conn = get_db(); c = conn.cursor()
    # Capturar antes para audit log
    antes_row = c.execute(
        "SELECT producto_nombre, lote, estado, disposicion, unidades "
        "FROM cola_liberacion WHERE id=?", (item_id,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Item no encontrado'}), 404
    antes = dict(antes_row)
    c.execute("""
        UPDATE cola_liberacion SET
          disposicion=?, estado=?, aprobado_por=?, aprobado_at=datetime('now'),
          notas=COALESCE(?, notas)
        WHERE id=?
    """, (disposicion, estado_nuevo, user, notas or None, item_id))
    accion = {
        'aprobado': 'LIBERAR_LOTE_PT',
        'rechazado': 'RECHAZAR_LOTE_PT',
        'reanalizar': 'REANALIZAR_LOTE_PT',
    }[disposicion]
    audit_log(c, usuario=user, accion=accion, tabla='cola_liberacion',
              registro_id=item_id, antes=antes,
              despues={'disposicion': disposicion, 'estado': estado_nuevo,
                       'aprobado_por': user, 'notas': notas},
              detalle=f"{accion} lote {antes.get('lote','—')} ({antes.get('producto_nombre','')})"
                      + (f" · {notas}" if notas else ""))
    conn.commit()
    return jsonify({'ok': True, 'estado': estado_nuevo})


@bp.route('/api/planta/limpieza-profunda/calendario', methods=['GET'])
def planta_limpieza_calendario():
    """Lista programación de limpieza profunda. Querystring: ?dias=20 (default)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 20))
    except (TypeError, ValueError):
        dias = 20
    fecha_desde = datetime.now().strftime('%Y-%m-%d')
    fecha_hasta = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT lpc.*, ap.nombre as area_nombre
        FROM limpieza_profunda_calendario lpc
        LEFT JOIN areas_planta ap ON ap.codigo = lpc.area_codigo
        WHERE lpc.fecha BETWEEN ? AND ?
        ORDER BY lpc.fecha ASC, lpc.area_codigo
    """, (fecha_desde, fecha_hasta)).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # Cobertura de áreas: cuántas áreas tuvieron limpieza en los últimos 14d
    cobertura = c.execute("""
        SELECT area_codigo, MAX(fecha) as ultima
        FROM limpieza_profunda_calendario
        WHERE estado='completada' AND fecha >= date('now','-14 days')
        GROUP BY area_codigo
    """).fetchall()
    return jsonify({
        'items': items,
        'rango': {'desde': fecha_desde, 'hasta': fecha_hasta, 'dias': dias},
        'cobertura_14d': {r[0]: r[1] for r in cobertura},
    })


@bp.route('/api/planta/limpieza-profunda/generar', methods=['POST'])
def planta_limpieza_generar():
    """Genera cronograma rotativo L-Ma-J-V para los próximos N días.
    Brief K (Alejandro): rotar L-Ma-J-V cubriendo las 9 áreas, idealmente
    el área que se produjo el día anterior.

    Body: {dias?: int (default 20), reset?: bool (borrar pendientes y regenerar)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    try:
        dias = int(d.get('dias', 20))
    except (TypeError, ValueError):
        dias = 20
    conn = get_db(); c = conn.cursor()

    if d.get('reset'):
        c.execute(
            "DELETE FROM limpieza_profunda_calendario WHERE estado='programada' AND fecha >= date('now')"
        )

    # Obtener orden de rotación según última limpieza por área
    ultimas = c.execute("""
        SELECT codigo, ultima_limpieza_profunda
        FROM areas_planta
        WHERE codigo IN ({})
    """.format(','.join('?' for _ in _AREAS_LIMPIEZA_PROFUNDA)),
        _AREAS_LIMPIEZA_PROFUNDA
    ).fetchall()
    # Mapear código → días desde última limpieza (-1 si nunca)
    dias_por_area = {}
    for cod, ult in ultimas:
        if ult:
            try:
                last = datetime.fromisoformat((ult or '').split('.')[0].replace('T', ' '))
                dias_por_area[cod] = (datetime.now() - last).days
            except Exception:
                dias_por_area[cod] = 999
        else:
            dias_por_area[cod] = 999
    # Cola priorizada: las que llevan más sin limpiar primero
    cola = sorted(_AREAS_LIMPIEZA_PROFUNDA, key=lambda x: dias_por_area.get(x, 999), reverse=True)

    creadas = []
    skipped = []
    today = datetime.now().date()
    for offset in range(dias + 1):
        fecha = today + timedelta(days=offset)
        # Limpieza profunda solo L-Ma-J-V (excluye Mié=2, Sáb=5, Dom=6)
        if fecha.weekday() in (2, 5, 6):
            continue
        fecha_str = fecha.strftime('%Y-%m-%d')
        # Buscar área que se produjo el día anterior (preferencia)
        prev_str = (fecha - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_area = c.execute("""
            SELECT ap.codigo
            FROM produccion_programada pp
            LEFT JOIN areas_planta ap ON ap.id = pp.area_id
            WHERE date(pp.fecha_programada) = ? AND ap.codigo IN ({})
            ORDER BY pp.id DESC LIMIT 1
        """.format(','.join('?' for _ in _AREAS_LIMPIEZA_PROFUNDA)),
            [prev_str, *_AREAS_LIMPIEZA_PROFUNDA]
        ).fetchone()
        if prev_area and prev_area[0] in cola:
            elegida = prev_area[0]
            razon = f'Producción ayer en {elegida}'
            cola.remove(elegida)
            cola.append(elegida)  # mover al final para rotación
        else:
            elegida = cola[0]
            razon = f'Más antigua sin limpieza ({dias_por_area.get(elegida, 999)}d)'
            cola.append(cola.pop(0))
        try:
            c.execute("""
                INSERT INTO limpieza_profunda_calendario
                  (fecha, area_codigo, estado, generado_por, razon_asignacion)
                VALUES (?, ?, 'programada', ?, ?)
            """, (fecha_str, elegida, user, razon))
            creadas.append({'fecha': fecha_str, 'area': elegida, 'razon': razon})
        except sqlite3.IntegrityError:
            skipped.append({'fecha': fecha_str, 'area': elegida, 'motivo': 'ya existe'})
    conn.commit()
    return jsonify({
        'ok': True,
        'creadas': creadas,
        'skipped': skipped,
        'total_creadas': len(creadas),
    })


@bp.route('/api/planta/limpieza-profunda/<int:item_id>/completar', methods=['POST'])
def planta_limpieza_completar(item_id):
    """Operario marca limpieza completada. Actualiza también
    areas_planta.ultima_limpieza_profunda."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT area_codigo FROM limpieza_profunda_calendario WHERE id=?", (item_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'Item no existe'}), 404
    area_codigo = row[0]
    c.execute("""
        UPDATE limpieza_profunda_calendario SET
          estado='completada', terminado_at=datetime('now'), terminado_por=?,
          notas=COALESCE(?, notas)
        WHERE id=?
    """, (user, d.get('notas'), item_id))
    c.execute(
        "UPDATE areas_planta SET ultima_limpieza_profunda=datetime('now') WHERE codigo=?",
        (area_codigo,)
    )
    c.execute("""
        INSERT INTO area_eventos (area_id, tipo, usuario, nota)
        SELECT id, 'fin_limpieza', ?, ? FROM areas_planta WHERE codigo=?
    """, (user, d.get('notas') or 'Limpieza profunda programada', area_codigo))
    conn.commit()
    return jsonify({'ok': True, 'area': area_codigo})


# ════════════════════════════════════════════════════════════════════════
# PLANTA INTELIGENTE — FASE 4: Plan semanal + cascade aceptar-producción
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "programación de la semana entra mira lunes
# acido hialuronico, animus le quedan 20 dias estamos sobre lo que es...
# sale que alcanzan las materias primas que recuerda no es solo para ese
# producto siempre que calcula un producto suma los consumos de todas las
# programaciones previas a esa, entonces dice 20 dias sin alerta, si se
# esta vendiendo mas deberia generar alerta a compras gerencia y alejandro
# incluso correo... entonces lo selecciona le sale con la foto, y de una
# sale señalar envases, solicitar etiquetas, armado de goteros si requiere,
# aceptar produccion se dispone para realizar, entonces automaticamente
# pasa a que el sistema decida en que area se hace y genere todo".

def _calcular_mp_requerido(producto, lotes, conn):
    """Devuelve dict {material_id: gramos_requeridos} para una producción."""
    fh = conn.execute(
        "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    if not fh:
        return {}
    lote_kg = fh[0] or 0
    items = conn.execute("""
        SELECT material_id, porcentaje, COALESCE(cantidad_g_por_lote, 0)
        FROM formula_items
        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
    """, (producto,)).fetchall()
    out = {}
    for mat_id, pct, cant_lote in items:
        if cant_lote:
            out[mat_id] = (cant_lote or 0) * lotes
        else:
            out[mat_id] = (pct or 0) / 100.0 * lote_kg * 1000 * lotes
    return out


def _stock_mp(material_id, conn):
    """Stock total de MP · audit zero-error 2-may-2026.

    Wrapper sobre stock_mp_total para compatibilidad con código legacy. El
    plan_semanal usa total (incluye cuarentena) porque calcula consumos
    futuros · si llegan en QC a tiempo, contarán.
    """
    return stock_mp_total(conn, material_id)


@bp.route('/api/planta/cronograma-areas', methods=['GET'])
def planta_cronograma_areas():
    """Matriz semanal · 10 áreas × 5 días Lun-Vie con todas las fases.

    Vista que Alejandro pidió (programacion_mayo_areas.html). Auto-alimentada
    desde data existente:
      - FAB1/FYE2/FYE3 ← produccion_programada (sala PROD1/PROD2/PROD3)
      - ENV1/ENV2     ← produccion_envasado + produccion_programada (PROD4)
      - MICRO         ← calidad_micro_resultados (fecha_muestreo)
      - LIB           ← cola_liberacion (fecha_min_liberacion)
      - ACOND         ← acondicionamiento
      - ENTR          ← despachos (fecha)
      - LIMP          ← limpieza_profunda_calendario

    Query params:
      desde · YYYY-MM-DD del lunes (default: lunes de esta semana)

    Response:
      {
        rango: {desde, hasta, semana},
        days: ['Lun 04', ..., 'Vie 08'],
        areas: {
          fab1: [[{t,l,u}, ...], [], ...],   # 5 listas (Lun-Vie)
          fye2, fye3, env1, env2, micro, lib, acond, entr, limp: idem
        }
      }
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import datetime as _dt, timedelta as _td

    # Calcular lunes de la semana
    desde_param = (request.args.get('desde') or '').strip()
    if desde_param:
        try:
            d0 = _dt.strptime(desde_param[:10], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'desde inválido (YYYY-MM-DD)'}), 400
    else:
        hoy = _dt.now().date()
        d0 = hoy - _td(days=hoy.weekday())  # lunes
    # Avanzar a lunes si cae en mié/dom
    while d0.weekday() != 0:
        d0 = d0 - _td(days=1)
    fechas = [d0 + _td(days=i) for i in range(5)]  # Lun-Vie
    fechas_iso = [f.isoformat() for f in fechas]
    fechas_set = set(fechas_iso)
    desde_iso = fechas_iso[0]
    hasta_iso = fechas_iso[-1]

    days_labels_es = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie']
    days_labels = [f"{days_labels_es[i]} {fechas[i].strftime('%d')}" for i in range(5)]

    # Matriz inicializada · 10 áreas × 5 días
    areas_keys = ['fab1', 'fye2', 'fye3', 'env1', 'env2',
                  'micro', 'lib', 'acond', 'entr', 'limp']
    matriz = {k: [[] for _ in range(5)] for k in areas_keys}

    def _idx(fecha_iso):
        try:
            return fechas_iso.index(fecha_iso)
        except ValueError:
            return None

    def _add(area, idx, t, label, urgente=False):
        if idx is None: return
        chip = {'t': t, 'l': label}
        if urgente:
            chip['u'] = True
        matriz[area][idx].append(chip)

    conn = get_db(); c = conn.cursor()

    # ── FAB · produccion_programada con area_id mapeado a PROD1/2/3 ─────
    # Sala → fila de Alejandro:
    #   PROD1 → fab1
    #   PROD2 → fye2 (fase fab del día)
    #   PROD3 → fye3 (fase fab del día)
    #   PROD4 → env2 (sala dedicada a envasado en HTML de Alejandro)
    #   ENV1  → env1
    SALA_TO_FILA_FAB = {'PROD1': 'fab1', 'PROD2': 'fye2', 'PROD3': 'fye3',
                         'PROD4': 'env2'}
    try:
        rows = c.execute(f"""
            SELECT pp.fecha_programada, pp.producto, ap.codigo,
                   COALESCE(pp.observaciones,''),
                   COALESCE(pp.estado, 'pendiente')
            FROM produccion_programada pp
            LEFT JOIN areas_planta ap ON ap.id = pp.area_id
            WHERE pp.fecha_programada BETWEEN ? AND ?
              AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado')
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, producto, sala, obs, estado in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            fila = SALA_TO_FILA_FAB.get(sala or '', 'fab1')
            urgente = ('urg' in (obs or '').lower() or
                        'crítico' in (obs or '').lower() or
                        '⚡' in (obs or ''))
            _add(fila, idx, 'fab', producto, urgente)
    except Exception:
        pass

    # ── ENV · produccion_envasado (iniciado_at o terminado_at en rango) ─
    try:
        rows = c.execute(f"""
            SELECT date(COALESCE(iniciado_at, terminado_at, fecha_creacion)) as fecha,
                   producto_nombre, lote,
                   COALESCE(presentacion_etiqueta, ''),
                   COALESCE(estado, '')
            FROM produccion_envasado
            WHERE date(COALESCE(iniciado_at, terminado_at, fecha_creacion))
                  BETWEEN ? AND ?
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, producto, lote, presentacion, estado in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            label = f"{producto}\n{presentacion}" if presentacion else (producto or '')
            # Sin info de sala específica · van a env1 por default
            _add('env1', idx, 'env', label or 'Envasado')
    except Exception:
        pass

    # ── MICRO · calidad_micro_resultados (fecha_muestreo o fecha_analisis) ─
    try:
        rows = c.execute(f"""
            SELECT COALESCE(fecha_muestreo, fecha_analisis) as fecha,
                   producto_nombre, lote, deadline_resultado
            FROM calidad_micro_resultados
            WHERE COALESCE(fecha_muestreo, fecha_analisis) BETWEEN ? AND ?
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, producto, lote, deadline in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            label = (producto or 'Muestra MICRO')
            if deadline:
                label += f"\n→ libera {deadline[5:10].replace('-','/')}"
            _add('micro', idx, 'micro', label)
    except Exception:
        pass

    # ── LIB · cola_liberacion (fecha_min_liberacion en rango) ───────────
    try:
        rows = c.execute(f"""
            SELECT fecha_min_liberacion, producto_nombre, lote, estado
            FROM cola_liberacion
            WHERE fecha_min_liberacion BETWEEN ? AND ?
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, producto, lote, estado in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            label = f"{producto}\n({lote or 'sin-lote'})" if producto else f'Lote {lote}'
            _add('lib', idx, 'lib', label)
    except Exception:
        pass

    # ── ACOND · acondicionamiento (creado_en o fecha_inicio) ───────────
    try:
        rows = c.execute(f"""
            SELECT date(COALESCE(creado_en, datetime('now'))) as fecha,
                   producto, lote, COALESCE(estado, '')
            FROM acondicionamiento
            WHERE date(COALESCE(creado_en, datetime('now')))
                  BETWEEN ? AND ?
              AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, producto, lote, estado in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            _add('acond', idx, 'acond', producto or f'Lote {lote}')
    except Exception:
        pass

    # ── ENTR · despachos (fecha) ────────────────────────────────────────
    try:
        rows = c.execute(f"""
            SELECT date(d.fecha) as fecha, COALESCE(cl.nombre,'') as cliente,
                   COUNT(di.id) as items
            FROM despachos d
              LEFT JOIN clientes cl ON cl.id = d.cliente_id
              LEFT JOIN despachos_items di ON di.numero_despacho = d.numero
            WHERE date(d.fecha) BETWEEN ? AND ?
            GROUP BY d.numero
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, cliente, n_items in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            label = f"Entrega {cliente}" + (f"\n{n_items} items" if n_items else '')
            _add('entr', idx, 'entr', label.strip() or 'Entrega')
    except Exception:
        pass

    # ── LIMP · limpieza_profunda_calendario ─────────────────────────────
    try:
        rows = c.execute(f"""
            SELECT lpc.fecha, lpc.area_codigo,
                   COALESCE(ap.nombre, lpc.area_codigo) as nombre,
                   lpc.estado
            FROM limpieza_profunda_calendario lpc
            LEFT JOIN areas_planta ap ON ap.codigo = lpc.area_codigo
            WHERE lpc.fecha BETWEEN ? AND ?
              AND LOWER(COALESCE(lpc.estado,'')) NOT IN ('cancelada')
        """, (desde_iso, hasta_iso)).fetchall()
        for fecha, area_cod, nombre, estado in rows:
            idx = _idx(fecha)
            if idx is None:
                continue
            _add('limp', idx, 'limp', nombre or area_cod or 'Limpieza')
    except Exception:
        pass

    return jsonify({
        'rango': {
            'desde': desde_iso, 'hasta': hasta_iso,
            'semana': f"{fechas[0].strftime('%d')}–{fechas[-1].strftime('%d')} {fechas[0].strftime('%b')} {fechas[0].year}"
        },
        'days': days_labels,
        'areas': matriz,
    })


@bp.route('/api/planta/cronograma-comparar-alejandro', methods=['GET'])
def planta_cronograma_comparar_alejandro():
    """Compara el cronograma de fabricación que mandó Alejandro vs lo que
    está realmente en produccion_programada (Calendar sync).

    Devuelve 3 secciones:
      - matches: producto+fecha que coinciden en ambos
      - en_alejandro_no_calendar: Alejandro programó pero Calendar NO tiene
      - en_calendar_no_alejandro: Calendar tiene pero Alejandro NO mencionó

    Esto le ayuda a Sebastián entender qué va a pasar:
      → Si "en_alejandro_no_calendar" tiene mucho → falta cargar producciones
      → Si "en_calendar_no_alejandro" tiene mucho → Calendar tiene cosas
        que Alejandro no contempló (revisar si están bien)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import datetime as _dt
    from templates_py.cronograma_alejandro_data import (
        ALEJANDRO_FAB_MAYO_2026, matchea
    )
    conn = get_db(); c = conn.cursor()

    # Producciones programadas en Calendar para mayo 2026
    rows = c.execute("""
        SELECT pp.fecha_programada, pp.producto, ap.codigo as area_cod,
               COALESCE(pp.estado, 'pendiente'), pp.id,
               COALESCE(pp.observaciones, '')
        FROM produccion_programada pp
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        WHERE pp.fecha_programada BETWEEN '2026-05-01' AND '2026-05-31'
          AND LOWER(COALESCE(pp.estado, '')) NOT IN ('cancelado')
    """).fetchall()
    calendar_items = []
    for fecha, producto, area, estado, pid, obs in rows:
        calendar_items.append({
            'fecha': fecha, 'producto': producto or '',
            'area': area or '', 'estado': estado, 'id': pid,
            'observaciones': obs or '',
        })

    # Cross-check
    matches = []
    en_alejandro_no_calendar = []
    en_calendar_no_alejandro = list(calendar_items)  # parte como todos, voy quitando los que matchean

    for fecha_a, producto_a, area_a, urgente in ALEJANDRO_FAB_MAYO_2026:
        # Buscar match en calendar (mismo día + producto similar)
        match = None
        for cal in calendar_items:
            if cal['fecha'] == fecha_a and matchea(cal['producto'], producto_a):
                match = cal
                break
        if match:
            # Mismo día y producto matchea
            area_match = (match['area'] == area_a)
            matches.append({
                'fecha': fecha_a,
                'producto_alejandro': producto_a,
                'producto_calendar': match['producto'],
                'area_alejandro': area_a,
                'area_calendar': match['area'],
                'area_match': area_match,
                'urgente_alejandro': urgente,
                'estado': match['estado'],
                'id_calendar': match['id'],
            })
            # Quitar de "en_calendar_no_alejandro"
            en_calendar_no_alejandro = [
                x for x in en_calendar_no_alejandro if x['id'] != match['id']
            ]
        else:
            # Buscar match en cualquier fecha (para detectar cambio de fecha)
            match_otra_fecha = None
            for cal in calendar_items:
                if matchea(cal['producto'], producto_a):
                    match_otra_fecha = cal
                    break
            en_alejandro_no_calendar.append({
                'fecha': fecha_a,
                'producto': producto_a,
                'area': area_a,
                'urgente': urgente,
                'match_otra_fecha': (match_otra_fecha['fecha']
                                      if match_otra_fecha else None),
                'producto_calendar_otra_fecha': (
                    match_otra_fecha['producto'] if match_otra_fecha else None
                ),
            })

    return jsonify({
        'rango': {'desde': '2026-05-01', 'hasta': '2026-05-31'},
        'resumen': {
            'total_alejandro': len(ALEJANDRO_FAB_MAYO_2026),
            'total_calendar': len(calendar_items),
            'matches_completos': sum(1 for m in matches if m.get('area_match')),
            'matches_fecha_distinto_area': sum(1 for m in matches if not m.get('area_match')),
            'falta_en_calendar': len(en_alejandro_no_calendar),
            'extra_en_calendar': len(en_calendar_no_alejandro),
        },
        'matches': matches,
        'en_alejandro_no_calendar': en_alejandro_no_calendar,
        'en_calendar_no_alejandro': en_calendar_no_alejandro,
    })


# ─────────────────────────────────────────────────────────────────────────
#  ASIGNAR ÁREAS · UI para que Alejandro asigne sala a cada producción
# ─────────────────────────────────────────────────────────────────────────
# Sebastián 2-may-2026: dos vías complementarias para que el plan refleje
# la organización que pide Alejandro:
#   1) Convención [CODIGO] al inicio del titulo en Calendar (parser en _sync).
#   2) UI manual: pantalla con listado + dropdown + auto-sugerir + confirmar.
# Estos endpoints sirven a la opción (2). Los cambios se persisten en
# produccion_programada.area_id (misma columna que los demás flujos).

def _sugerir_area_para_producto(c, producto, lote_kg):
    """Sugiere area_id para una producción según producto + tamaño de lote.

    Reglas (basadas en project_planta_crew_areas.md):
      • Si la fórmula contiene alcohol (palabras 'alcohol', 'etanol', 'isopropi') → PROD1 (especial='alcoholes')
      • Si lote_kg ≤ 100 → PROD2 (marmita 100ml)
      • Si lote_kg ≤ 250 → PROD3 (marmita 250ml)
      • Si lote_kg > 250 → PROD1 (gran capacidad, no especial)
      • Default → PROD1
    """
    try:
        # Cargar areas y formulas
        areas = {r[1]: r[0] for r in c.execute(
            "SELECT id, codigo FROM areas_planta WHERE activo=1"
        ).fetchall()}
        if not areas:
            return None
        # Detectar alcoholes en la fórmula
        usa_alcohol = False
        try:
            mps = c.execute("""
                SELECT LOWER(COALESCE(m.descripcion,''))
                  FROM formulas_v2 f
                  LEFT JOIN maestro_mp m ON m.id = f.mp_id
                 WHERE f.producto_nombre = ?
            """, (producto,)).fetchall()
            for r in mps:
                desc = r[0] or ''
                if any(kw in desc for kw in ('alcohol', 'etanol', 'isopropi')):
                    usa_alcohol = True
                    break
        except Exception:
            pass
        if usa_alcohol and 'PROD1' in areas:
            return areas['PROD1']
        try:
            lk = float(lote_kg or 0)
        except Exception:
            lk = 0
        if lk and lk <= 100 and 'PROD2' in areas:
            return areas['PROD2']
        if lk and lk <= 250 and 'PROD3' in areas:
            return areas['PROD3']
        if 'PROD1' in areas:
            return areas['PROD1']
        # Fallback: cualquier area que pueda producir
        any_prod = c.execute(
            "SELECT id FROM areas_planta WHERE puede_producir=1 AND activo=1 LIMIT 1"
        ).fetchone()
        return any_prod[0] if any_prod else None
    except Exception:
        return None


@bp.route('/api/planta/asignar-areas', methods=['GET'])
def planta_asignar_areas_listar():
    """Lista producciones de los próximos N días con su área actual + sugerida.

    Query params:
        dias (int, default 30): horizonte hacia adelante
        solo_sin_area (bool, default false): solo las que no tienen area asignada

    Devuelve para cada producción: id, producto, fecha, lotes, cantidad_kg,
    estado, area_id_actual + nombre, area_sugerida_id + codigo, lista de
    áreas disponibles para dropdown.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 30))
    except (TypeError, ValueError):
        dias = 30
    dias = max(1, min(dias, 180))
    solo_sin = request.args.get('solo_sin_area', 'false').lower() in ('1', 'true', 'yes')

    conn = get_db(); c = conn.cursor()
    # Cargar áreas activas (para dropdown)
    areas_disp = []
    for r in c.execute(
        """SELECT id, codigo, nombre, puede_producir, puede_envasar,
                  marmita_ml, especial
             FROM areas_planta WHERE activo=1 ORDER BY orden, id"""
    ).fetchall():
        areas_disp.append({
            'id': r[0], 'codigo': r[1], 'nombre': r[2],
            'puede_producir': bool(r[3]), 'puede_envasar': bool(r[4]),
            'marmita_ml': r[5], 'especial': r[6],
        })

    # Cargar producciones del horizonte (no completadas, no canceladas)
    where = """
        WHERE pp.fecha_programada BETWEEN date('now') AND date('now', ?)
          AND LOWER(COALESCE(pp.estado,'')) NOT IN ('completado','cancelado')
    """
    params = [f'+{dias} day']
    if solo_sin:
        where += " AND pp.area_id IS NULL"

    rows = c.execute(f"""
        SELECT pp.id, pp.producto, pp.fecha_programada,
               COALESCE(pp.lotes,1), COALESCE(pp.cantidad_kg, 0),
               COALESCE(pp.estado,'programado'),
               pp.area_id, ap.codigo, ap.nombre,
               COALESCE(pp.observaciones,''),
               COALESCE(pp.origen,'manual')
          FROM produccion_programada pp
          LEFT JOIN areas_planta ap ON ap.id = pp.area_id
          {where}
          ORDER BY pp.fecha_programada, pp.producto
    """, params).fetchall()

    # Cache lote_size_kg por producto (para sugerir)
    formulas = _get_formulas(conn)
    items = []
    for r in rows:
        (pid, prod, fecha, lotes, cant_kg, estado, area_id_act,
         area_cod, area_nom, obs, origen) = r
        lote_kg = formulas.get(prod, {}).get('lote_size_kg', 0) or 0
        sug_id = _sugerir_area_para_producto(c, prod, lote_kg)
        sug_cod = next((a['codigo'] for a in areas_disp if a['id'] == sug_id), None)
        items.append({
            'id': pid,
            'producto': prod or '',
            'fecha': fecha,
            'lotes': lotes,
            'cantidad_kg': float(cant_kg or 0),
            'estado': estado,
            'origen': origen,
            'observaciones': obs,
            'area_id_actual': area_id_act,
            'area_codigo_actual': area_cod,
            'area_nombre_actual': area_nom,
            'area_sugerida_id': sug_id,
            'area_sugerida_codigo': sug_cod,
            'lote_size_kg': float(lote_kg or 0),
        })

    return jsonify({
        'horizonte_dias': dias,
        'solo_sin_area': solo_sin,
        'total': len(items),
        'sin_area': sum(1 for x in items if x['area_id_actual'] is None),
        'areas_disponibles': areas_disp,
        'producciones': items,
    })


@bp.route('/api/planta/asignar-areas', methods=['POST'])
def planta_asignar_areas_bulk():
    """Asigna área a múltiples producciones en una sola llamada.

    Body JSON:
        asignaciones: [{id: int, area_id: int|null}, ...]

    Valida cada asignación. Devuelve dict con éxitos, errores y warnings
    (sala-ocupada en mismo día). NO falla la operación completa si una
    asignación individual no es válida — reporta y sigue con el resto.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(force=True, silent=True) or {}
    asignaciones = data.get('asignaciones', [])
    if not isinstance(asignaciones, list) or not asignaciones:
        return jsonify({'error': 'asignaciones debe ser lista no vacía'}), 400
    if len(asignaciones) > 200:
        return jsonify({'error': 'demasiadas asignaciones (max 200)'}), 400

    conn = get_db(); c = conn.cursor()
    user = session.get('compras_user', 'desconocido')
    ok_ids, errores, warnings = [], [], []

    # Cache áreas para validar y reportar conflictos
    areas_map = {}
    for r in c.execute(
        "SELECT id, codigo, nombre, puede_producir FROM areas_planta WHERE activo=1"
    ).fetchall():
        areas_map[r[0]] = {'codigo': r[1], 'nombre': r[2], 'puede_producir': bool(r[3])}

    for asg in asignaciones:
        try:
            pid = int(asg.get('id'))
        except (TypeError, ValueError):
            errores.append({'id': asg.get('id'), 'error': 'id inválido'})
            continue
        new_area = asg.get('area_id')
        if new_area is not None:
            try:
                new_area = int(new_area)
            except (TypeError, ValueError):
                errores.append({'id': pid, 'error': 'area_id inválido'})
                continue
            if new_area not in areas_map:
                errores.append({'id': pid, 'error': 'área no existe o inactiva'})
                continue

        pp = c.execute(
            """SELECT id, producto, fecha_programada, area_id,
                      COALESCE(estado,'')
                 FROM produccion_programada WHERE id=?""", (pid,)
        ).fetchone()
        if not pp:
            errores.append({'id': pid, 'error': 'producción no existe'})
            continue
        # No permitir reasignar producciones completadas o canceladas
        if pp[4].lower() in ('completado', 'cancelado'):
            errores.append({'id': pid, 'error': f'no se puede reasignar (estado: {pp[4]})'})
            continue

        prev_area = pp[3]
        # Conflicto: misma fecha + sala ya tomada → warning, no bloquea
        if new_area is not None:
            conf = c.execute("""
                SELECT id, producto FROM produccion_programada
                 WHERE fecha_programada=? AND area_id=? AND id<>?
                   AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
            """, (pp[2], new_area, pid)).fetchall()
            if conf:
                warnings.append({
                    'id': pid, 'producto': pp[1], 'fecha': pp[2],
                    'area_codigo': areas_map[new_area]['codigo'],
                    'choca_con': [{'id': x[0], 'producto': x[1]} for x in conf],
                })

        c.execute(
            "UPDATE produccion_programada SET area_id=? WHERE id=?",
            (new_area, pid)
        )
        # audit_log
        try:
            from audit_helpers import audit_log
            audit_log(
                c,
                accion='ASIGNAR_AREA_PROGRAMADA',
                tabla='produccion_programada',
                fila_id=pid,
                usuario=user,
                antes={'area_id': prev_area},
                despues={'area_id': new_area, 'producto': pp[1], 'fecha': pp[2]},
            )
        except Exception:
            pass
        ok_ids.append(pid)

    conn.commit()
    return jsonify({
        'ok': True,
        'asignados': len(ok_ids),
        'ids_ok': ok_ids,
        'errores': errores,
        'warnings': warnings,
    })


@bp.route('/api/planta/plan-semanal', methods=['GET'])
def planta_plan_semanal():
    """Vista consolidada del plan: cada producción ordenada por fecha,
    con días de inventario, consumo agregado y alertas.

    Sebastian (30-abr-2026): "siempre que calcula un producto suma los
    consumos de todas las programaciones previas a esa".

    Para cada producción programada:
      - dias_inventario_pt: días que duran las unidades PT con velocidad Shopify
      - mp_disponible_neto: stock_actual - sum(MP requerido por producciones PREVIAS)
      - alcanza_mp: bool (true si neto >= req actual)
      - mp_faltante: dict de materiales en déficit con cantidad
      - alerta_nivel: 'verde'|'amarillo'|'rojo' según días
      - presentaciones: lista de las del producto
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 14))
    except (TypeError, ValueError):
        dias = 14
    conn = get_db(); c = conn.cursor()

    fecha_desde = datetime.now().strftime('%Y-%m-%d')
    fecha_hasta = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')

    # 1) Producciones programadas en el rango
    producciones = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes, pp.estado,
               pp.area_id, ap.codigo as area_codigo, ap.nombre as area_nombre,
               fh.lote_size_kg, fh.imagen_url
        FROM produccion_programada pp
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        WHERE pp.fecha_programada BETWEEN ? AND ?
          AND COALESCE(pp.estado,'programado') NOT IN ('completado','cancelado')
        ORDER BY pp.fecha_programada ASC, pp.id ASC
    """, (fecha_desde, fecha_hasta)).fetchall()

    # 2) Consumo acumulado por material — fluye según orden temporal
    consumo_acumulado = {}  # material_id -> g acumulados
    items = []

    for row in producciones:
        prod_id, producto, fecha_prog, lotes, estado, area_id, area_codigo, area_nombre, lote_size, imagen_url = row
        lotes = lotes or 1
        mp_req = _calcular_mp_requerido(producto, lotes, c)

        # Para cada MP, calcular disponible NETO al momento de esta producción
        mp_status = []
        deficit = []
        for mat_id, req_g in mp_req.items():
            stock_total = _stock_mp(mat_id, c)
            ya_reservado = consumo_acumulado.get(mat_id, 0)
            disp_neto = stock_total - ya_reservado
            mat_nom_row = c.execute(
                "SELECT material_nombre FROM formula_items "
                "WHERE material_id=? LIMIT 1", (mat_id,)
            ).fetchone()
            mat_nom = (mat_nom_row[0] if mat_nom_row else mat_id)
            estado_mp = 'ok' if disp_neto >= req_g else ('justo' if disp_neto >= req_g * 0.5 else 'deficit')
            mp_status.append({
                'material_id': mat_id, 'material_nombre': mat_nom,
                'requerido_g': round(req_g),
                'stock_total_g': round(stock_total),
                'reservado_previo_g': round(ya_reservado),
                'disponible_neto_g': round(disp_neto),
                'estado': estado_mp,
            })
            if estado_mp == 'deficit':
                deficit.append({
                    'material_id': mat_id, 'material_nombre': mat_nom,
                    'falta_g': round(req_g - disp_neto),
                })
            # Acumular para siguientes
            consumo_acumulado[mat_id] = ya_reservado + req_g

        # Días de inventario PT
        # Buscar SKUs de este producto y velocidad de venta
        velocidad_dia = 0
        stock_pt = 0
        sku_rows = c.execute(
            "SELECT sku FROM sku_producto_map WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1",
            (producto,)
        ).fetchall()
        for (sku,) in sku_rows:
            vel = c.execute("""
                SELECT COALESCE(SUM(cantidad),0)/60.0
                FROM ordenes_shopify_items WHERE sku=? AND fecha >= date('now','-60 days')
            """, (sku,)).fetchone() if False else None  # legacy, may not exist
            # Stock PT
            sp = c.execute(
                "SELECT COALESCE(SUM(unidades_disponible),0) FROM stock_pt WHERE sku=?",
                (sku,)
            ).fetchone()
            if sp:
                stock_pt += sp[0] or 0
        dias_inv = round(stock_pt / max(velocidad_dia, 0.01), 1) if velocidad_dia > 0 else None

        # Nivel de alerta por días de inventario
        if dias_inv is None:
            alerta_dias = 'gris'
        elif dias_inv < 10:
            alerta_dias = 'rojo'
        elif dias_inv < 20:
            alerta_dias = 'amarillo'
        else:
            alerta_dias = 'verde'

        # Presentaciones del producto
        pres_rows = c.execute("""
            SELECT id, etiqueta, volumen_ml, peso_g, envase_codigo
            FROM producto_presentaciones
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND activo=1
        """, (producto,)).fetchall()
        presentaciones = [{
            'id': p[0], 'etiqueta': p[1], 'volumen_ml': p[2],
            'peso_g': p[3], 'envase_codigo': p[4]
        } for p in pres_rows]

        # ¿Alcanzan TODAS las MP para esta producción?
        alcanza_mp = len(deficit) == 0

        items.append({
            'produccion_id': prod_id,
            'producto': producto,
            'imagen_url': imagen_url,
            'fecha_programada': fecha_prog,
            'lotes': lotes,
            'lote_size_kg': lote_size,
            'estado': estado,
            'area_codigo': area_codigo,
            'area_nombre': area_nombre,
            'stock_pt_unidades': stock_pt,
            'dias_inventario': dias_inv,
            'alerta_dias': alerta_dias,
            'alcanza_mp': alcanza_mp,
            'mp_status': mp_status,
            'mp_deficit': deficit,
            'presentaciones': presentaciones,
        })

    # KPIs globales
    total = len(items)
    n_rojo = sum(1 for it in items if it['alerta_dias'] == 'rojo')
    n_amar = sum(1 for it in items if it['alerta_dias'] == 'amarillo')
    n_sin_mp = sum(1 for it in items if not it['alcanza_mp'])
    return jsonify({
        'rango': {'desde': fecha_desde, 'hasta': fecha_hasta, 'dias': dias},
        'items': items,
        'kpis': {
            'total': total,
            'alerta_roja_dias': n_rojo,
            'alerta_amarilla_dias': n_amar,
            'sin_mp_suficiente': n_sin_mp,
        }
    })


@bp.route('/api/planta/aceptar-produccion/<int:produccion_id>', methods=['POST'])
def planta_aceptar_produccion(produccion_id):
    """Cascade automático cuando el operario "acepta" la producción.

    Sebastian (30-abr-2026): "lo selecciona le sale con la foto, y de una
    sale señalar envases, solicitar etiquetas, armado de goteros si
    requiere, aceptar producción se dispone para realizar, entonces
    automaticamente pasa a que el sistema decida en que area se hace y
    genere todo".

    Acciones:
      1. Si no tiene area_id → llamar a sugerir_area y asignar la mejor
      2. Crear tareas operativas: señalar envases, solicitar etiquetas,
         armar goteros (si presentación lo requiere)
      3. Programar envasado tentativo al día siguiente
      4. Notificar a Calidad que viene muestra micro pronto
      5. Devolver el plan completo

    Body opcional: {presentacion_id, lote_personalizado, fecha_envasado_override}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    conn = get_db(); c = conn.cursor()

    pp_row = c.execute("""
        SELECT id, producto, fecha_programada, lotes, area_id, estado
        FROM produccion_programada WHERE id=?
    """, (produccion_id,)).fetchone()
    if not pp_row:
        return jsonify({'error': 'Producción no existe'}), 404
    prod_id, producto, fecha_prog, lotes, area_id, estado = pp_row
    lotes = lotes or 1

    log = []
    # 1) Asignar área si no la tiene
    if not area_id:
        # Calcular lote_kg para sugerencia
        fh = c.execute(
            "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
            (producto,)
        ).fetchone()
        lote_kg = (fh[0] if fh else 0) * lotes if fh else 0
        if lote_kg <= 0:
            log.append('⚠ No se pudo sugerir área: producto sin lote_size_kg')
        else:
            # Reusar la lógica de sugerencia
            cap_min = lote_kg * 1.2
            tanques = c.execute("""
                SELECT codigo, area_codigo, capacidad_litros
                FROM equipos_planta
                WHERE activo=1 AND tipo IN ('tanque','marmita','olla')
                  AND capacidad_litros >= ?
                ORDER BY capacidad_litros ASC
            """, (cap_min,)).fetchall()
            por_area = {}
            for t in tanques:
                a = t[1]
                if a and (a not in por_area or t[2] < por_area[a]):
                    por_area[a] = t[2]
            # Tomar la primera area que pueda producir
            elegida = None
            for area_codigo, cap in por_area.items():
                area_chk = c.execute(
                    "SELECT id, nombre, puede_producir, activo FROM areas_planta WHERE codigo=?",
                    (area_codigo,)
                ).fetchone()
                if area_chk and area_chk[2] and area_chk[3]:
                    elegida = (area_chk[0], area_chk[1], area_codigo)
                    break
            if elegida:
                c.execute("UPDATE produccion_programada SET area_id=? WHERE id=?",
                          (elegida[0], produccion_id))
                area_id = elegida[0]
                log.append(f'✓ Área asignada: {elegida[1]} ({elegida[2]})')
            else:
                log.append('⚠ Sin tanque disponible — asignar manualmente')
    else:
        area_row = c.execute(
            "SELECT codigo, nombre FROM areas_planta WHERE id=?", (area_id,)
        ).fetchone()
        if area_row:
            log.append(f'✓ Área ya asignada: {area_row[1]}')

    # 2) Crear tareas operativas
    pres_id = d.get('presentacion_id')
    pres_etiqueta = ''
    requiere_gotero = False
    if pres_id:
        pr = c.execute(
            "SELECT etiqueta, envase_codigo, presentacion_codigo FROM producto_presentaciones WHERE id=?",
            (pres_id,)
        ).fetchone()
        if pr:
            pres_etiqueta = pr[0]
            # Heurística: si la presentación es suero/gotero o tiene "gotero" en etiqueta
            etl = (pr[0] or '').lower()
            cod = (pr[2] or '').lower()
            requiere_gotero = ('suero' in etl or 'gotero' in etl or cod.startswith('sue_') or cod.startswith('co_'))

    fecha_obj = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    tareas_creadas = []

    # Tarea 1: señalar envases
    cur = c.execute("""
        INSERT INTO tareas_operativas
          (titulo, descripcion, tipo, producto_relacionado, asignado_a,
           fecha_objetivo, estado, origen_tipo, origen_id, creado_por)
        VALUES (?, ?, 'recoleccion_mee', ?, ?, ?, 'pendiente', 'aceptar_produccion', ?, ?)
    """, (
        f'Señalar envases para {producto}' + (f' · {pres_etiqueta}' if pres_etiqueta else ''),
        f'Marcar y separar envases de bodega MEE para producción del {fecha_prog}.',
        producto, 'mayerlin,operarios', fecha_obj, produccion_id, user
    ))
    tareas_creadas.append({'id': cur.lastrowid, 'tipo': 'recoleccion_mee'})

    # Tarea 2: solicitar etiquetas
    cur = c.execute("""
        INSERT INTO tareas_operativas
          (titulo, descripcion, tipo, producto_relacionado, asignado_a,
           fecha_objetivo, estado, origen_tipo, origen_id, creado_por)
        VALUES (?, ?, 'recoleccion_mee', ?, ?, ?, 'pendiente', 'aceptar_produccion', ?, ?)
    """, (
        f'Solicitar etiquetas para {producto}',
        f'Confirmar etiquetas listas para envasado del {fecha_obj}. Si no están, alertar.',
        producto, 'camilo,catalina', fecha_obj, produccion_id, user
    ))
    tareas_creadas.append({'id': cur.lastrowid, 'tipo': 'etiquetas'})

    # Tarea 3: armar goteros (si aplica)
    if requiere_gotero:
        cur = c.execute("""
            INSERT INTO tareas_operativas
              (titulo, descripcion, tipo, producto_relacionado, asignado_a,
               fecha_objetivo, estado, origen_tipo, origen_id, creado_por)
            VALUES (?, ?, 'recoleccion_mee', ?, ?, ?, 'pendiente', 'aceptar_produccion', ?, ?)
        """, (
            f'Armar goteros para {producto}' + (f' · {pres_etiqueta}' if pres_etiqueta else ''),
            'Ensamblar goteros (cuerpo + bulbo) según presentación.',
            producto, 'camilo,operarios', fecha_obj, produccion_id, user
        ))
        tareas_creadas.append({'id': cur.lastrowid, 'tipo': 'armar_goteros'})

    log.append(f'✓ {len(tareas_creadas)} tarea(s) operativa(s) creada(s) para {fecha_obj}')

    # 3) Notificar a Calidad que viene muestra micro
    try:
        from blueprints.notif import push_notif_multi
        push_notif_multi(
            ['alejandro', 'sebastian'],
            'planta',
            f'🧪 Producción aceptada: {producto}',
            body=f'Lote programado para {fecha_prog} en área {area_id}. Muestra micro se solicitará al iniciar envasado.',
            link='/inventarios#programacion',
            remitente=user,
        )
        log.append('✓ Calidad notificada')
    except Exception as e:
        log.append(f'⚠ Notif no enviada: {e}')

    # 4) Marcar produccion como confirmada (estado='confirmada' opcional)
    c.execute(
        "UPDATE produccion_programada SET observaciones=COALESCE(observaciones,'')||'\n[ACEPTADA por '||?||' '||datetime('now')||']' WHERE id=?",
        (user, produccion_id)
    )
    conn.commit()

    return jsonify({
        'ok': True,
        'produccion_id': produccion_id,
        'producto': producto,
        'log': log,
        'tareas_creadas': tareas_creadas,
        'fecha_envasado_estimada': fecha_obj,
        'area_id': area_id,
    })


@bp.route('/api/planta/preflight/<int:produccion_id>/confirmar-limpieza', methods=['POST'])
def planta_preflight_confirmar_limpieza(produccion_id):
    """Operario confirma que acaba de hacer limpieza profunda en la sala
    asociada a esta producción. Registra evento + actualiza
    areas_planta.ultima_limpieza_profunda."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    nota = (d.get('nota') or '').strip() or 'Limpieza profunda confirmada vía preflight'
    conn = get_db(); c = conn.cursor()
    pp = c.execute(
        "SELECT area_id FROM produccion_programada WHERE id=?", (produccion_id,)
    ).fetchone()
    if not pp or not pp[0]:
        return jsonify({'error': 'Producción sin área asignada'}), 400
    area_id = pp[0]
    c.execute("UPDATE areas_planta SET ultima_limpieza_profunda=datetime('now') WHERE id=?", (area_id,))
    c.execute("""
        INSERT INTO area_eventos (area_id, tipo, produccion_id, usuario, nota)
        VALUES (?, 'fin_limpieza', ?, ?, ?)
    """, (area_id, produccion_id, user, nota))
    conn.commit()
    return jsonify({'ok': True, 'mensaje': 'Limpieza profunda registrada'})
