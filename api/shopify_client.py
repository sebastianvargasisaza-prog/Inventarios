"""Cliente Shopify unificado para EOS Inventarios.

Sebastián 23-may-2026 PM · agente auditor reportó 4 implementaciones casi
idénticas del sync de Shopify orders (animus.py, auto_plan_jobs.py,
programacion.py, auto_plan.py). Cada fix había que aplicarlo 4 veces.

Este módulo centraliza:
- TZ Bogotá helper canónico (`created_at_bogota`)
- Pull paginado con fetch_with_retry (429/5xx)
- INSERT OR REPLACE en animus_shopify_orders con tags + customer_tags +
  filtros cancelled/refunded ya cubiertos.
- Window opt-in por días (default 90)
- Hook opcional a `_sync_shopify_a_movimientos` para crear movimientos
  SHOPIFY_VENTA en kardex (solo cuando incluir_movimientos=True).

API:
    sync_shopify_orders(conn, *, days=90, incluir_movimientos=False,
                        timeout=30, log_to=None) -> dict
        Returns {'ok': bool, 'synced': int, 'days': int,
                  'error': str|None, 'ventas_inventario': int|None}
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


def created_at_bogota(created_at_str: str) -> str:
    """Convierte ISO UTC de Shopify a fecha en TZ Bogotá (UTC-5).

    Shopify devuelve `created_at` en ISO UTC (ej '2026-05-22T03:30:00Z').
    Si hacemos [:10] sin convertir, venta de hoy 22:30 Bogotá queda como
    AYER UTC. El filtro `WHERE date >= N` la pierde.
    """
    if not created_at_str:
        return ''
    try:
        s = (created_at_str or '').replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        bogota = timezone(timedelta(hours=-5))
        return dt.astimezone(bogota).strftime('%Y-%m-%d')
    except Exception:
        return (created_at_str or '')[:10]


def _get_shopify_config(conn):
    """Lee token + shop desde animus_config (tabla key/value)."""
    try:
        from blueprints.animus import _cfg
        token = _cfg(conn, 'shopify_token')
        shop = _cfg(conn, 'shopify_shop')
        return token, shop
    except Exception:
        return None, None


def ciclo_despacho(orden):
    """Cuándo salió el pedido, con qué guía y si LLEGÓ · sale de `fulfillments[]`.

    Gerencia (17-ago): *"hoy cerramos el ciclo cuando el pedido SALE, no cuando LLEGA · sin esto
    no sabemos cuántos pedidos llegaron de verdad"*. Shopify ya manda todo y el sync lo tiraba.

    Devuelve `(despachado_at, guia, transportadora, entregado_at, estado_envio)`.

    Reglas:
      · se toma el fulfillment MÁS RECIENTE no cancelado -- un pedido se puede despachar en
        partes y lo que interesa es el estado actual del envío;
      · `entregado_at` se llena SÓLO si la transportadora reporta `shipment_status='delivered'`.
        Donde no lo reporte queda VACÍO, y vacío es honesto: una entrega inventada se lee igual
        que una confirmada, y es sobre eso que se decide (M115/M124);
      · `estado_envio` viaja aparte justamente para poder distinguir *"no llegó"* de *"nadie lo
        reportó"*, que es lo que el indicador existe para medir.

    Está como función y no inline para poder MEDIRLA: la extracción es lo único que puede
    equivocarse acá, y probarla contra una respuesta real de Shopify no exige red.
    """
    ffs = [f for f in ((orden or {}).get('fulfillments') or [])
           if str((f or {}).get('status') or '').lower() != 'cancelled']
    if not ffs:
        return ('', '', '', '', '')
    ff = ffs[-1] or {}
    guia = (ff.get('tracking_number') or '')
    if not guia:
        _nums = ff.get('tracking_numbers') or []
        guia = (_nums[0] if _nums else '')
    estado_envio = (ff.get('shipment_status') or '')
    entregado_at = (created_at_bogota(ff.get('updated_at', ''))
                    if str(estado_envio).lower() == 'delivered' else '')
    return (created_at_bogota(ff.get('created_at', '')), guia,
            (ff.get('tracking_company') or ''), entregado_at, estado_envio)


def sync_shopify_orders(conn, *, days: int = 90,
                          incluir_movimientos: bool = False,
                          timeout: int = 30,
                          log_to=None) -> dict:
    """Sync de Shopify orders → animus_shopify_orders.

    Args:
        conn: conexión DB EOS (sqlite3 o psycopg wrapper).
        days: ventana de días hacia atrás para pull (default 90).
        incluir_movimientos: si True, llama `_sync_shopify_a_movimientos`
            después del pull para crear movimientos SHOPIFY_VENTA en kardex.
            Solo se usa desde endpoint manual `/api/animus/sync`.
        timeout: timeout por request HTTP (default 30s).
        log_to: callable opcional para logging (logger.info, etc).

    Returns:
        dict {'ok': bool, 'synced': int, 'days': int, 'error': str|None,
              'ventas_inventario': int|None}
    """
    out = {'ok': False, 'synced': 0, 'days': days,
            'error': None, 'ventas_inventario': None}

    def _log(msg):
        if log_to:
            try:
                log_to(msg)
            except Exception:
                pass

    token, shop = _get_shopify_config(conn)
    if not token or not shop:
        out['error'] = 'Shopify no configurado (shopify_token/shopify_shop)'
        return out

    # Helper retry (importado lazy para evitar circular en boot)
    try:
        from http_helpers import fetch_with_retry
    except Exception as e:
        out['error'] = f'http_helpers no disponible: {e}'
        return out

    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime(
        '%Y-%m-%dT00:00:00Z')
    url = (
        f"https://{shop}/admin/api/2024-01/orders.json"
        f"?status=any&limit=250&created_at_min={cutoff}"
    )
    synced = 0
    try:
        while url:
            req = urllib.request.Request(
                url, headers={'X-Shopify-Access-Token': token})
            with fetch_with_retry(req, timeout=timeout, max_intentos=3) as r:
                body = r.read()
                link_hdr = r.headers.get('Link', '') or ''
            data = json.loads(body)
            orders = data.get('orders', [])
            for o in orders:
                line_items = o.get('line_items', []) or []
                items_sku = json.dumps([
                    {'sku': li.get('sku', ''),
                      'qty': li.get('quantity', 0)}
                    for li in line_items
                ])
                total_uds = sum(
                    li.get('quantity', 0) for li in line_items)
                # FIX 23-may-PM · address shipping first (más correcto
                # para Colombia donde billing y shipping suelen diferir)
                addr = (o.get('shipping_address')
                         or o.get('billing_address')
                         or {})
                tags = o.get('tags', '') or ''
                cust_tags = ((o.get('customer') or {}).get('tags', '')) or ''
                # La marca de CONTRAENTREGA se escribe a mano al crear el pedido, y puede venir
                # de tres lados según quién lo cargue: la NOTA del pedido (lo más común acá), una
                # etiqueta, o el medio de pago. Se traen los tres y el detector mira los tres
                # (`es_contraentrega`), porque depender de uno solo pierde pedidos en silencio.
                nota = o.get('note') or ''
                # La marca de contraentrega también se escribe en la DIRECCIÓN DE ENVÍO
                # (3-ago · "CONTRAENTREGA ENVIAR CON EL PROFE"). El buscador de Shopify la
                # encuentra ahí; EOS guardaba sólo la ciudad, así que esa marca nunca llegaba
                # al sistema y el detector veía 4 pedidos donde había decenas.
                direccion = ' '.join(x for x in (
                    addr.get('address1') or '', addr.get('address2') or '',
                    addr.get('company') or '') if x).strip()
                gateway = ', '.join(o.get('payment_gateway_names') or []) or (o.get('gateway') or '')
                (_despachado_at, _guia, _transportadora,
                 _entregado_at, _estado_envio) = ciclo_despacho(o)
                # UPSERT que toca SOLO las columnas de este sync (M20). Con `INSERT OR REPLACE`
                # toda columna no listada vuelve a su default: éste borraba los descuentos y el
                # flag `flujo_synced`, y el sync de marketing borraba a su vez estas etiquetas.
                # Los tres sincronizadores se pisaban y ganaba el que corriera último.
                conn.execute(
                    """INSERT INTO animus_shopify_orders
                       (shopify_id, nombre, email, total, moneda, estado,
                        estado_pago, sku_items, unidades_total, ciudad,
                        pais, creado_en, synced_at, tags, customer_tags,
                        nota, gateway, direccion, despachado_at, guia,
                        transportadora, entregado_at, estado_envio)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,
                               datetime('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(shopify_id) DO UPDATE SET
                         nombre=excluded.nombre, email=excluded.email,
                         total=excluded.total, moneda=excluded.moneda,
                         estado=excluded.estado, estado_pago=excluded.estado_pago,
                         sku_items=excluded.sku_items,
                         unidades_total=excluded.unidades_total,
                         ciudad=excluded.ciudad, pais=excluded.pais,
                         creado_en=excluded.creado_en, synced_at=excluded.synced_at,
                         tags=excluded.tags, customer_tags=excluded.customer_tags,
                         nota=excluded.nota, gateway=excluded.gateway,
                         direccion=excluded.direccion,
                         despachado_at=excluded.despachado_at, guia=excluded.guia,
                         transportadora=excluded.transportadora,
                         entregado_at=excluded.entregado_at,
                         estado_envio=excluded.estado_envio""",
                    (str(o['id']),
                     o.get('name', ''),
                     o.get('email', ''),
                     float(o.get('total_price', 0)),
                     o.get('currency', 'COP'),
                     # FIX 27-jun (auditoría Shopify→Necesidades) · Shopify NO escribe 'cancelled' en
                     # fulfillment_status (queda null/unfulfilled); la marca de cancelación es cancelled_at.
                     # Antes el filtro de velocidad `estado NOT IN ('cancelled',...)` era letra muerta y las
                     # órdenes CANCELADAS contaban como ventas → velocidad inflada de Ánimus. Ahora si la
                     # orden está cancelada el estado queda 'cancelled' y el filtro existente la excluye.
                     ('cancelled' if (o.get('cancelled_at') or '').strip()
                      else (o.get('fulfillment_status') or '')),
                     o.get('financial_status', ''),
                     items_sku,
                     total_uds,
                     addr.get('city', ''),
                     addr.get('country_code', 'CO'),
                     created_at_bogota(o.get('created_at', '')),
                     tags,
                     cust_tags,
                     nota,
                     gateway,
                     direccion,
                     _despachado_at,
                     _guia,
                     _transportadora,
                     _entregado_at,
                     _estado_envio),
                )
                synced += 1
            # Paginación cursor-based Link header rel=next
            next_url = None
            for part in link_hdr.split(','):
                if 'rel="next"' in part:
                    s = part.find('<') + 1
                    e = part.find('>')
                    if s > 0 and e > s:
                        next_url = part[s:e].strip()
            url = next_url
            conn.commit()   # commit POR PÁGINA (robustez · un sync profundo que corte no pierde lo traído)
        conn.commit()
        out['ok'] = True
        out['synced'] = synced
        _log(f'shopify_client · synced {synced} orders ({days}d window)')
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8', errors='replace')[:200]
        except Exception:
            err_body = ''
        out['error'] = f'Shopify HTTP {e.code} — {err_body}'
        return out
    except Exception as e:
        out['error'] = f'Error red Shopify: {e}'
        return out

    # Hook opcional · crear movimientos SHOPIFY_VENTA en kardex
    if incluir_movimientos:
        try:
            from blueprints.animus import _sync_shopify_a_movimientos
            vi = _sync_shopify_a_movimientos(conn)
            out['ventas_inventario'] = vi
        except Exception as e:
            out['error'] = (out.get('error') or '') + \
                f' · ventas_inventario falló: {e}'

    return out
