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

# ─── Stock projection ────────────────────────────────────────────────────────

def _project_stock(conn, prod_vel, formulas, mp_stock, calendar_events):
    """
    For each product with a formula:
    1. Gets actual finished product stock from acondicionamiento (unidades_producidas)
    2. Checks MP availability for one production batch
    3. Projects stock at 60 days given Shopify velocity (in units)
    4. Generates semaphore: verde/amarillo/rojo
    """
    # Finished product stock from acondicionamiento (last 180 days, in units)
    acondi_rows = conn.execute("""
        SELECT producto,
               COALESCE(SUM(unidades_producidas), 0) as total_uds
        FROM acondicionamiento
        WHERE fecha >= date('now', '-180 days')
        GROUP BY producto
    """).fetchall()
    # Normalize names to uppercase for matching
    pt_stock = {}
    for r in acondi_rows:
        prod_name = str(r[0] or '').strip().upper()
        pt_stock[prod_name] = int(r[1] or 0)

    # Build set of products that have formulas
    products_with_formula = set(formulas.keys())

    # Next production per product from calendar events
    next_prod_by_product = {}
    for ev in calendar_events:
        titulo = ev.get('titulo', '').upper()
        fecha = ev.get('fecha', '')
        for prod in products_with_formula:
            key = prod[:6].upper()
            if key in titulo and prod not in next_prod_by_product:
                next_prod_by_product[prod] = fecha
                break

    # Build mp_stock key set for matching debug (lowercase + uppercase variants)
    mp_keys = set(mp_stock.keys())

    projection = []
    all_alerts = []

    for prod, formula in sorted(formulas.items()):
        vel_mes = prod_vel.get(prod, 0)
        lote_kg = formula['lote_size_kg']
        items = formula['items']

        # Finished product stock in units (from acondicionamiento)
        stock_pt_uds = pt_stock.get(prod.upper(), 0)

        # MP check: can we produce one batch?
        # Only flag deficit if needed_g > 0 (formula has quantity data)
        mp_check = []
        can_produce = True
        items_with_qty = [i for i in items if i.get('cantidad_g_por_lote', 0) > 0]
        if not items_with_qty:
            # Formula has no quantity data — mark as unknown, not blocking
            can_produce = None  # None = unknown
        else:
            for item in items_with_qty:
                mid = str(item['material_id']).strip()
                needed_g = float(item['cantidad_g_por_lote'])
                available_g = mp_stock.get(mid, 0)
                deficit_g = max(0, needed_g - available_g)
                ok = deficit_g < 1  # within 1g tolerance
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

        prox_prod = next_prod_by_product.get(prod, 'No programado')

        # Stock projection: current units minus 2 months of sales
        stock_60d_uds = max(stock_pt_uds - int(vel_mes * 2), 0) if vel_mes > 0 else stock_pt_uds

        # MP alert list
        missing_mp = [m for m in mp_check if not m['ok']]

        # Semaphore: based on units, not kg
        if can_produce is False and vel_mes > 0:
            semaforo = 'rojo'
        elif stock_60d_uds <= 0 and vel_mes > 5:
            semaforo = 'rojo'
        elif stock_60d_uds < vel_mes and vel_mes > 0:
            semaforo = 'amarillo'
        else:
            semaforo = 'verde'

        # Alerts
        if missing_mp and can_produce is False:
            msg = ("Faltan " + str(len(missing_mp)) + " MPs para producir 1 lote: " +
                   ", ".join(m['nombre'] + " (deficit " + str(int(m['deficit_g'])) + "g)"
                             for m in missing_mp[:3]))
            if len(missing_mp) > 3:
                msg += " y " + str(len(missing_mp) - 3) + " mas"
            all_alerts.append({
                'producto': prod,
                'nivel': 'critico' if semaforo == 'rojo' else 'alto',
                'tipo': 'mp_faltante',
                'mensaje': msg,
            })

        if stock_60d_uds <= 0 and vel_mes > 5:
            all_alerts.append({
                'producto': prod,
                'nivel': 'alto',
                'tipo': 'stock_insuficiente_60d',
                'mensaje': ("Stock PT actual: " + str(stock_pt_uds) + " uds"
                            " — velocidad " + str(int(vel_mes)) + " uds/mes no cubre 60 dias"),
            })

        if prox_prod == 'No programado' and vel_mes > 5:
            all_alerts.append({
                'producto': prod,
                'nivel': 'medio',
                'tipo': 'sin_programar',
                'mensaje': ("Vende " + str(int(vel_mes)) + " uds/mes"
                            " pero no tiene produccion programada en calendario"),
            })

        projection.append({
            'producto': prod,
            'lote_kg': lote_kg,
            'vel_mes': round(vel_mes, 1),
            'stock_actual': stock_pt_uds,
            'stock_60d': int(stock_60d_uds),
            'prox_produccion': prox_prod,
            'mp_lista': can_produce,
            'n_mp_faltantes': len(missing_mp),
            'semaforo': semaforo,
            'mp_check': mp_check,
        })

    # Sort: rojo -> amarillo -> verde
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
