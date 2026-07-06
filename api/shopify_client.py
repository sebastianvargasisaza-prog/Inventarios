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
                conn.execute(
                    """INSERT OR REPLACE INTO animus_shopify_orders
                       (shopify_id, nombre, email, total, moneda, estado,
                        estado_pago, sku_items, unidades_total, ciudad,
                        pais, creado_en, synced_at, tags, customer_tags)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,
                               datetime('now', '-5 hours'), ?, ?)""",
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
                     cust_tags),
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
