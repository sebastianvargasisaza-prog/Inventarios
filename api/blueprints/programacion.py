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

CALENDAR_ID  = os.environ.get('CALENDAR_ID', 'c_d3a06d5f8ace62d5566968a70aeb2f3bd1d0a5b6b2b2f8c6b4ad66ac0d03286c@group.calendar.google.com')
GOOGLE_API_KEY   = os.environ.get('GOOGLE_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ─── Auth helper ────────────────────────────────────────────────────────────

def _auth():
    return bool(session.get('compras_user') or session.get('cont_user'))

# ─── Shopify velocity ────────────────────────────────────────────────────────

def _shopify_velocity(conn, days=60):
    """
    Lee animus_shopify_orders de los últimos `days` días.
    Retorna dict {sku_prefix: {units_per_month, orders}} usando sku_items JSON.
    También retorna dict {producto_nombre: vel_mes} usando sku_producto_map.
    """
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT sku_items, unidades_total, creado_en FROM animus_shopify_orders WHERE creado_en >= ? AND sku_items IS NOT NULL",
        (since,)
    ).fetchall()

    sku_units = {}  # sku_prefix -> total units in period
    sku_orders = {} # sku_prefix -> order count

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
            # Prefix: take chars before first hyphen or first 4-6 chars
            prefix = raw_sku.split('-')[0] if '-' in raw_sku else raw_sku[:6]
            sku_units[prefix] = sku_units.get(prefix, 0) + qty
            sku_orders[prefix] = sku_orders.get(prefix, 0) + 1

    months = days / 30.0
    sku_vel = {sku: round(units / months, 1) for sku, units in sku_units.items()}

    # Map SKU -> producto_nombre
    sku_map = {}
    for row in conn.execute("SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1").fetchall():
        sku_map[row[0].upper()] = row[1]

    prod_vel = {}  # producto_nombre -> vel_mes
    for sku, vel in sku_vel.items():
        if sku in sku_map:
            prod = sku_map[sku]
            prod_vel[prod] = prod_vel.get(prod, 0) + vel

    return {
        'sku_velocity': sku_vel,
        'prod_velocity': prod_vel,
        'total_orders': len(rows),
        'days_analyzed': days,
        'months_analyzed': round(months, 1),
    }

# ─── Google Calendar ─────────────────────────────────────────────────────────

def _fetch_calendar_events(days_ahead=90):
    """Fetch production calendar events via Google Calendar REST API."""
    if not GOOGLE_API_KEY:
        return {'events': [], 'error': 'GOOGLE_API_KEY no configurada'}

    now = datetime.utcnow()
    time_min = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    time_max = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%dT%H:%M:%SZ')

    params = urllib.parse.urlencode({
        'key': GOOGLE_API_KEY,
        'timeMin': time_min,
        'timeMax': time_max,
        'singleEvents': 'true',
        'orderBy': 'startTime',
        'maxResults': 50,
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
        return {'events': events, 'error': None}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        return {'events': [], 'error': f'Calendar API HTTP {e.code}: {body}'}
    except Exception as e:
        return {'events': [], 'error': str(e)}

# ─── MP stock ────────────────────────────────────────────────────────────────

def _get_mp_stock(conn):
    """Returns dict {material_id: stock_actual_g}"""
    rows = conn.execute(
        "SELECT codigo, stock_actual, unidad FROM maestro_mps WHERE activo=1"
    ).fetchall()
    stock = {}
    for r in rows:
        codigo = str(r[0] or '').strip()
        val = float(r[1] or 0)
        unidad = str(r[2] or 'g').lower()
        # Normalize to grams
        if unidad in ('kg', 'kilo', 'kilos'):
            val = val * 1000
        stock[codigo] = val
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

# ─── Stock projection ────────────────────────────────────────────────────────

def _project_stock(conn, prod_vel, formulas, mp_stock, calendar_events):
    """
    For each product with a formula and velocity data:
    1. Calculates MP requirements for one production run (lote_size_kg)
    2. Checks if all MPs are available
    3. Projects stock at 30/60 days given velocity
    4. Generates semaphore: verde/amarillo/rojo
    """
    # Build set of products that have both velocity and formula
    products_with_formula = set(formulas.keys())

    # Next production per product from calendar events
    next_prod_by_product = {}
    for ev in calendar_events:
        titulo = ev.get('titulo', '').upper()
        fecha = ev.get('fecha', '')
        for prod in products_with_formula:
            # Simple match: first 6 chars of product in event title
            key = prod[:6].upper()
            if key in titulo and prod not in next_prod_by_product:
                next_prod_by_product[prod] = fecha
                break

    projection = []
    all_alerts = []

    # All products that have formulas — show all, mark those without velocity as 0
    for prod, formula in sorted(formulas.items()):
        vel_mes = prod_vel.get(prod, 0)
        lote_kg = formula['lote_size_kg']
        items = formula['items']

        # Estimate current finished product stock from acondicionamiento
        # (units produced minus estimated sold)
        # Simple estimate: 0 for now (can be wired to PT inventory later)
        stock_pt_uds = 0

        # MP check: can we produce one batch?
        mp_check = []
        can_produce = True
        for item in items:
            mid = item['material_id']
            needed_g = item['cantidad_g_por_lote']
            available_g = mp_stock.get(mid, 0)
            deficit_g = max(0, needed_g - available_g)
            ok = deficit_g == 0
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

        # Stock projection at 30d and 60d (in kg of product)
        vel_kg_mes = vel_mes * 0.030  # assuming 30ml per unit → 0.030 kg/unit (rough)
        stock_30d = lote_kg - vel_kg_mes if lote_kg > 0 else 0
        stock_60d = lote_kg - (vel_kg_mes * 2) if lote_kg > 0 else 0

        prox_prod = next_prod_by_product.get(prod, 'No programado')

        # Semaphore logic
        if not can_produce and vel_mes > 0:
            semaforo = 'rojo'
        elif stock_60d < 0 and vel_mes > 0:
            semaforo = 'rojo'
        elif stock_30d < (vel_kg_mes * 0.5):
            semaforo = 'amarillo'
        else:
            semaforo = 'verde'

        # Missing MPs alert
        missing_mp = [m for m in mp_check if not m['ok']]
        if missing_mp:
            msg = f"Faltan {len(missing_mp)} MPs para producir 1 lote: " + \
                  ", ".join(f"{m['nombre']} (deficit {m['deficit_g']:.0f}g)" for m in missing_mp[:3])
            if len(missing_mp) > 3:
                msg += f" y {len(missing_mp)-3} más"
            all_alerts.append({
                'producto': prod,
                'nivel': 'critico' if semaforo == 'rojo' else 'alto',
                'tipo': 'mp_faltante',
                'mensaje': msg,
            })

        if stock_60d < 0 and vel_mes > 0:
            all_alerts.append({
                'producto': prod,
                'nivel': 'alto',
                'tipo': 'stock_insuficiente_60d',
                'mensaje': f"Stock proyectado a 60 días: {stock_60d:.1f}kg — velocidad {vel_mes:.0f} uds/mes requiere reposición urgente",
            })

        if prox_prod == 'No programado' and vel_mes > 5:
            all_alerts.append({
                'producto': prod,
                'nivel': 'medio',
                'tipo': 'sin_programar',
                'mensaje': f"Vende {vel_mes:.0f} uds/mes pero no tiene producción programada en calendario",
            })

        projection.append({
            'producto': prod,
            'lote_kg': lote_kg,
            'vel_mes': round(vel_mes, 1),
            'stock_actual': round(lote_kg, 1),
            'stock_30d': round(stock_30d, 1),
            'stock_60d': round(stock_60d, 1),
            'prox_produccion': prox_prod,
            'mp_lista': can_produce,
            'n_mp_faltantes': len(missing_mp),
            'semaforo': semaforo,
            'mp_check': mp_check,
        })

    # Sort: rojo → amarillo → verde
    order = {'rojo': 0, 'amarillo': 1, 'verde': 2}
    projection.sort(key=lambda x: (order.get(x['semaforo'], 3), x['producto']))
    all_alerts.sort(key=lambda x: {'critico': 0, 'alto': 1, 'medio': 2}.get(x['nivel'], 3))

    return projection, all_alerts

# ─── Anthropic narrative ─────────────────────────────────────────────────────

def _generate_narrative(projection, alerts, vel_data):
    """Calls Anthropic API to generate Spanish narrative summary."""
    if not ANTHROPIC_API_KEY:
        return None

    n_rojo = sum(1 for p in projection if p['semaforo'] == 'rojo')
    n_amarillo = sum(1 for p in projection if p['semaforo'] == 'amarillo')
    top_ventas = sorted(projection, key=lambda x: x['vel_mes'], reverse=True)[:3]
    top_str = ", ".join(f"{p['producto'][:20]} ({p['vel_mes']} uds/mes)" for p in top_ventas)

    prompt = (
        f"Eres el sistema de planificación de Espagiria Laboratorios. "
        f"Analiza este estado de producción y da un resumen ejecutivo en español en máximo 4 oraciones, "
        f"con tono técnico-operativo directo:\n\n"
        f"- Productos en estado crítico (rojo): {n_rojo}\n"
        f"- Productos en alerta (amarillo): {n_amarillo}\n"
        f"- Productos en orden (verde): {len(projection) - n_rojo - n_amarillo}\n"
        f"- Top ventas: {top_str}\n"
        f"- Total pedidos Shopify analizados (60d): {vel_data.get('total_orders', 0)}\n"
        f"- Alertas críticas: {len([a for a in alerts if a['nivel'] == 'critico'])}\n"
        f"- Alertas altas: {len([a for a in alerts if a['nivel'] == 'alto'])}\n"
        f"\nResumen:"
    )

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        return resp.get('content', [{}])[0].get('text', '')
    except Exception as e:
        return f"[IA no disponible: {e}]"

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
        narrativa = _generate_narrative(projection, alerts, vel_data)
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


@bp.route('/api/programacion/velocidad')
def prog_velocidad():
    if not _auth():
        return jsonify({'error': 'No autenticado'}), 401
    days = int(request.args.get('days', 60))
    conn = get_db()
    return jsonify(_shopify_velocity(conn, days=days))


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
