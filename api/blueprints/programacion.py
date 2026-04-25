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
import os, json, urllib.request, urllib.error, urllib.parse
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

    # Denominador = días reales de datos en tabla, no la ventana solicitada.
    # Si el sync solo jaló 4 días, dividir por 60 daría velocidad 10x baja.
    if rows:
        all_dates = [r[2] for r in rows if r[2]]
        if len(all_dates) >= 2:
            from datetime import date as _dt
            d_min = _dt.fromisoformat(min(all_dates))
            d_max = _dt.fromisoformat(max(all_dates))
            actual_days = max((d_max - d_min).days, 1)
        else:
            actual_days = 1
    else:
        actual_days = days
    months = max(actual_days / 30.0, 1/30.0)  # mínimo 1 día
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
                summary = line[8:].replace('\n', ' ').replace('\,', ',').strip()
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
    """Return list of upcoming local production events from produccion_programada."""
    try:
        rows = conn.execute(
            """SELECT id, producto, fecha_programada, lotes, estado, observaciones
               FROM produccion_programada
               WHERE estado NOT IN ('completado','cancelado')
                 AND fecha_programada >= date('now')
               ORDER BY fecha_programada"""
        ).fetchall()
        return [
            {'id': r[0], 'titulo': r[1], 'fecha': r[2],
             'lotes': r[3], 'estado': r[4], 'descripcion': r[5] or ''}
            for r in rows
        ]
    except Exception as e:
        return []

# ─── MP stock ────────────────────────────────────────────────────────────────

def _get_mp_stock(conn):
    """Returns dict {material_id: stock_actual_g}
    Stock calculated from movimientos (Entrada - Salida), already in grams.
    """
    rows = conn.execute("""
        SELECT material_id,
               COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0)
        FROM movimientos
        GROUP BY material_id
    """).fetchall()
    stock = {}
    for material_id, stock_g in rows:
        if material_id:
            stock[str(material_id).strip()] = max(float(stock_g or 0), 0)
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
    """
    Stock real de producto terminado desde stock_pt.
    Cuando Espagiria libera un lote de CC, el sistema crea entradas en stock_pt
    con unidades_disponible. Los despachos la reducen.
    Mapea sku -> producto_nombre via sku_producto_map.
    Returns dict {PRODUCTO_UPPER: stock_int}
    """
    # SKU -> producto_nombre (from sku_producto_map)
    sku_map = {}
    try:
        for row in conn.execute("SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1").fetchall():
            k = str(row[0] or '').strip().upper()
            if k:
                sku_map[k] = str(row[1] or '').strip().upper()
    except Exception:
        pass

    # Stock disponible por SKU desde stock_pt (fuente real de PT liberado)
    stock = {}
    try:
        rows = conn.execute("""
            SELECT sku, COALESCE(SUM(unidades_disponible), 0)
            FROM stock_pt
            WHERE estado = 'Disponible'
            GROUP BY sku
        """).fetchall()
        for row in rows:
            raw_sku = str(row[0] or '').strip().upper()
            uds = max(int(row[1] or 0), 0)
            if not raw_sku:
                continue
            # Try exact SKU match first, then prefix match
            prod = sku_map.get(raw_sku)
            if not prod:
                prefix = raw_sku.split('-')[0]
                prod = sku_map.get(prefix)
            if prod:
                stock[prod] = stock.get(prod, 0) + uds
            else:
                # Store by raw SKU as fallback so it's visible in debug
                stock[raw_sku] = stock.get(raw_sku, 0) + uds
    except Exception:
        pass

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

DIAS_CRITICOS = 20   # umbral de cobertura: menos de esto = rojo
DIAS_ALERTA   = 40   # buffer: menos de esto = amarillo

def _project_stock(conn, prod_vel, formulas, mp_stock, calendar_events):
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
    # Priority: 1) local DB, 2) Google Calendar / iCal (smart matching)
    products_with_formula = set(formulas.keys())
    next_prod_by_product = {}

    # 1. Local DB events (exact product name)
    local_events = _fetch_local_production_events(conn)
    for ev in local_events:
        prod_ev = ev.get('titulo', '')
        if prod_ev in products_with_formula and prod_ev not in next_prod_by_product:
            next_prod_by_product[prod_ev] = ev.get('fecha', '')

    # 2. Google Calendar / iCal events (smart title matching)
    import re as _re_cal
    _stop_words = {'DE','DEL','LA','EL','LOS','LAS','CON','MAS','PARA',
                   'PRODUCCION','PRODUCCIÓN','LOTE','ESPAGIRIA','ANIMUS'}

    def _cal_score(titulo_up, prod_up):
        if prod_up in titulo_up:
            return 100
        tw = set(w for w in _re_cal.split(r'[^A-Z0-9]+', titulo_up) if len(w) > 2)
        pw = set(w for w in _re_cal.split(r'[^A-Z0-9]+', prod_up)  if len(w) > 2)
        pw -= _stop_words
        if not pw:
            return 0
        return int(100 * len(pw & tw) / len(pw))

    for ev in calendar_events:
        titulo_up = ev.get('titulo', '').upper()
        fecha_ev  = ev.get('fecha', '')
        if not fecha_ev:
            continue
        best_prod, best_score = None, 49
        for prod in products_with_formula:
            if prod in next_prod_by_product:
                continue
            sc = _cal_score(titulo_up, prod.upper())
            if sc > best_score:
                best_score, best_prod = sc, prod
        if best_prod:
            next_prod_by_product[best_prod] = fecha_ev

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
        if vel_dia > 0:
            dias_cob = stock_uds / vel_dia
        else:
            dias_cob = 999.0   # sin ventas = cobertura indefinida

        # Produccion en calendario
        prox_prod = next_prod_by_product.get(prod, 'No programado')

        # Validar si la produccion calendario llega antes del dia critico
        cal_ok = False
        if prox_prod != 'No programado':
            try:
                prod_date = __import__('datetime').date.fromisoformat(prox_prod)
                dias_hasta_prod = (prod_date - today).days
                cal_ok = dias_hasta_prod <= dias_cob
            except Exception:
                cal_ok = False

        # MP check: puede producir un lote?
        mp_check = []
        can_produce = True
        items_with_qty = [i for i in items if i.get('cantidad_g_por_lote', 0) > 0]
        if not items_with_qty:
            can_produce = None  # desconocido: formula sin cantidades
        else:
            for item in items_with_qty:
                mid = str(item['material_id']).strip()
                needed_g = float(item['cantidad_g_por_lote'])
                available_g = mp_stock.get(mid, 0)
                deficit_g = max(0, needed_g - available_g)
                ok = deficit_g < 1
                if not ok:
                    can_produce = False
                mp_check.append({
                    'material_id': mid,
                    'nombre': item['material_nombre'],
                    'needed_g': needed_g,
                    'available_g': available_g,
                    'deficit_g': deficit_g,
                    'ok': ok,
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
            all_alerts.append({
                'producto': prod,
                'nivel': 'alto',
                'tipo': 'mp_faltante',
                'mensaje': ("Faltan " + n_str + " MPs para producir: " + names),
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
            'cal_ok': cal_ok,
            'mp_lista': can_produce,
            'n_mp_faltantes': len(missing_mp),
            'semaforo': semaforo,
            'mp_check': mp_check,
        })

    order = {'rojo': 0, 'amarillo': 1, 'verde': 2}
    projection.sort(key=lambda x: (order.get(x['semaforo'], 3), x['producto']))
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

    # 5. Project stock + alerts
    projection, alerts = _project_stock(
        conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', [])
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
        'narrativa_ia': narrativa,
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

    matches = []
    for ev in cal.get('events', []):
        titulo = ev.get('titulo','')
        scores = sorted(
            [{'producto': p, 'score': score(titulo, p)} for p in products_with_formula],
            key=lambda x: -x['score']
        )[:5]
        matches.append({'evento': titulo, 'fecha': ev.get('fecha',''), 'top_matches': scores})

    return jsonify({
        'source': cal.get('source','?'),
        'error':  cal.get('error'),
        'total_events': len(cal.get('events',[])),
        'gcal_ical_url_set': bool(GCAL_ICAL_URL),
        'google_api_key_set': bool(GOOGLE_API_KEY),
        'matches': matches,
        'raw_events': cal.get('events',[])
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
    projection, _ = _project_stock(conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []))
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
    _, alerts = _project_stock(conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', []))
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

    projection, alerts = _project_stock(
        conn, vel_data['prod_velocity'], formulas, mp_stock, cal.get('events', [])
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
