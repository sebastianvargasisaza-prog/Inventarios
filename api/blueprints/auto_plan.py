"""
Auto-Plan Maestro — Sebastian + Alejandro (30-abr-2026)

"Tenemos algo maravilloso allí en planta... debe ser la herramienta más
avanzada del mundo, anclada y generada por Claude... usa toda tu capacidad
para que quede perfecta".

El motor que cada lunes a las 7am genera AUTOMÁTICAMENTE:
  1. Plan de producción próximas 8 semanas (solo L/M/V)
  2. Compras anticipadas de MP y envases
  3. Calendario de conteo cíclico (Ma/Ju)
  4. Emails ejecutivos a Sebastián, Alejandro, Catalina
  5. Agenda diaria por operario

Reglas (Sebastian, 30-abr-2026):
  - Vit C → cadencia 30d
  - Suero AH 1.5% → cadencia 90d, lote 90kg
  - Otros sueros/hidratantes/limpiadores → auto por umbral cobertura<30d
  - L/M/V producir, Ma/Ju acondicionar/envasar/conteo
  - MP mínimo 30d, ideal 60d
  - Envases mínimo 90d (China lead 180d)
  - Predicción agresiva exacta

Si dudas algo de MP → genera tarea "verificar existencia real".
"""
from flask import Blueprint, jsonify, request, session
from datetime import datetime, timedelta, date
import sqlite3
import json
import logging
from database import get_db
from config import ADMIN_USERS

bp = Blueprint('auto_plan', __name__)
log = logging.getLogger('auto_plan')

# Días de la semana donde SE PRODUCE (lunes=0, martes=1, ...)
DIAS_PRODUCCION = (0, 2, 4)        # lunes, miércoles, viernes
DIAS_ACOND_CONTEO = (1, 3)         # martes, jueves
DIAS_NO_LABORAL = (5, 6)           # sábado, domingo

# ───────────────────────────────────────────────────────────────────────
# UTILIDADES
# ───────────────────────────────────────────────────────────────────────

def _next_dia_produccion(desde_fecha):
    """Devuelve la próxima fecha L/M/V desde una fecha base."""
    f = desde_fecha
    while f.weekday() not in DIAS_PRODUCCION:
        f += timedelta(days=1)
    return f


def _proximo_dia_acond(desde_fecha):
    """Próximo Ma o Ju (para conteo cíclico / acondicionamiento)."""
    f = desde_fecha
    while f.weekday() not in DIAS_ACOND_CONTEO:
        f += timedelta(days=1)
    return f


def _ventas_diarias_por_sku(c, sku, dias=60):
    """Devuelve [(fecha, unidades)] de ventas del SKU en los últimos N días.

    Detecta automáticamente la tabla disponible:
      1) ventas_diarias (sku, fecha, cantidad) — si existe
      2) animus_shopify_orders.sku_items (JSON parse) — caso real Espagiria
      3) ordenes_shopify_items legacy
    """
    # Estrategia 1: tabla agregada
    try:
        r = c.execute("""
            SELECT fecha, COALESCE(SUM(cantidad),0)
            FROM ventas_diarias WHERE sku=? AND fecha >= date('now','-' || ? || ' days')
            GROUP BY fecha ORDER BY fecha
        """, (sku, dias)).fetchall()
        if r:
            return [(row[0], float(row[1] or 0)) for row in r]
    except Exception:
        pass

    # Estrategia 2: animus_shopify_orders con sku_items JSON
    try:
        rows = c.execute("""
            SELECT date(creado_en), sku_items
            FROM animus_shopify_orders
            WHERE creado_en >= date('now','-' || ? || ' days')
              AND sku_items IS NOT NULL AND sku_items != ''
        """, (dias,)).fetchall()
        if rows:
            por_dia = {}
            for fecha, sku_items_json in rows:
                if not fecha or not sku_items_json:
                    continue
                try:
                    items = json.loads(sku_items_json) if isinstance(sku_items_json, str) else sku_items_json
                except Exception:
                    continue
                if not isinstance(items, list):
                    continue
                cantidad = 0
                for it in items:
                    sk = (it.get('sku') or it.get('SKU') or '').strip()
                    if sk == sku:
                        cantidad += float(it.get('cantidad') or it.get('quantity') or 0)
                if cantidad > 0:
                    por_dia[fecha] = por_dia.get(fecha, 0) + cantidad
            return sorted([(f, q) for f, q in por_dia.items()])
    except Exception:
        pass

    # Estrategia 3: ordenes_shopify_items legacy
    try:
        r = c.execute("""
            SELECT date(fecha), COALESCE(SUM(cantidad),0)
            FROM ordenes_shopify_items
            WHERE sku=? AND fecha >= date('now','-' || ? || ' days')
            GROUP BY date(fecha) ORDER BY 1
        """, (sku, dias)).fetchall()
        if r:
            return [(row[0], float(row[1] or 0)) for row in r]
    except Exception:
        pass

    return []


def _velocidad_y_tendencia(c, sku):
    """Velocidad de venta diaria + factor de tendencia (regresión 30d).

    factor_tendencia:
      1.0 = estable · >1 = subiendo · <1 = bajando
    """
    rows = _ventas_diarias_por_sku(c, sku, dias=30)

    if not rows:
        # Sin datos. Fallback: consumo desde stock_pt (movimientos negativos = ventas)
        try:
            r = c.execute("""
                SELECT COALESCE(SUM(unidades_disponible),0) FROM stock_pt WHERE sku=?
            """, (sku,)).fetchone()
            stock_actual = float(r[0] if r else 0)
            # Si tiene stock, asumimos rotación trimestral conservadora (1 unit/dia)
            return (max(0.5, stock_actual / 90.0), 1.0)
        except Exception:
            return (0.0, 1.0)

    n = len(rows)
    if n < 5:
        avg = sum(q for _, q in rows) / max(1, n)
        return (float(avg), 1.0)

    # Regresión lineal sobre días reales (no índices) para captar tendencia
    xs = list(range(n))
    ys = [q for _, q in rows]
    sum_x = sum(xs); sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_xx = sum(x * x for x in xs)
    try:
        b = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        a = (sum_y - b * sum_x) / n
    except ZeroDivisionError:
        b = 0
        a = sum_y / n
    velocidad_actual = max(0.0, a + b * (n - 1))
    velocidad_inicial = max(0.01, a + b * 0)
    factor = velocidad_actual / velocidad_inicial if velocidad_inicial > 0 else 1.0
    factor = max(0.3, min(factor, 3.0))
    # Velocidad observada simple (suma / días totales) como fallback
    obs = sum(ys) / 30.0
    velocidad_final = max(velocidad_actual, obs)
    return (velocidad_final, factor)


def _stock_actual_pt(c, producto):
    """Stock total PT actual sumando todos los SKUs del producto."""
    rows = c.execute(
        "SELECT sku FROM sku_producto_map WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1",
        (producto,)
    ).fetchall()
    total = 0
    for (sku,) in rows:
        r = c.execute(
            "SELECT COALESCE(SUM(unidades_disponible),0) FROM stock_pt WHERE sku=?",
            (sku,)
        ).fetchone()
        if r:
            total += r[0] or 0
    return int(total)


def _velocidad_total_producto(c, producto):
    """Suma velocidades + tendencia agregada de todos los SKUs del producto."""
    rows = c.execute(
        "SELECT sku FROM sku_producto_map WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1",
        (producto,)
    ).fetchall()
    vel_total = 0.0
    factores = []
    for (sku,) in rows:
        v, f = _velocidad_y_tendencia(c, sku)
        vel_total += v
        if v > 0:
            factores.append(f)
    factor_avg = (sum(factores) / len(factores)) if factores else 1.0
    return (vel_total, factor_avg)


def _alias_calendar_for(c, producto):
    """Devuelve el alias_calendar configurado del producto, o None."""
    r = c.execute(
        "SELECT alias_calendar FROM sku_planeacion_config WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    return r[0] if r and r[0] else None


def _ultima_produccion(c, producto):
    """Fecha de última producción del producto. Usa matcher robusto."""
    fechas = []
    # BD
    r = c.execute("""
        SELECT MAX(fecha_programada) FROM produccion_programada
        WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
          AND estado IN ('completado','en_proceso','pendiente')
    """, (producto,)).fetchone()
    if r and r[0]:
        try:
            fechas.append(datetime.strptime(r[0][:10], '%Y-%m-%d').date())
        except Exception:
            pass
    # Calendar con matcher robusto
    eventos = _calendar_events_cached()
    alias = _alias_calendar_for(c, producto)
    for ev in eventos:
        score = _match_producto_evento(producto, alias, ev.get('titulo'), ev.get('descripcion', ''))
        if score >= 60:  # threshold de confianza
            try:
                fechas.append(datetime.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date())
            except Exception:
                pass
    return max(fechas) if fechas else None


def _historico_producciones_producto(c, producto, dias_atras=365):
    """Devuelve TODAS las fechas de producciones (BD + Calendar) con match robusto."""
    fechas = set()
    desde = (datetime.now().date() - timedelta(days=dias_atras)).isoformat()
    rows = c.execute("""
        SELECT fecha_programada FROM produccion_programada
        WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
          AND estado IN ('completado','en_proceso','pendiente')
          AND date(fecha_programada) >= ?
    """, (producto, desde)).fetchall()
    for r in rows:
        try:
            fechas.add(datetime.strptime(r[0][:10], '%Y-%m-%d').date())
        except Exception:
            pass
    # Calendar con matcher robusto
    eventos = _calendar_events_cached()
    alias = _alias_calendar_for(c, producto)
    for ev in eventos:
        score = _match_producto_evento(producto, alias, ev.get('titulo'), ev.get('descripcion', ''))
        if score >= 60:
            try:
                fechas.add(datetime.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date())
            except Exception:
                pass
    return sorted(fechas)


_CAL_CACHE = {'ts': None, 'events': []}

def _calendar_events_cached(force_refresh=False):
    """Lee Google Calendar una vez por minuto y cachea."""
    now = datetime.now()
    if not force_refresh and _CAL_CACHE['ts'] and (now - _CAL_CACHE['ts']).total_seconds() < 60:
        return _CAL_CACHE['events']
    try:
        from blueprints.programacion import _fetch_calendar_events
        result = _fetch_calendar_events(days_ahead=180) or {}
        _CAL_CACHE['events'] = result.get('events') or []
        _CAL_CACHE['ts'] = now
    except Exception:
        _CAL_CACHE['events'] = []
        _CAL_CACHE['ts'] = now
    return _CAL_CACHE['events']


# ════════════════════════════════════════════════════════════════════════
# MATCHING ROBUSTO producto ↔ evento Calendar (zero-error-enterprise)
# ════════════════════════════════════════════════════════════════════════
import re as _re_match
import unicodedata as _ud

# Stopwords que NO deben usarse para matching (palabras genéricas)
_MATCH_STOPWORDS = {
    'SUERO', 'CREMA', 'GEL', 'EMULSION', 'LIMPIADOR', 'CONTORNO',
    'OJOS', 'FACIAL', 'CORPORAL', 'HIDRATANTE', 'ILUMINADOR',
    'ANTIOXIDANTE', 'EXFOLIANTE', 'MASCARILLA', 'ESENCIA', 'NUEVA',
    'FORMULA', 'PARA', 'CON', 'DE', 'LA', 'EL', 'BHA', 'AHA',
}

def _normalizar(s):
    """Normaliza string: quita tildes, mayúsculas, trim, sin caracteres raros."""
    if not s:
        return ''
    s = _ud.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not _ud.combining(c))
    return s.upper().strip()


def _palabras_clave_unicas(producto_nombre):
    """Extrae palabras CLAVE únicas del producto (no stopwords, >2 chars)."""
    norm = _normalizar(producto_nombre)
    palabras = _re_match.findall(r'[A-Z0-9+]+', norm)
    return [p for p in palabras if len(p) >= 2 and p not in _MATCH_STOPWORDS]


def _match_producto_evento(producto_nombre, alias_csv, titulo_evento, descripcion=''):
    """Devuelve score de match (0-100) entre un producto y un evento de calendar.

    Algoritmo:
      - Score 100: alias EXACTO encontrado en título
      - Score 80-95: alias parcial + match palabras clave
      - Score 50-79: solo palabras clave únicas matchean
      - Score < 50: no match (probable falso positivo)
    """
    if not titulo_evento:
        return 0
    texto = _normalizar(titulo_evento + ' ' + (descripcion or ''))

    # 1) Alias exact match (máxima confianza)
    if alias_csv:
        for alias in alias_csv.split(','):
            alias_norm = _normalizar(alias)
            if not alias_norm or len(alias_norm) < 3:
                continue
            # Match palabra completa con boundaries
            patron = r'(^|[^A-Z0-9+])' + _re_match.escape(alias_norm) + r'($|[^A-Z0-9+])'
            if _re_match.search(patron, texto):
                return 100

    # 2) Match por palabras clave únicas del producto
    palabras_clave = _palabras_clave_unicas(producto_nombre)
    if not palabras_clave:
        return 0

    # Cuántas palabras clave del producto aparecen en el evento
    matched = 0
    for p in palabras_clave:
        if _re_match.search(r'(^|[^A-Z0-9+])' + _re_match.escape(p) + r'($|[^A-Z0-9+])', texto):
            matched += 1
    if matched == 0:
        return 0

    # Score: porcentaje de palabras clave matcheadas
    score = int((matched / len(palabras_clave)) * 80)  # max 80 sin alias
    # Bonus si el producto tiene UNA palabra clave única y aparece
    if len(palabras_clave) == 1 and matched == 1:
        score = max(score, 75)
    return score


def _parsear_kg_evento(titulo, descripcion=''):
    """Parser AGRESIVO de kg en título/descripción.

    Detecta:
      - "90 kg", "90kg", "90KG"
      - "90,5 kg", "90.5 kg"
      - "Lote 90", "Batch 90", "90 kilos"
      - "L90", "B90"
    """
    texto = (titulo or '') + ' ' + (descripcion or '')
    # Lista de patrones de mayor a menor confianza
    patrones = [
        r'(\d+(?:[.,]\d+)?)\s*(?:kg|KG|Kg|kG)\b',           # "90 kg" - alta confianza
        r'(\d+(?:[.,]\d+)?)\s*(?:kilos?|KILOS?)\b',          # "90 kilos"
        r'\b(?:lote|LOTE|Lote|batch|BATCH|Batch)\s+(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)?', # "Lote 90"
        r'\b(?:L|B)(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)\b',     # "L90 kg"
    ]
    for patron in patrones:
        m = _re_match.search(patron, texto)
        if m:
            kg_str = m.group(1).replace(',', '.')
            try:
                v = float(kg_str)
                if 0 < v <= 5000:  # rango razonable
                    return v
            except Exception:
                pass
    return None


def _producciones_programadas_futuro(c, producto):
    """Cantidad de lotes programados a futuro (no completados)."""
    r = c.execute("""
        SELECT COALESCE(SUM(lotes), 0) FROM produccion_programada
        WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
          AND estado IN ('pendiente','en_proceso')
          AND fecha_programada >= date('now')
    """, (producto,)).fetchone()
    return int(r[0] if r else 0)


# ───────────────────────────────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ───────────────────────────────────────────────────────────────────────

def generar_plan(horizonte_dias=60, tipo='auto', usuario='cron'):
    """Algoritmo central. Genera plan completo para los próximos N días.

    Devuelve dict con:
      producciones_propuestas: lista de dicts con producción a crear
      compras_propuestas: SOL automáticas de MP y envases
      conteos_propuestos: calendario conteo cíclico
      alertas: lista de alertas críticas
      log: lineas paso a paso
    """
    inicio = datetime.now()
    conn = get_db(); c = conn.cursor()

    log_lineas = []
    log_lineas.append(f"🤖 Generación auto-plan iniciada {inicio.isoformat()}")
    log_lineas.append(f"   Horizonte: {horizonte_dias}d · tipo={tipo} · usuario={usuario}")

    fecha_hoy = datetime.now().date()
    fecha_fin = fecha_hoy + timedelta(days=horizonte_dias)

    # 1. Cargar configs
    skus = c.execute("""
        SELECT spc.producto_nombre, spc.categoria, spc.cadencia_dias,
               spc.cobertura_target_dias, spc.cobertura_min_dias, spc.cobertura_max_dias,
               spc.merma_pct, spc.prioridad,
               fh.lote_size_kg
        FROM sku_planeacion_config spc
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(spc.producto_nombre))
        WHERE spc.activo = 1
        ORDER BY spc.prioridad, spc.producto_nombre
    """).fetchall()

    log_lineas.append(f"   Productos en config: {len(skus)}")

    # 2. Para cada SKU decidir si producir y cuándo
    producciones_propuestas = []
    alertas = []
    fechas_ocupadas = {}  # area_codigo -> set de fechas ocupadas
    # Sebastian (30-abr-2026): contador de lotes proyectados POR FECHA en
    # memoria — antes el counter solo miraba BD y todas las proyecciones
    # caían el mismo día. Ahora distribuimos máx 2 lotes por día L/M/V.
    LOTES_MAX_POR_DIA = 2
    lotes_por_fecha = {}  # ISO date → count

    for sku_row in skus:
        producto, categoria, cadencia, cob_target, cob_min, cob_max, merma_pct, prioridad, lote_size_kg = sku_row
        # Sebastian (30-abr-2026): "todo debe producirse con un margen de 20
        # dias antes de que se agote" — usar 20d como umbral mínimo de
        # disparo, anulando el cob_min de la config si era mayor.
        cob_min = min(cob_min or 30, 20)
        if not lote_size_kg:
            log_lineas.append(f"   ⊘ {producto}: sin lote_size_kg en formula — saltado")
            continue

        velocidad, factor_tendencia = _velocidad_total_producto(c, producto)
        stock_actual = _stock_actual_pt(c, producto)
        ultima_prod = _ultima_produccion(c, producto)
        prog_futuro_lotes = _producciones_programadas_futuro(c, producto)

        # Velocidad ajustada por tendencia (Sebastian: "predicción agresiva")
        velocidad_proyectada = velocidad * factor_tendencia

        # Días de inventario actuales (con tendencia)
        if velocidad_proyectada > 0:
            dias_inv_actual = stock_actual / velocidad_proyectada
        else:
            dias_inv_actual = None

        # ¿Toca producir?
        razon = ''
        toca = False
        if cadencia and ultima_prod:
            dias_desde_ult = (fecha_hoy - ultima_prod).days
            if dias_desde_ult >= cadencia:
                toca = True
                razon = f'cadencia {cadencia}d cumplida ({dias_desde_ult}d desde {ultima_prod})'
        if not toca and dias_inv_actual is not None and dias_inv_actual < cob_min:
            toca = True
            razon = f'cobertura {dias_inv_actual:.0f}d < mínimo {cob_min}d'
        if not toca and dias_inv_actual is not None and dias_inv_actual < cob_target and prog_futuro_lotes == 0:
            toca = True
            razon = f'cobertura {dias_inv_actual:.0f}d < target {cob_target}d (sin prods futuras)'

        if not toca:
            continue

        # Calcular tamaño del lote: cubrir hasta cob_target con tendencia
        unidades_a_cubrir = velocidad_proyectada * cob_target
        # Aplicar merma al lote en kg
        kg_base = (lote_size_kg or 0)
        # ¿Cuántos lotes? Si la velocidad pide más de 1 lote, sugiere múltiples
        # Pero por simplicidad inicial: 1 lote = lote_size_kg, ajusta cantidad de lotes
        lotes_necesarios = 1
        # Si las unidades a cubrir × peso_g_unidad > lote_size, multiplicar lotes
        # Heurística: si velocidad × cob_target > 1.5 × velocidad × cadencia → 2 lotes
        # Por ahora: 1 lote, registramos kg con merma para que CC compre lo correcto
        kg_con_merma = kg_base * (1 + merma_pct / 100.0)

        # Asignar fecha L/M/V que no esté ocupada (BD + proyecciones en memoria)
        if ultima_prod and cadencia:
            base_fecha = ultima_prod + timedelta(days=cadencia)
        else:
            base_fecha = fecha_hoy + timedelta(days=2)
        fecha_objetivo = _next_dia_produccion(max(fecha_hoy + timedelta(days=2), base_fecha))
        # Iterar hasta encontrar día con cupo (BD + memoria), saltando L/M/V
        for _ in range(40):  # hasta 40 intentos para horizonte largo
            iso = fecha_objetivo.isoformat()
            ya_hay_bd = c.execute("""
                SELECT COUNT(*) FROM produccion_programada
                WHERE date(fecha_programada) = ? AND estado IN ('pendiente','en_proceso')
            """, (iso,)).fetchone()[0]
            ya_hay_proj = lotes_por_fecha.get(iso, 0)
            total = ya_hay_bd + ya_hay_proj
            if total < LOTES_MAX_POR_DIA:
                break
            fecha_objetivo = _next_dia_produccion(fecha_objetivo + timedelta(days=1))
        # Reservar el slot
        iso = fecha_objetivo.isoformat()
        lotes_por_fecha[iso] = lotes_por_fecha.get(iso, 0) + 1

        producciones_propuestas.append({
            'producto': producto,
            'categoria': categoria,
            'fecha_programada': fecha_objetivo.isoformat(),
            'lotes': lotes_necesarios,
            'lote_size_kg': lote_size_kg,
            'kg_con_merma': round(kg_con_merma, 2),
            'merma_pct': merma_pct,
            'velocidad_dia': round(velocidad, 2),
            'tendencia': round(factor_tendencia, 2),
            'velocidad_proyectada': round(velocidad_proyectada, 2),
            'stock_actual': stock_actual,
            'dias_inv_actual': round(dias_inv_actual, 1) if dias_inv_actual else None,
            'cobertura_target': cob_target,
            'razon': razon,
            'prioridad': prioridad,
        })
        log_lineas.append(f"   ✓ {producto[:40]:40} → {fecha_objetivo} · {kg_con_merma:.0f}kg · {razon}")

    log_lineas.append(f"   Producciones propuestas: {len(producciones_propuestas)}")

    # 3. Calcular compras anticipadas (MP + envases)
    consumo_acumulado = {}  # material_id -> g requeridos por todo el plan
    for prop in producciones_propuestas:
        items = c.execute("""
            SELECT material_id, material_nombre, COALESCE(cantidad_g_por_lote, 0), porcentaje
            FROM formula_items
            WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
        """, (prop['producto'],)).fetchall()
        for mat_id, mat_nom, cant_lote_g, pct in items:
            req_g = (cant_lote_g or 0) * prop['lotes']
            if not req_g and pct:
                req_g = (pct / 100.0) * (prop['lote_size_kg'] or 0) * 1000 * prop['lotes']
            req_g = req_g * (1 + prop['merma_pct'] / 100.0)
            consumo_acumulado[mat_id] = consumo_acumulado.get(mat_id, 0) + req_g

    compras_propuestas = []
    for mat_id, req_g in consumo_acumulado.items():
        # Stock actual
        stock = c.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN tipo IN ('Ingreso','Ajuste','Devolucion') THEN cantidad
                     WHEN tipo IN ('Salida','Consumo') THEN -cantidad
                     ELSE 0 END
            ), 0) FROM movimientos WHERE material_id=?
        """, (mat_id,)).fetchone()
        stock_g = float(stock[0] if stock else 0)
        # Lead time + buffer
        lt = c.execute("""
            SELECT lead_time_dias, buffer_dias, cobertura_min_dias, cobertura_ideal_dias,
                   origen, es_envase, proveedor_principal, material_nombre
            FROM mp_lead_time_config WHERE material_id=?
        """, (mat_id,)).fetchone()
        if lt:
            lead, buffer, cob_min, cob_ideal, origen, es_envase, prov, nombre = lt
        else:
            lead, buffer, cob_min, cob_ideal, origen, es_envase, prov, nombre = 14, 30, 30, 60, 'local', 0, '', mat_id
        # ¿Falta?
        deficit_g = req_g - stock_g
        if deficit_g <= 0:
            continue
        # Cuánto pedir: deficit + cobertura ideal extra
        cantidad_a_pedir_g = deficit_g + (req_g / horizonte_dias * cob_ideal)
        # Urgencia
        if origen in ('china', 'usa', 'europa') and stock_g < req_g * 0.5:
            urgencia = 'critica'
        elif stock_g < req_g * 0.3:
            urgencia = 'critica'
        elif stock_g < req_g * 0.6:
            urgencia = 'alta'
        else:
            urgencia = 'normal'
        compras_propuestas.append({
            'material_id': mat_id,
            'material_nombre': nombre or mat_id,
            'requerido_g': round(req_g),
            'stock_actual_g': round(stock_g),
            'deficit_g': round(deficit_g),
            'cantidad_a_pedir_g': round(cantidad_a_pedir_g),
            'lead_time_dias': lead,
            'origen': origen,
            'es_envase': bool(es_envase),
            'proveedor_principal': prov,
            'urgencia': urgencia,
        })

    log_lineas.append(f"   Compras propuestas: {len(compras_propuestas)} ({sum(1 for c in compras_propuestas if c['urgencia']=='critica')} críticas)")

    # 4. Conteo cíclico para Martes/Jueves
    conteos_propuestos = []
    cursor_dia = _proximo_dia_acond(fecha_hoy + timedelta(days=1))
    materiales_a_contar = c.execute("""
        SELECT cc.material_id, cc.categoria_abc, cc.frecuencia_dias, cc.ultimo_conteo_fecha,
               COALESCE(mlt.material_nombre, cc.material_id)
        FROM conteo_ciclico_config cc
        LEFT JOIN mp_lead_time_config mlt ON mlt.material_id = cc.material_id
        ORDER BY
          CASE cc.categoria_abc WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END,
          COALESCE(cc.ultimo_conteo_fecha, '0000-01-01') ASC
    """).fetchall()
    # Filtrar materiales que toquen contar
    contar_hoy = []
    for mat_id, cat_abc, frec, ult, nom in materiales_a_contar:
        if ult:
            try:
                ult_d = datetime.fromisoformat(ult.split('T')[0]).date()
                if (fecha_hoy - ult_d).days < (frec or 90):
                    continue
            except Exception:
                pass
        contar_hoy.append((mat_id, cat_abc, nom))
    # Distribuir uno por Ma/Ju, max 5 por día
    while contar_hoy and cursor_dia <= fecha_fin:
        if cursor_dia.weekday() in DIAS_ACOND_CONTEO:
            chunk = contar_hoy[:5]
            for mat_id, cat_abc, nom in chunk:
                conteos_propuestos.append({
                    'fecha': cursor_dia.isoformat(),
                    'material_id': mat_id,
                    'material_nombre': nom,
                    'categoria_abc': cat_abc,
                    'asignado_a': 'milton,operarios',
                })
            contar_hoy = contar_hoy[5:]
        cursor_dia = _proximo_dia_acond(cursor_dia + timedelta(days=1))

    log_lineas.append(f"   Conteos cíclicos: {len(conteos_propuestos)}")

    # 5. Compilar alertas críticas
    for cp in compras_propuestas:
        if cp['urgencia'] == 'critica':
            alertas.append({
                'tipo': 'compra_critica',
                'severidad': 'critica' if cp['origen'] == 'china' else 'alta',
                'titulo': f'⚠ {cp["material_nombre"]}: déficit {cp["deficit_g"]:.0f}g · lead {cp["lead_time_dias"]}d ({cp["origen"]})',
                'detalle': cp,
            })

    duracion_ms = int((datetime.now() - inicio).total_seconds() * 1000)
    log_lineas.append(f"   ⏱ Generación completada en {duracion_ms}ms")

    return {
        'producciones_propuestas': producciones_propuestas,
        'compras_propuestas': compras_propuestas,
        'conteos_propuestos': conteos_propuestos,
        'alertas': alertas,
        'log': log_lineas,
        'duracion_ms': duracion_ms,
        'horizonte_dias': horizonte_dias,
        'fecha_hoy': fecha_hoy.isoformat(),
        'fecha_fin': fecha_fin.isoformat(),
    }


def aplicar_plan(plan, usuario='cron'):
    """Aplica el plan generado: crea produccion_programada, solicitudes_compra,
    conteo_ciclico_calendario.

    Devuelve dict con counts e ids creados.
    """
    conn = get_db(); c = conn.cursor()
    creadas_prod = []
    creadas_compras = []
    creadas_conteos = []

    for prop in plan['producciones_propuestas']:
        # Verificar si ya hay una producción para ese mismo producto+fecha
        existing = c.execute("""
            SELECT id FROM produccion_programada
            WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
              AND date(fecha_programada) = ?
              AND estado IN ('pendiente','en_proceso')
        """, (prop['producto'], prop['fecha_programada'])).fetchone()
        if existing:
            continue

        # Sumar pedidos de maquila al lote (Sebastian: "si Fernando lleva 500
        # le adiciona a la producción esas 500 unidades").
        # Considera misma fórmula (comparte_formula_con) → Kelly Guerra para Animus
        kg_extra_maquila = 0
        pedidos_maquila_asociar = []
        try:
            mq_rows = c.execute("""
                SELECT mp.id, mp.kg_estimados, mp.cliente_nombre
                FROM maquila_pedidos mp
                LEFT JOIN clientes_maquila cm ON cm.id = mp.cliente_id
                WHERE mp.estado = 'recibido'
                  AND mp.produccion_id IS NULL
                  AND (
                      UPPER(TRIM(mp.producto_nombre)) = UPPER(TRIM(?))
                   OR (cm.comparte_formula_con IS NOT NULL
                       AND UPPER(TRIM(?)) IN (
                           SELECT UPPER(TRIM(producto_nombre)) FROM formula_headers
                           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(mp.producto_nombre))
                       ))
                  )
            """, (prop['producto'], prop['producto'])).fetchall()
            for mq in mq_rows:
                kg_extra_maquila += (mq[1] or 0)
                pedidos_maquila_asociar.append(mq[0])
        except Exception:
            pass

        kg_total = prop['kg_con_merma'] + kg_extra_maquila
        obs_extra = ''
        if kg_extra_maquila > 0:
            obs_extra = f' | Maquila: +{kg_extra_maquila:.1f}kg para {len(pedidos_maquila_asociar)} pedido(s)'

        cur = c.execute("""
            INSERT INTO produccion_programada
              (producto, fecha_programada, lotes, estado, observaciones, origen, cantidad_kg)
            VALUES (?, ?, ?, 'pendiente', ?, 'auto_plan', ?)
        """, (
            prop['producto'], prop['fecha_programada'], prop['lotes'],
            f"AUTO-PLAN ({plan['fecha_hoy']}): {prop['razon']}{obs_extra}",
            kg_total,
        ))
        creadas_prod.append(cur.lastrowid)

        # Asociar pedidos de maquila a esta producción
        for mq_id in pedidos_maquila_asociar:
            c.execute(
                "UPDATE maquila_pedidos SET produccion_id=?, estado='planificado', actualizado_en=datetime('now') WHERE id=?",
                (cur.lastrowid, mq_id)
            )

        # Asignar área automáticamente (sugerir-area)
        try:
            cap_min = (prop['kg_con_merma'] or 0) * 1.2
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
            for area_codigo, _cap in por_area.items():
                area_chk = c.execute(
                    "SELECT id, puede_producir, activo FROM areas_planta WHERE codigo=?",
                    (area_codigo,)
                ).fetchone()
                if area_chk and area_chk[1] and area_chk[2]:
                    c.execute("UPDATE produccion_programada SET area_id=? WHERE id=?",
                              (area_chk[0], cur.lastrowid))
                    break
        except Exception as e:
            log.warning(f'Asignación área fallida prod={cur.lastrowid}: {e}')

        # Asignar operarios automáticamente
        try:
            _asignar_operarios_a_produccion(conn, cur.lastrowid)
        except Exception as e:
            log.warning(f'Asignación operarios fallida prod={cur.lastrowid}: {e}')

    for cp in plan['compras_propuestas']:
        # Crear solicitud_compra automatizada
        # Numero unico
        next_n = c.execute("""
            SELECT COALESCE(MAX(CAST(SUBSTR(numero, 6) AS INTEGER)), 0) + 1
            FROM solicitudes_compra WHERE numero LIKE 'AUTO-%'
        """).fetchone()[0] or 1
        numero = f'AUTO-{next_n:04d}'
        cantidad_kg = round(cp['cantidad_a_pedir_g'] / 1000.0, 2)
        urgencia_solic = 'Urgente' if cp['urgencia'] == 'critica' else ('Alta' if cp['urgencia'] == 'alta' else 'Normal')
        try:
            cur = c.execute("""
                INSERT INTO solicitudes_compra
                  (numero, fecha, estado, solicitante, urgencia,
                   observaciones, area, empresa, categoria, tipo, valor)
                VALUES (?, date('now'), 'Pendiente', 'AUTO-PLAN', ?, ?, 'Producción', 'Espagiria',
                        ?, 'Compra', 0)
            """, (
                numero, urgencia_solic,
                f"AUTO-PLAN: {cp['material_nombre']} {cantidad_kg}kg · lead {cp['lead_time_dias']}d ({cp['origen']}) · déficit {cp['deficit_g']:.0f}g",
                'Materia Prima' if not cp['es_envase'] else 'Material de Empaque',
            ))
            sol_id = cur.lastrowid
            # Item asociado
            c.execute("""
                INSERT INTO solicitudes_compra_items
                  (numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion, valor_estimado, proveedor_sugerido)
                VALUES (?, ?, ?, ?, 'g', ?, 0, ?)
            """, (
                numero, cp['material_id'], cp['material_nombre'],
                cp['cantidad_a_pedir_g'],
                f"Para producciones plan {plan['fecha_hoy']}",
                cp.get('proveedor_principal') or '',
            ))
            creadas_compras.append({'numero': numero, 'sol_id': sol_id})
        except Exception as e:
            log.warning(f'Solicitud auto-plan fallida {cp["material_id"]}: {e}')

    for con in plan['conteos_propuestos']:
        try:
            c.execute("""
                INSERT OR IGNORE INTO conteo_ciclico_calendario
                  (fecha, material_id, material_nombre, categoria_abc, asignado_a, generado_por)
                VALUES (?, ?, ?, ?, ?, 'auto_plan')
            """, (con['fecha'], con['material_id'], con['material_nombre'],
                  con['categoria_abc'], con['asignado_a']))
            if c.rowcount:
                creadas_conteos.append(con)
        except Exception as e:
            log.warning(f'Conteo auto-plan fallido {con["material_id"]}: {e}')

    # Log de la corrida
    c.execute("""
        INSERT INTO auto_plan_runs
          (ejecutado_por, tipo, horizonte_dias, producciones_creadas,
           compras_creadas, alertas_criticas, payload_json, duracion_ms)
        VALUES (?, 'auto', ?, ?, ?, ?, ?, ?)
    """, (
        usuario, plan['horizonte_dias'],
        len(creadas_prod), len(creadas_compras), len(plan.get('alertas', [])),
        json.dumps({'log': plan['log'][:50]}, ensure_ascii=False),
        plan['duracion_ms'],
    ))
    conn.commit()

    return {
        'producciones_creadas': creadas_prod,
        'compras_creadas': creadas_compras,
        'conteos_creados': creadas_conteos,
    }


# ───────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ───────────────────────────────────────────────────────────────────────

def _auth():
    if 'compras_user' not in session:
        return None, jsonify({'error': 'No autorizado'}), 401
    return session.get('compras_user', ''), None, None


@bp.route('/api/auto-plan/preview', methods=['GET'])
def auto_plan_preview():
    """Genera el plan en modo dry-run (no aplica). Sebastian ve qué propondría."""
    u, err, code = _auth()
    if err:
        return err, code
    try:
        horizonte = int(request.args.get('dias', 60))
    except Exception:
        horizonte = 60
    plan = generar_plan(horizonte_dias=horizonte, tipo='dry_run', usuario=u)
    return jsonify(plan)


@bp.route('/api/auto-plan/aplicar', methods=['POST'])
def auto_plan_aplicar():
    """Genera y aplica el plan ahora mismo (manual trigger)."""
    u, err, code = _auth()
    if err:
        return err, code
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin puede disparar el auto-plan'}), 403
    try:
        horizonte = int((request.json or {}).get('dias', 60))
    except Exception:
        horizonte = 60
    plan = generar_plan(horizonte_dias=horizonte, tipo='manual', usuario=u)
    resultado = aplicar_plan(plan, usuario=u)
    return jsonify({
        'ok': True,
        'resultado': resultado,
        'plan': {
            'producciones_propuestas': len(plan['producciones_propuestas']),
            'compras_propuestas': len(plan['compras_propuestas']),
            'conteos_propuestos': len(plan['conteos_propuestos']),
            'alertas': plan['alertas'],
            'log': plan['log'],
        },
    })


@bp.route('/api/auto-plan/ejecutar-ahora', methods=['POST'])
def auto_plan_ejecutar_ahora():
    """Dispara el cron auto-plan AHORA (sin esperar al 7am del próximo día).
    Útil para test inicial o cuando Sebastian quiere refrescar el plan."""
    u, err, code = _auth()
    if err:
        return err, code
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin'}), 403
    try:
        from blueprints.auto_plan_jobs import ejecutar_auto_plan_diario
        from flask import current_app
        # Ejecutar en background para no bloquear el response
        import threading
        threading.Thread(
            target=ejecutar_auto_plan_diario,
            args=(current_app._get_current_object(),),
            daemon=True
        ).start()
        return jsonify({'ok': True, 'mensaje': 'Auto-plan ejecutándose en background. Mira /api/auto-plan/runs en 30s.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/auto-plan/asegurar-actualizado', methods=['POST'])
def auto_plan_asegurar_actualizado():
    """Sebastian (30-abr-2026): "que el cronograma sea de manera inteligente
    osea montado desde shopify, necesidades reales, monte todo con la lógica
    que hemos usado en calendario asi esta todo en la app".

    Llamada al cargar /planta. Verifica si el último auto-plan run fue hace
    más de N horas (default 12). Si sí, dispara generar+aplicar en BACKGROUND
    sin bloquear el response. El frontend muestra el plan y se refresca solo
    cuando el cron termina.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        max_horas = int(request.args.get('max_horas', 12))
    except Exception:
        max_horas = 12

    conn = get_db(); c = conn.cursor()
    last = c.execute("""
        SELECT id, ejecutado_at,
               CAST((julianday('now') - julianday(ejecutado_at)) * 24 AS INTEGER) AS horas
        FROM auto_plan_runs
        WHERE error IS NULL OR error = ''
        ORDER BY id DESC LIMIT 1
    """).fetchone()

    if last and last[2] is not None and last[2] < max_horas:
        return jsonify({
            'ok': True,
            'ejecutado': False,
            'razon': f'Plan vigente · último run hace {last[2]}h',
            'ultimo_run_at': last[1],
        })

    # Disparar en background
    try:
        from blueprints.auto_plan_jobs import ejecutar_auto_plan_diario
        from flask import current_app
        import threading
        threading.Thread(
            target=ejecutar_auto_plan_diario,
            args=(current_app._get_current_object(),),
            daemon=True
        ).start()
        return jsonify({
            'ok': True,
            'ejecutado': True,
            'mensaje': 'Auto-plan ejecutándose en background. El plan se actualizará en ~30 segundos.',
            'ultimo_run_at': last[1] if last else None,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/planta/plan-semanal-v2', methods=['GET'])
def plan_semanal_v2():
    """Sebastian (30-abr-2026): vista Semana siempre con datos.

    Si BD tiene producciones programadas → muéstralas (origen='bd').
    Si BD vacía → proyecta los próximos 14 días con el motor (origen='proyeccion').
    Cada item lleva flag de origen para que la UI muestre badge "🔮 Proyectado".

    Querystring: ?dias=14 (default)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 14))
    except Exception:
        dias = 14

    conn = get_db(); c = conn.cursor()
    fecha_desde = datetime.now().strftime('%Y-%m-%d')
    fecha_hasta = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')

    # Producciones reales en BD
    rows = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes, pp.estado,
               ap.codigo as area_codigo, ap.nombre as area_nombre,
               fh.lote_size_kg, fh.imagen_url, pp.cantidad_kg
        FROM produccion_programada pp
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
        WHERE pp.fecha_programada BETWEEN ? AND ?
          AND pp.estado IN ('pendiente','en_proceso')
        ORDER BY pp.fecha_programada ASC, pp.id ASC
    """, (fecha_desde, fecha_hasta)).fetchall()

    items_bd = []
    for r in rows:
        items_bd.append({
            'origen': 'bd',
            'produccion_id': r[0],
            'producto': r[1],
            'fecha_programada': r[2],
            'lotes': r[3] or 1,
            'estado': r[4],
            'area_codigo': r[5],
            'area_nombre': r[6],
            'lote_size_kg': r[7],
            'imagen_url': r[8],
            'kg': r[9] or r[7] or 0,
        })

    items_proy = []
    if not items_bd:
        # BD vacía → proyectar
        proy = _generar_proyeccion_lotes(c, max(1, dias // 30 + 1))
        # Solo los próximos 'dias' días
        from datetime import datetime as _dt2
        fecha_limite = _dt2.now().date() + timedelta(days=dias)
        for p in proy:
            try:
                f = _dt2.strptime(p['fecha'], '%Y-%m-%d').date()
                if f > fecha_limite:
                    continue
            except Exception:
                continue
            # Buscar imagen del producto
            img = c.execute(
                "SELECT imagen_url FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
                (p['producto'],)
            ).fetchone()
            items_proy.append({
                'origen': 'proyeccion',
                'produccion_id': None,  # aún no existe
                'producto': p['producto'],
                'fecha_programada': p['fecha'],
                'lotes': 1,
                'estado': 'sugerido',
                'area_codigo': None,
                'area_nombre': None,
                'lote_size_kg': p['lote_kg'],
                'imagen_url': img[0] if img else None,
                'kg': p['kg_con_merma'],
                'razon': f"Cadencia {p['cadencia_dias']}d" if p.get('cadencia_dias') else 'Auto por umbral',
            })

    items = items_bd + items_proy
    items.sort(key=lambda x: x['fecha_programada'])

    # Last run info
    last_run = c.execute("""
        SELECT ejecutado_at,
               CAST((julianday('now') - julianday(ejecutado_at)) * 24 AS INTEGER) AS horas
        FROM auto_plan_runs ORDER BY id DESC LIMIT 1
    """).fetchone()

    return jsonify({
        'rango': {'desde': fecha_desde, 'hasta': fecha_hasta, 'dias': dias},
        'items': items,
        'kpis': {
            'total': len(items),
            'desde_bd': len(items_bd),
            'proyectadas': len(items_proy),
        },
        'auto_plan_status': {
            'ultimo_run_at': last_run[0] if last_run else None,
            'horas_desde_run': last_run[1] if last_run and last_run[1] is not None else None,
            'plan_vacio': len(items_bd) == 0,
        },
    })


@bp.route('/api/planta/confirmar-proyeccion', methods=['POST'])
def confirmar_proyeccion():
    """Cuando el operario ve una proyección y la quiere persistir como
    producción real, este endpoint la mete en produccion_programada.
    Body: {producto, fecha_programada, lotes?, lote_size_kg?, kg?}"""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    producto = (d.get('producto') or '').strip()
    fecha = (d.get('fecha_programada') or '').strip()
    if not producto or not fecha:
        return jsonify({'error': 'producto y fecha_programada requeridos'}), 400
    conn = get_db(); c = conn.cursor()
    # Verificar duplicado
    existing = c.execute("""
        SELECT id FROM produccion_programada
        WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))
          AND date(fecha_programada)=date(?)
          AND estado IN ('pendiente','en_proceso')
    """, (producto, fecha)).fetchone()
    if existing:
        return jsonify({'ok': True, 'id': existing[0], 'ya_existia': True})
    kg_total = float(d.get('kg') or d.get('lote_size_kg') or 0)
    cur = c.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, observaciones, origen, cantidad_kg)
        VALUES (?, ?, ?, 'pendiente', ?, 'confirmacion_manual', ?)
    """, (
        producto, fecha, int(d.get('lotes') or 1),
        f'Confirmado desde proyección por {user} el {datetime.now().isoformat()}',
        kg_total,
    ))
    nuevo_id = cur.lastrowid
    # Auto-asignar área + operarios
    try:
        if kg_total > 0:
            cap_min = kg_total * 1.2
            tanques = c.execute("""
                SELECT area_codigo FROM equipos_planta
                WHERE activo=1 AND tipo IN ('tanque','marmita','olla')
                  AND capacidad_litros >= ?
                ORDER BY capacidad_litros ASC LIMIT 1
            """, (cap_min,)).fetchone()
            if tanques:
                area_chk = c.execute(
                    "SELECT id FROM areas_planta WHERE codigo=? AND puede_producir=1 AND activo=1",
                    (tanques[0],)
                ).fetchone()
                if area_chk:
                    c.execute("UPDATE produccion_programada SET area_id=? WHERE id=?",
                              (area_chk[0], nuevo_id))
        _asignar_operarios_a_produccion(conn, nuevo_id)
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'id': nuevo_id, 'ya_existia': False})


@bp.route('/api/planta/produccion/<int:prod_id>/eliminar-y-replanificar', methods=['POST'])
def eliminar_y_replan(prod_id):
    """Sebastian (30-abr-2026): "si ya la hicimos le demos eliminar, y ponga
    otra alli automaticamente".

    Elimina la producción y propone otra del MISMO producto en la próxima
    fecha disponible según cadencia/cobertura.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    motivo = (d.get('motivo') or 'Eliminada manualmente').strip()
    conn = get_db(); c = conn.cursor()

    # Obtener datos de la producción antes de borrarla
    pp = c.execute("""
        SELECT producto, fecha_programada, lotes, cantidad_kg
        FROM produccion_programada WHERE id=?
    """, (prod_id,)).fetchone()
    if not pp:
        return jsonify({'error': 'Producción no existe'}), 404
    producto, fecha_orig, lotes, kg = pp

    # Marcar como cancelada (no eliminamos para no perder histórico)
    c.execute("""
        UPDATE produccion_programada SET
          estado='cancelado',
          observaciones=COALESCE(observaciones,'')||' | Cancelada por '||?||': '||?
        WHERE id=?
    """, (user, motivo, prod_id))

    # Calcular próxima fecha sugerida según cadencia
    cfg = c.execute("""
        SELECT cadencia_dias, cobertura_target_dias, cobertura_min_dias, merma_pct
        FROM sku_planeacion_config
        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
    """, (producto,)).fetchone()
    cadencia = cfg[0] if cfg else None
    cob_target = cfg[1] if cfg else 60

    velocidad, factor = _velocidad_total_producto(c, producto)
    velocidad_proj = max(0.5, velocidad * factor)
    stock_actual = _stock_actual_pt(c, producto)

    # Si tiene cadencia → próxima = fecha_orig + cadencia
    # Si no → cuando bajará bajo umbral 20d
    from datetime import datetime as _dt2
    fecha_orig_dt = _dt2.strptime(fecha_orig[:10], '%Y-%m-%d').date() if fecha_orig else _dt2.now().date()
    if cadencia:
        proxima = fecha_orig_dt + timedelta(days=cadencia)
    else:
        # Días hasta bajar de 20
        dias_disp = max(0, (stock_actual / velocidad_proj) - 20)
        proxima = _dt2.now().date() + timedelta(days=int(dias_disp))
    # Asegurar L/M/V
    while proxima.weekday() not in (0, 2, 4):
        proxima += timedelta(days=1)

    # Crear nueva producción sugerida
    cur = c.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, observaciones, origen, cantidad_kg)
        VALUES (?, ?, ?, 'pendiente', ?, 'replan_post_eliminacion', ?)
    """, (
        producto, proxima.isoformat(), lotes or 1,
        f'Replanificada tras cancelación de id={prod_id}',
        kg or 0,
    ))
    nuevo_id = cur.lastrowid
    conn.commit()
    return jsonify({
        'ok': True,
        'eliminado': prod_id,
        'nueva_id': nuevo_id,
        'nueva_fecha': proxima.isoformat(),
        'producto': producto,
        'mensaje': f'Producción cancelada · nueva sugerida para {proxima.isoformat()}',
    })


@bp.route('/api/planta/produccion/<int:prod_id>/editar-lote', methods=['POST'])
def editar_lote(prod_id):
    """Sebastian (30-abr-2026): "permita editar la cantidad del lote y
    calcule todo".

    Body: {cantidad_kg: float, lotes?: int}
    Recalcula MP requerida + envases + costos al cambiar tamaño.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    nueva_kg = d.get('cantidad_kg')
    if nueva_kg is None:
        return jsonify({'error': 'cantidad_kg requerido'}), 400
    nueva_kg = float(nueva_kg)
    nuevos_lotes = int(d.get('lotes') or 1)
    conn = get_db(); c = conn.cursor()

    pp = c.execute(
        "SELECT producto, lotes, cantidad_kg FROM produccion_programada WHERE id=?",
        (prod_id,)
    ).fetchone()
    if not pp:
        return jsonify({'error': 'Producción no existe'}), 404
    producto, lotes_actuales, kg_actuales = pp

    c.execute("""
        UPDATE produccion_programada SET
          cantidad_kg=?, lotes=?,
          observaciones=COALESCE(observaciones,'')||' | Lote editado por '||?||' '||datetime('now')||': '||?||'kg→'||?||'kg'
        WHERE id=?
    """, (nueva_kg, nuevos_lotes, user, kg_actuales or 0, nueva_kg, prod_id))
    conn.commit()

    # Recalcular MP requerida + envases con el nuevo tamaño
    fh = c.execute(
        "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    lote_kg_base = (fh[0] if fh else 0) or 0
    factor = nueva_kg / lote_kg_base if lote_kg_base else 1
    items = c.execute("""
        SELECT material_id, material_nombre, COALESCE(cantidad_g_por_lote,0)
        FROM formula_items
        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
    """, (producto,)).fetchall()
    mp_recalc = []
    for mat_id, mat_nom, cant_g in items:
        nueva_g = (cant_g or 0) * factor * nuevos_lotes
        mp_recalc.append({'material_id': mat_id, 'material_nombre': mat_nom,
                          'gramos_requeridos': round(nueva_g)})

    # Envases recalculados
    pres = c.execute("""
        SELECT envase_codigo, factor_g_por_unidad, etiqueta
        FROM producto_presentaciones
        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND activo=1 AND es_default=1
        LIMIT 1
    """, (producto,)).fetchone()
    envase_recalc = None
    if pres and pres[1] and pres[1] > 0:
        unidades = (nueva_kg * 1000 * nuevos_lotes) / pres[1]
        envase_recalc = {
            'envase_codigo': pres[0],
            'etiqueta': pres[2],
            'unidades_requeridas': int(unidades),
        }

    return jsonify({
        'ok': True,
        'produccion_id': prod_id,
        'producto': producto,
        'cantidad_kg_anterior': kg_actuales,
        'cantidad_kg_nueva': nueva_kg,
        'mp_recalculada': mp_recalc,
        'envase_recalculado': envase_recalc,
    })


@bp.route('/api/planta/detectar-cambios-demanda', methods=['GET'])
def detectar_cambios_demanda():
    """Sebastian (30-abr-2026): "si algo debe modificarse que me diga de
    manera inmediata aumento venta aparezca alli recomiendo mover a tal
    día y este a otro deseas aceptar?".

    Compara velocidad actual (últimos 14d) vs base (días 15-44 atrás).
    Detecta SKUs con cambio significativo (>20% arriba o abajo).
    Sugiere ajustes al calendario.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    skus_config = c.execute("""
        SELECT producto_nombre FROM sku_planeacion_config WHERE activo=1
    """).fetchall()

    cambios_detectados = []
    for (producto,) in skus_config:
        # Velocidad reciente (14d) vs base (15-44d atrás)
        sku_rows = c.execute(
            "SELECT sku FROM sku_producto_map WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1",
            (producto,)
        ).fetchall()
        if not sku_rows:
            continue
        v_reciente_total = 0.0
        v_base_total = 0.0
        for (sku,) in sku_rows:
            # Reciente
            r = _ventas_diarias_por_sku(c, sku, dias=14)
            if r:
                v_reciente_total += sum(q for _, q in r) / 14.0
            # Base (días 15-44)
            r2 = c.execute("""
                SELECT date(creado_en), sku_items
                FROM animus_shopify_orders
                WHERE creado_en BETWEEN date('now','-44 days') AND date('now','-15 days')
                  AND sku_items IS NOT NULL
            """).fetchall()
            cant = 0
            for fecha, sku_items_json in r2:
                if not sku_items_json:
                    continue
                try:
                    items = json.loads(sku_items_json) if isinstance(sku_items_json, str) else sku_items_json
                except Exception:
                    continue
                for it in (items or []):
                    if (it.get('sku') or '').strip() == sku:
                        cant += float(it.get('cantidad') or it.get('quantity') or 0)
            if cant > 0:
                v_base_total += cant / 30.0
        if v_base_total < 0.1 or v_reciente_total < 0.1:
            continue
        cambio_pct = ((v_reciente_total - v_base_total) / v_base_total) * 100
        if abs(cambio_pct) < 20:
            continue
        # Cambio significativo
        # Buscar próxima producción programada
        prox = c.execute("""
            SELECT id, fecha_programada FROM produccion_programada
            WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))
              AND fecha_programada >= date('now')
              AND estado IN ('pendiente','en_proceso')
            ORDER BY fecha_programada ASC LIMIT 1
        """, (producto,)).fetchone()
        recomendacion = ''
        nueva_fecha = None
        if cambio_pct > 0 and prox:
            # Aumento: adelantar
            try:
                fp = datetime.strptime(prox[1][:10], '%Y-%m-%d').date()
                # Adelantar tantos días como porcentaje × 0.3 (heurística)
                dias_adelanto = min(14, int(cambio_pct * 0.2))
                nueva_fecha = fp - timedelta(days=dias_adelanto)
                while nueva_fecha.weekday() not in (0, 2, 4):
                    nueva_fecha -= timedelta(days=1)
                if nueva_fecha < datetime.now().date():
                    nueva_fecha = datetime.now().date()
                    while nueva_fecha.weekday() not in (0, 2, 4):
                        nueva_fecha += timedelta(days=1)
                recomendacion = f'Adelantar de {prox[1]} a {nueva_fecha.isoformat()}'
            except Exception:
                pass
        cambios_detectados.append({
            'producto': producto,
            'velocidad_base': round(v_base_total, 2),
            'velocidad_reciente': round(v_reciente_total, 2),
            'cambio_pct': round(cambio_pct, 1),
            'tipo': 'aumento' if cambio_pct > 0 else 'caida',
            'severidad': 'alta' if abs(cambio_pct) > 50 else 'media',
            'proxima_produccion_id': prox[0] if prox else None,
            'proxima_fecha_actual': prox[1] if prox else None,
            'fecha_sugerida': nueva_fecha.isoformat() if nueva_fecha else None,
            'recomendacion': recomendacion,
        })

    return jsonify({
        'cambios': cambios_detectados,
        'total': len(cambios_detectados),
    })


# ════════════════════════════════════════════════════════════════════════
# DEBUG CALENDAR — visibilidad total de qué se lee y cómo se matchea
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/planta/calendar-eventos-plan', methods=['GET'])
def calendar_eventos_plan():
    """Devuelve eventos del Google Calendar que el motor MRP matchea con
    productos configurados, para mostrarlos EN el calendario del Plan v2.

    Sebastian (30-abr-2026): "tal cual como es" — el calendario real debe
    aparecer en el Plan, no solo las proyecciones del motor.

    Querystring: ?dias=30|60|90|180|365 (default 30)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 30))
    except Exception:
        dias = 30
    conn = get_db(); c = conn.cursor()
    eventos = _calendar_events_cached()
    fecha_hoy = datetime.now().date()
    fecha_top = fecha_hoy + timedelta(days=dias)

    productos = c.execute("""
        SELECT producto_nombre, alias_calendar FROM sku_planeacion_config WHERE activo=1
    """).fetchall()
    productos_list = [{'nombre': p[0], 'alias': p[1]} for p in productos]

    items = []
    for ev in eventos:
        try:
            f = datetime.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
        except Exception:
            continue
        if f < fecha_hoy or f > fecha_top:
            continue
        # Match
        mejor_score = 0
        mejor_producto = None
        for p in productos_list:
            score = _match_producto_evento(p['nombre'], p['alias'], ev.get('titulo'), ev.get('descripcion', ''))
            if score > mejor_score:
                mejor_score = score
                mejor_producto = p['nombre']
        kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion', ''))
        items.append({
            'fecha': f.isoformat(),
            'titulo': ev.get('titulo', ''),
            'producto_match': mejor_producto if mejor_score >= 60 else None,
            'score': mejor_score,
            'kg': kg,
            'origen': 'google_calendar',
        })
    items.sort(key=lambda x: x['fecha'])
    return jsonify({'eventos': items, 'total': len(items)})


@bp.route('/api/planta/calendar-debug', methods=['GET'])
def calendar_debug():
    """Devuelve TODOS los eventos del calendar, su match con productos
    configurados, y kg detectados. Sebastian: "que sea perfecto"."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    eventos = _calendar_events_cached(force_refresh=True)
    productos = c.execute("""
        SELECT spc.producto_nombre, spc.alias_calendar, fh.lote_size_kg
        FROM sku_planeacion_config spc
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre))=UPPER(TRIM(spc.producto_nombre))
        WHERE spc.activo=1
    """).fetchall()
    productos_list = [{'nombre': p[0], 'alias': p[1], 'lote_kg': p[2]} for p in productos]
    eventos_analizados = []
    for ev in eventos:
        # Buscar mejor match
        mejor_score = 0
        mejor_producto = None
        candidatos = []
        for p in productos_list:
            score = _match_producto_evento(p['nombre'], p['alias'], ev.get('titulo'), ev.get('descripcion', ''))
            if score > 0:
                candidatos.append({'producto': p['nombre'], 'score': score})
                if score > mejor_score:
                    mejor_score = score
                    mejor_producto = p['nombre']
        kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion', ''))
        candidatos.sort(key=lambda x: -x['score'])
        # Estado
        if mejor_score >= 60:
            if len([cc for cc in candidatos if cc['score'] >= 60]) > 1:
                estado = 'conflicto'
            else:
                estado = 'matcheado'
        elif mejor_score > 0:
            estado = 'sin_match'
        else:
            estado = 'no_relacionado'
        eventos_analizados.append({
            'titulo': ev.get('titulo', ''),
            'fecha': ev.get('fecha', ''),
            'descripcion': (ev.get('descripcion') or '')[:200],
            'kg_detectados': kg,
            'producto_match': mejor_producto if mejor_score >= 60 else None,
            'score_match': mejor_score,
            'candidatos_top3': candidatos[:3],
            'estado': estado,
        })
    # KPIs
    total = len(eventos_analizados)
    matcheados = sum(1 for e in eventos_analizados if e['estado'] == 'matcheado')
    conflicto = sum(1 for e in eventos_analizados if e['estado'] == 'conflicto')
    sin_match = sum(1 for e in eventos_analizados if e['estado'] == 'sin_match')
    no_rel = sum(1 for e in eventos_analizados if e['estado'] == 'no_relacionado')
    con_kg = sum(1 for e in eventos_analizados if e['kg_detectados'])
    return jsonify({
        'total_eventos': total,
        'matcheados': matcheados,
        'en_conflicto': conflicto,
        'sin_match_aceptable': sin_match,
        'no_relacionados': no_rel,
        'con_kg_detectados': con_kg,
        'eventos': eventos_analizados,
        'productos_configurados': len(productos_list),
    })


# ════════════════════════════════════════════════════════════════════════
# APRENDIZAJE DEL HISTÓRICO — el sistema infiere cadencias reales
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "en el calendario aparece lo que ya fabricamos
# es decir esos podrías usarlo como universo para el futuro y arrancar
# colocando lo que no hemos producido".
#
# Lee TODAS las producciones histórias (produccion_programada estado
# completado/en_proceso + Google Calendar) y deriva:
#   - Cadencia real (mediana de intervalos entre lotes)
#   - Última fecha de producción
#   - Productos NUEVOS sin histórico → arrancan como "primer lote"

def _calcular_cadencia_real(fechas):
    """Dada una lista de fechas (date objects), calcula intervalos en días
    y devuelve la mediana."""
    if len(fechas) < 2:
        return None
    fechas_ordenadas = sorted(fechas)
    intervalos = []
    for i in range(1, len(fechas_ordenadas)):
        delta = (fechas_ordenadas[i] - fechas_ordenadas[i-1]).days
        if delta > 0:
            intervalos.append(delta)
    if not intervalos:
        return None
    intervalos.sort()
    n = len(intervalos)
    if n % 2 == 0:
        return (intervalos[n//2 - 1] + intervalos[n//2]) // 2
    return intervalos[n // 2]


@bp.route('/api/planta/kpi-cobertura', methods=['GET'])
def kpi_cobertura_skus():
    """Sebastian (30-abr-2026): "dime cuántos productos están en el plan
    para saber que sí están todos los SKU".

    Querystring: ?dias=14|30|60|90|180|365 — calcula cobertura sobre el
    horizonte solicitado. La cobertura considera producción en BD +
    Google Calendar.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 60))
    except Exception:
        dias = 60
    conn = get_db(); c = conn.cursor()
    productos_total = c.execute(
        "SELECT producto_nombre FROM formula_headers WHERE producto_nombre IS NOT NULL"
    ).fetchall()
    productos_total_set = {(p[0] or '').strip().upper() for p in productos_total if p[0]}

    fecha_limite = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')

    # Producciones en BD dentro del horizonte
    productos_en_plan_bd = c.execute("""
        SELECT DISTINCT UPPER(TRIM(producto)) FROM produccion_programada
        WHERE estado IN ('pendiente','en_proceso')
          AND fecha_programada >= date('now')
          AND fecha_programada <= date(?)
    """, (fecha_limite,)).fetchall()
    productos_en_plan_set = {p[0] for p in productos_en_plan_bd if p[0]}

    # Sumar Google Calendar
    eventos_cal = _calendar_events_cached()
    fecha_hoy = datetime.now().date()
    fecha_top = fecha_hoy + timedelta(days=dias)
    for ev in eventos_cal:
        try:
            f = datetime.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
            if f < fecha_hoy or f > fecha_top:
                continue
        except Exception:
            continue
        titulo = (ev.get('titulo') or '').upper()
        # Match contra productos
        for prod_upper in productos_total_set:
            palabras = [w for w in prod_upper.split() if len(w) > 4]
            if prod_upper in titulo or any(w in titulo for w in palabras):
                productos_en_plan_set.add(prod_upper)

    productos_con_config = c.execute("""
        SELECT UPPER(TRIM(producto_nombre)) FROM sku_planeacion_config WHERE activo=1
    """).fetchall()
    productos_config_set = {p[0] for p in productos_con_config if p[0]}

    # Productos que están en formula pero NO en plan
    sin_plan = []
    for p in productos_total:
        if p[0] and (p[0].strip().upper() not in productos_en_plan_set):
            sin_plan.append(p[0])

    return jsonify({
        'horizonte_dias': dias,
        'total_skus': len(productos_total_set),
        'en_plan': len(productos_en_plan_set),
        'en_plan_futuro': len(productos_en_plan_set),  # back-compat
        'con_config': len(productos_config_set),
        'sin_plan': sorted(sin_plan),
        'cobertura_pct': round(len(productos_en_plan_set) / max(1, len(productos_total_set)) * 100, 1),
    })


@bp.route('/api/planta/producto-nuevo', methods=['POST'])
def producto_nuevo_rapido():
    """Sebastian (30-abr-2026): "debe permitir adicionar nuevos productos
    porque se vienen lanzamientos... lo palancamos desde área científica
    pero debe existir en producción también por si se necesita programar
    algo de manera prioritaria".

    Crea de un solo click:
      1. Entrada en formula_headers (sin items)
      2. sku_planeacion_config con cadencia=null (auto por umbral)
      3. Opcionalmente programa una producción inicial prioritaria

    Body: {producto_nombre*, lote_size_kg*, categoria?, cadencia_dias?,
           merma_pct?, fecha_primera_prod?, lotes_inicial?,
           prioritario? (boolean)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    producto = (d.get('producto_nombre') or '').strip()
    lote_kg = d.get('lote_size_kg')
    if not producto or not lote_kg:
        return jsonify({'error': 'producto_nombre y lote_size_kg requeridos'}), 400
    lote_kg = float(lote_kg)
    conn = get_db(); c = conn.cursor()

    # 1. formula_headers
    existing_fh = c.execute(
        "SELECT producto_nombre FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    if not existing_fh:
        c.execute("""
            INSERT INTO formula_headers (producto_nombre, lote_size_kg, unidad_base_g)
            VALUES (?, ?, 1.0)
        """, (producto, lote_kg))
        log_msg_fh = 'fórmula creada'
    else:
        log_msg_fh = 'fórmula ya existía'

    # 2. sku_planeacion_config
    existing_cfg = c.execute(
        "SELECT id FROM sku_planeacion_config WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    if not existing_cfg:
        c.execute("""
            INSERT INTO sku_planeacion_config
              (producto_nombre, categoria, cadencia_dias, cobertura_target_dias,
               cobertura_min_dias, cobertura_max_dias, merma_pct, prioridad,
               activo, notas)
            VALUES (?, ?, ?, 60, 20, 90, ?, 2, 1, ?)
        """, (
            producto, d.get('categoria'), d.get('cadencia_dias'),
            float(d.get('merma_pct') or 5.0),
            f'Creado por {user} el {datetime.now().date()} (lanzamiento)',
        ))
        log_msg_cfg = 'config creada'
    else:
        log_msg_cfg = 'config ya existía'

    # 3. Producción inicial prioritaria (opcional)
    produccion_id = None
    if d.get('prioritario') or d.get('fecha_primera_prod'):
        from datetime import datetime as _dt2
        fecha_obj = (d.get('fecha_primera_prod') or '').strip()
        if not fecha_obj:
            # Próximo L/M/V
            fobj = _dt2.now().date() + timedelta(days=2)
            while fobj.weekday() not in (0, 2, 4):
                fobj += timedelta(days=1)
            fecha_obj = fobj.isoformat()
        merma = float(d.get('merma_pct') or 5.0)
        kg_con_merma = lote_kg * (1 + merma / 100.0)
        cur = c.execute("""
            INSERT INTO produccion_programada
              (producto, fecha_programada, lotes, estado, observaciones, origen, cantidad_kg)
            VALUES (?, ?, ?, 'pendiente', ?, 'producto_nuevo_lanzamiento', ?)
        """, (
            producto, fecha_obj, int(d.get('lotes_inicial') or 1),
            f'PRODUCTO NUEVO · creado por {user} · {("prioritario" if d.get("prioritario") else "primera producción")}',
            kg_con_merma,
        ))
        produccion_id = cur.lastrowid
        # Auto-asignar área + operarios al producto nuevo
        try:
            cap_min = kg_con_merma * 1.2
            tanques = c.execute("""
                SELECT area_codigo FROM equipos_planta
                WHERE activo=1 AND tipo IN ('tanque','marmita','olla')
                  AND capacidad_litros >= ?
                ORDER BY capacidad_litros ASC LIMIT 1
            """, (cap_min,)).fetchone()
            if tanques:
                area_chk = c.execute(
                    "SELECT id FROM areas_planta WHERE codigo=? AND puede_producir=1 AND activo=1",
                    (tanques[0],)
                ).fetchone()
                if area_chk:
                    c.execute("UPDATE produccion_programada SET area_id=? WHERE id=?",
                              (area_chk[0], produccion_id))
            _asignar_operarios_a_produccion(conn, produccion_id)
        except Exception:
            pass

    # Notificar a admins
    try:
        from blueprints.notif import push_notif_multi
        push_notif_multi(
            ['sebastian', 'alejandro'], 'planta',
            f'🆕 Producto nuevo: {producto}',
            body=f'Lote {lote_kg}kg · creado por {user}' + (f' · 1ra producción {fecha_obj}' if produccion_id else ''),
            link='/inventarios#programacion',
            remitente=user,
        )
    except Exception:
        pass

    conn.commit()
    return jsonify({
        'ok': True,
        'producto': producto,
        'formula': log_msg_fh,
        'config': log_msg_cfg,
        'produccion_creada_id': produccion_id,
        'mensaje': f'✓ {producto} agregado al sistema',
    })


@bp.route('/api/auto-plan/aprender-historico', methods=['GET'])
def aprender_historico():
    """Analiza producciones histórias (BD + Google Calendar) y deriva
    cadencias reales. Devuelve comparación con la config actual.

    Querystring: ?meses_atras=12 (default — cuánto histórico considerar)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        meses_atras = int(request.args.get('meses_atras', 12))
    except Exception:
        meses_atras = 12

    conn = get_db(); c = conn.cursor()
    fecha_desde = (datetime.now() - timedelta(days=meses_atras * 30)).date()

    # 1. Producciones desde produccion_programada (BD interna)
    rows_bd = c.execute("""
        SELECT producto, fecha_programada, lotes, estado, cantidad_kg
        FROM produccion_programada
        WHERE date(fecha_programada) >= ?
          AND estado IN ('completado','en_proceso','pendiente')
          AND producto IS NOT NULL
        ORDER BY producto, fecha_programada
    """, (fecha_desde.isoformat(),)).fetchall()

    # Acumular fechas por producto
    fechas_por_producto = {}
    for prod, fecha, lotes, estado, kg in rows_bd:
        try:
            f = datetime.strptime(fecha[:10], '%Y-%m-%d').date()
        except Exception:
            continue
        key = (prod or '').strip().upper()
        if not key:
            continue
        fechas_por_producto.setdefault(key, {'nombre_real': prod, 'fechas': [],
                                              'lotes_total': 0, 'kg_total': 0})
        fechas_por_producto[key]['fechas'].append(f)
        fechas_por_producto[key]['lotes_total'] += (lotes or 1)
        fechas_por_producto[key]['kg_total'] += (kg or 0)

    # 2. Producciones desde Google Calendar (eventos con producto en el título)
    try:
        from blueprints.programacion import _fetch_calendar_events
        cal_events = _fetch_calendar_events(days_ahead=0) or []
        # _fetch_calendar_events devuelve eventos futuros, pero podemos
        # ampliar para incluir el pasado. Si no, usamos solo BD.
    except Exception:
        cal_events = []

    # Cargar productos en formula_headers para detectar nuevos
    productos_formula = c.execute("""
        SELECT producto_nombre, lote_size_kg FROM formula_headers
    """).fetchall()
    productos_formula_set = {(p[0] or '').strip().upper(): {'nombre': p[0], 'lote_kg': p[1]}
                             for p in productos_formula if p[0]}

    # 3. Cargar config actual
    configs = c.execute("""
        SELECT producto_nombre, cadencia_dias, cobertura_target_dias, merma_pct
        FROM sku_planeacion_config WHERE activo=1
    """).fetchall()
    config_por_producto = {(c[0] or '').strip().upper(): {
        'cadencia': c[1], 'target': c[2], 'merma': c[3]
    } for c in configs}

    # 4. Análisis por producto
    aprendizaje = []
    productos_con_historico = set()
    for key, info in fechas_por_producto.items():
        productos_con_historico.add(key)
        cadencia_real = _calcular_cadencia_real(info['fechas'])
        cfg = config_por_producto.get(key, {})
        cadencia_config = cfg.get('cadencia')
        ultima = max(info['fechas']) if info['fechas'] else None
        primera = min(info['fechas']) if info['fechas'] else None
        # Diferencia entre real vs config
        diferencia = None
        if cadencia_real and cadencia_config:
            diferencia = cadencia_real - cadencia_config
        # Recomendación
        recomendar_cambiar = False
        if cadencia_real and (not cadencia_config or abs((cadencia_real or 0) - (cadencia_config or 0)) > 7):
            recomendar_cambiar = True
        aprendizaje.append({
            'producto': info['nombre_real'],
            'lotes_historicos': len(info['fechas']),
            'lotes_total_unidades': info['lotes_total'],
            'kg_total': round(info['kg_total'], 1),
            'primera_produccion': primera.isoformat() if primera else None,
            'ultima_produccion': ultima.isoformat() if ultima else None,
            'dias_desde_ultima': (datetime.now().date() - ultima).days if ultima else None,
            'cadencia_real_dias': cadencia_real,
            'cadencia_configurada': cadencia_config,
            'diferencia_dias': diferencia,
            'recomendar_actualizar': recomendar_cambiar,
            'tiene_config': key in config_por_producto,
            'tiene_formula': key in productos_formula_set,
        })

    # 5. Productos NUEVOS (en formula_headers pero sin histórico)
    productos_nuevos = []
    for key, info in productos_formula_set.items():
        if key not in productos_con_historico:
            cfg = config_por_producto.get(key, {})
            productos_nuevos.append({
                'producto': info['nombre'],
                'lote_kg': info['lote_kg'],
                'tiene_config': key in config_por_producto,
                'cadencia_configurada': cfg.get('cadencia'),
                'sugerencia': 'Producir primer lote pronto — sin histórico',
            })

    return jsonify({
        'fecha_analisis': datetime.now().isoformat(),
        'meses_atras': meses_atras,
        'aprendizaje': sorted(aprendizaje, key=lambda x: -(x.get('lotes_historicos') or 0)),
        'productos_nuevos': productos_nuevos,
        'kpis': {
            'productos_con_historico': len(aprendizaje),
            'productos_nuevos_sin_historico': len(productos_nuevos),
            'recomendaciones_actualizar': sum(1 for a in aprendizaje if a['recomendar_actualizar']),
            'total_lotes_analizados': sum(a['lotes_historicos'] for a in aprendizaje),
        },
    })


@bp.route('/api/auto-plan/aplicar-aprendizaje', methods=['POST'])
def aplicar_aprendizaje():
    """Toma las cadencias detectadas del histórico y actualiza la config.
    Body: {productos: [{producto, cadencia_real_dias}, ...]}
    O sin body para aplicar TODAS las recomendaciones.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    productos_a_aplicar = d.get('productos')

    conn = get_db(); c = conn.cursor()

    if not productos_a_aplicar:
        # Modo sin lista: tomar todas las recomendaciones del análisis
        from flask import url_for
        analisis = aprender_historico()
        if hasattr(analisis, 'get_json'):
            data = analisis.get_json()
        else:
            data = analisis[0].get_json() if isinstance(analisis, tuple) else {}
        productos_a_aplicar = []
        for a in (data.get('aprendizaje') or []):
            if a.get('recomendar_actualizar') and a.get('cadencia_real_dias'):
                productos_a_aplicar.append({
                    'producto': a['producto'],
                    'cadencia_real_dias': a['cadencia_real_dias'],
                })

    actualizados = []
    for it in productos_a_aplicar:
        producto = (it.get('producto') or '').strip()
        cadencia = it.get('cadencia_real_dias')
        if not producto or not cadencia:
            continue
        # Verificar si tiene config
        existing = c.execute(
            "SELECT id, cadencia_dias FROM sku_planeacion_config WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND activo=1",
            (producto,)
        ).fetchone()
        if existing:
            c.execute("""
                UPDATE sku_planeacion_config SET
                  cadencia_dias=?, actualizado_en=datetime('now'),
                  notas=COALESCE(notas,'')||' · Aprendido del histórico '||date('now')
                WHERE id=?
            """, (int(cadencia), existing[0]))
            actualizados.append({'producto': producto, 'cadencia_anterior': existing[1],
                                  'cadencia_nueva': cadencia, 'accion': 'actualizado'})
        else:
            # Crear config nueva con cadencia detectada
            c.execute("""
                INSERT INTO sku_planeacion_config
                  (producto_nombre, cadencia_dias, cobertura_target_dias,
                   cobertura_min_dias, merma_pct, prioridad, activo, notas)
                VALUES (?, ?, 60, 20, 5.0, 3, 1, ?)
            """, (producto, int(cadencia),
                  f'Auto-creado desde histórico {datetime.now().date()}'))
            actualizados.append({'producto': producto, 'cadencia_anterior': None,
                                  'cadencia_nueva': cadencia, 'accion': 'creado'})

    conn.commit()
    return jsonify({
        'ok': True, 'actualizados': actualizados, 'total': len(actualizados),
    })


# ════════════════════════════════════════════════════════════════════════
# MAQUILA INTELIGENTE — clientes + pedidos integrados al motor del Plan
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "Kelly Guerra compra productos para marca de ella
# pero misma fórmula Animus... espacio de maquila inteligente, si Fernando
# lleva 500 le adiciona a la producción esas 500 unidades".

@bp.route('/api/maquila/clientes', methods=['GET', 'POST'])
def maquila_clientes():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        nombre = (d.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'nombre requerido'}), 400
        try:
            c.execute("""
                INSERT INTO clientes_maquila
                  (nombre, nit_cedula, email, telefono, es_marca_propia,
                   empresa_grupo, comparte_formula_con, margen_seguridad_pct, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nombre, d.get('nit_cedula'), d.get('email'), d.get('telefono'),
                1 if d.get('es_marca_propia') else 0,
                d.get('empresa_grupo'), d.get('comparte_formula_con'),
                int(d.get('margen_seguridad_pct') or 5),
                d.get('notas'),
            ))
            conn.commit()
            return jsonify({'ok': True, 'id': c.lastrowid})
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Cliente ya existe con ese nombre'}), 409
    rows = c.execute(
        "SELECT * FROM clientes_maquila WHERE activo=1 ORDER BY nombre"
    ).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'clientes': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/maquila/pedidos', methods=['GET', 'POST'])
def maquila_pedidos():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        cliente_id = d.get('cliente_id')
        producto = (d.get('producto_nombre') or '').strip()
        unidades = int(d.get('unidades') or 0)
        if not cliente_id or not producto or unidades <= 0:
            return jsonify({'error': 'cliente_id, producto_nombre, unidades requeridos'}), 400
        # Buscar cliente
        cli = c.execute(
            "SELECT nombre FROM clientes_maquila WHERE id=?", (cliente_id,)
        ).fetchone()
        if not cli:
            return jsonify({'error': 'Cliente no existe'}), 400
        # Generar número
        n = c.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(numero,4) AS INTEGER)),0)+1 FROM maquila_pedidos WHERE numero LIKE 'MQ-%'"
        ).fetchone()[0] or 1
        numero = f'MQ-{n:04d}'
        # Calcular kg estimados desde presentación
        kg_est = d.get('kg_estimados')
        if not kg_est and d.get('presentacion_id'):
            pr = c.execute(
                "SELECT factor_g_por_unidad FROM producto_presentaciones WHERE id=?",
                (d.get('presentacion_id'),)
            ).fetchone()
            if pr and pr[0]:
                kg_est = (unidades * pr[0]) / 1000.0
        try:
            c.execute("""
                INSERT INTO maquila_pedidos
                  (numero, cliente_id, cliente_nombre, producto_nombre, presentacion_id,
                   unidades, kg_estimados, fecha_entrega_objetivo, precio_unidad,
                   observaciones, creado_por)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                numero, cliente_id, cli[0], producto,
                d.get('presentacion_id'),
                unidades, kg_est,
                (d.get('fecha_entrega_objetivo') or '').strip() or None,
                d.get('precio_unidad'),
                d.get('observaciones'),
                user,
            ))
            conn.commit()
            return jsonify({'ok': True, 'numero': numero, 'id': c.lastrowid,
                            'kg_estimados': kg_est})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    # GET — filtros opcionales
    estado = (request.args.get('estado') or '').strip()
    cliente = request.args.get('cliente_id')
    where = []
    params = []
    if estado and estado != 'todos':
        where.append('mp.estado=?'); params.append(estado)
    if cliente:
        where.append('mp.cliente_id=?'); params.append(int(cliente))
    sql = """
        SELECT mp.*, cm.nombre as cliente_nombre_full,
               pp.fecha_programada as produccion_fecha,
               pp.estado as produccion_estado
        FROM maquila_pedidos mp
        LEFT JOIN clientes_maquila cm ON cm.id = mp.cliente_id
        LEFT JOIN produccion_programada pp ON pp.id = mp.produccion_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY mp.fecha_entrega_objetivo ASC NULLS LAST, mp.id DESC"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    # KPIs
    pendientes = sum(1 for it in items if it['estado'] in ('recibido', 'planificado'))
    en_prod = sum(1 for it in items if it['estado'] == 'en_produccion')
    return jsonify({
        'pedidos': items, 'total': len(items),
        'pendientes': pendientes, 'en_produccion': en_prod,
    })


@bp.route('/api/maquila/pedidos/<int:pedido_id>/asignar-produccion', methods=['POST'])
def maquila_asignar_produccion(pedido_id):
    """Asocia un pedido de maquila a una producción específica."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    prod_id = d.get('produccion_id')
    if not prod_id:
        return jsonify({'error': 'produccion_id requerido'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("""
        UPDATE maquila_pedidos SET produccion_id=?, estado='planificado', actualizado_en=datetime('now')
        WHERE id=?
    """, (prod_id, pedido_id))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/maquila/pedidos/<int:pedido_id>', methods=['DELETE'])
def maquila_pedido_cancelar(pedido_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    c.execute(
        "UPDATE maquila_pedidos SET estado='cancelado' WHERE id=?", (pedido_id,)
    )
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════
# Asignación automática de operarios (Mayerlin fija + rotación inteligente)
# ════════════════════════════════════════════════════════════════════════
def _asignar_operarios_a_produccion(conn, produccion_id):
    """Asigna automáticamente operarios a una producción según reglas:
       - Dispensación: SIEMPRE Mayerlin (regla dura)
       - Elaboración/Envasado/Acondicionamiento: rotan según historial reciente
    """
    c = conn.cursor()
    # Buscar Mayerlin
    mayerlin = c.execute(
        "SELECT id FROM operarios_planta WHERE LOWER(nombre)='mayerlin' AND activo=1 LIMIT 1"
    ).fetchone()
    op_disp_id = mayerlin[0] if mayerlin else None

    # Para las otras fases: encontrar operario con MENOS asignaciones en últimos 7 días
    def operario_menos_asignado(rol_excluir=None):
        rows = c.execute(f"""
            SELECT op.id, op.nombre,
                   (SELECT COUNT(*) FROM produccion_programada pp
                    WHERE pp.fecha_programada >= date('now','-7 days')
                      AND (pp.operario_elaboracion_id=op.id
                        OR pp.operario_envasado_id=op.id
                        OR pp.operario_acondicionamiento_id=op.id)) AS carga
            FROM operarios_planta op
            WHERE op.activo=1
              AND op.fija_en_dispensacion=0
              AND op.es_jefe_produccion=0
              AND LOWER(op.nombre) != 'mayerlin'
            ORDER BY carga ASC, op.nombre LIMIT 1
        """).fetchone()
        return rows[0] if rows else None

    op_elab_id = operario_menos_asignado()
    op_env_id = operario_menos_asignado()
    op_acond_id = operario_menos_asignado()

    c.execute("""
        UPDATE produccion_programada SET
          operario_dispensacion_id = COALESCE(operario_dispensacion_id, ?),
          operario_elaboracion_id = COALESCE(operario_elaboracion_id, ?),
          operario_envasado_id = COALESCE(operario_envasado_id, ?),
          operario_acondicionamiento_id = COALESCE(operario_acondicionamiento_id, ?)
        WHERE id=?
    """, (op_disp_id, op_elab_id, op_env_id, op_acond_id, produccion_id))


@bp.route('/api/planta/produccion/<int:prod_id>/asignar-operarios-auto', methods=['POST'])
def asignar_operarios_auto(prod_id):
    """Asigna operarios automáticamente (Mayerlin fija + rotación)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    _asignar_operarios_a_produccion(conn, prod_id)
    conn.commit()
    return jsonify({'ok': True, 'mensaje': 'Operarios asignados'})


@bp.route('/api/planta/asignar-operarios-bulk', methods=['POST'])
def asignar_operarios_bulk():
    """Asigna operarios automáticamente a TODAS las producciones pendientes
    sin operarios. Útil después de Auto-Plan."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id FROM produccion_programada
        WHERE estado IN ('pendiente','en_proceso')
          AND fecha_programada >= date('now')
          AND (operario_dispensacion_id IS NULL
            OR operario_elaboracion_id IS NULL
            OR operario_envasado_id IS NULL)
    """).fetchall()
    asignadas = 0
    for (pid,) in rows:
        _asignar_operarios_a_produccion(conn, pid)
        asignadas += 1
    conn.commit()
    return jsonify({'ok': True, 'asignadas': asignadas})


# ════════════════════════════════════════════════════════════════════════
# Descarga Plan PDF/Excel (para Alejandro)
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/planta/plan/exportar', methods=['GET'])
def plan_exportar():
    """Exporta el plan a Excel para revisión.
    Querystring: ?meses=1|2|3|6|12 ?formato=xlsx|csv (default xlsx)
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from flask import Response
    try:
        meses = int(request.args.get('meses', 3))
    except Exception:
        meses = 3
    formato = (request.args.get('formato') or 'xlsx').lower()

    conn = get_db(); c = conn.cursor()
    proyeccion = _generar_proyeccion_lotes(c, meses)

    if formato == 'csv':
        import io
        buffer = io.StringIO()
        buffer.write('Producto,Fecha,Mes,Lote_kg,Kg_con_merma,Velocidad_dia,Tipo,Cadencia_dias\n')
        for p in proyeccion:
            buffer.write(f"{p['producto']},{p['fecha']},{p['mes']},{p['lote_kg']},{p['kg_con_merma']:.1f},{p['velocidad_dia']:.2f},{p['tipo']},{p.get('cadencia_dias') or ''}\n")
        return Response(
            buffer.getvalue(), mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=plan_{meses}m.csv'}
        )

    # Excel
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return jsonify({'error': 'openpyxl no disponible'}), 500

    wb = Workbook()
    ws = wb.active
    ws.title = f'Plan {meses}m'

    # Header
    headers = ['Producto', 'Fecha', 'Mes', 'Lote kg', 'Kg con merma',
               'Velocidad/día', 'Tipo', 'Cadencia']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='7C3AED', end_color='7C3AED', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')

    # Datos
    for r, p in enumerate(proyeccion, 2):
        ws.cell(row=r, column=1, value=p['producto'])
        ws.cell(row=r, column=2, value=p['fecha'])
        ws.cell(row=r, column=3, value=p['mes'])
        ws.cell(row=r, column=4, value=p['lote_kg'])
        ws.cell(row=r, column=5, value=round(p['kg_con_merma'], 1))
        ws.cell(row=r, column=6, value=round(p['velocidad_dia'], 2))
        ws.cell(row=r, column=7, value=p['tipo'])
        ws.cell(row=r, column=8, value=p.get('cadencia_dias') or '')

    # Anchos
    for col, w in zip('ABCDEFGH', [42, 12, 10, 10, 14, 14, 14, 12]):
        ws.column_dimensions[col].width = w

    # Hoja resumen mensual
    ws2 = wb.create_sheet('Resumen mensual')
    ws2.cell(row=1, column=1, value='Mes').font = Font(bold=True)
    ws2.cell(row=1, column=2, value='Lotes').font = Font(bold=True)
    ws2.cell(row=1, column=3, value='Kg total').font = Font(bold=True)
    ws2.cell(row=1, column=4, value='SKUs distintos').font = Font(bold=True)
    resumen = {}
    for p in proyeccion:
        m = p['mes']
        if m not in resumen:
            resumen[m] = {'lotes': 0, 'kg': 0, 'skus': set()}
        resumen[m]['lotes'] += 1
        resumen[m]['kg'] += p['kg_con_merma']
        resumen[m]['skus'].add(p['producto'])
    for r, m in enumerate(sorted(resumen), 2):
        ws2.cell(row=r, column=1, value=m)
        ws2.cell(row=r, column=2, value=resumen[m]['lotes'])
        ws2.cell(row=r, column=3, value=round(resumen[m]['kg'], 1))
        ws2.cell(row=r, column=4, value=len(resumen[m]['skus']))

    import io
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        buf.read(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename=plan_{meses}m_alejandro.xlsx'}
    )


@bp.route('/api/planta/produccion/<int:prod_id>/aceptar-recomendacion', methods=['POST'])
def aceptar_recomendacion(prod_id):
    """Acepta una recomendación de mover producción a otra fecha."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    nueva_fecha = (d.get('nueva_fecha') or '').strip()
    if not nueva_fecha:
        return jsonify({'error': 'nueva_fecha requerida'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("""
        UPDATE produccion_programada SET
          fecha_programada=?,
          observaciones=COALESCE(observaciones,'')||' | Movida por '||?||' a '||?||' (recomendación demanda)'
        WHERE id=?
    """, (nueva_fecha, user, nueva_fecha, prod_id))
    conn.commit()
    return jsonify({'ok': True, 'produccion_id': prod_id, 'nueva_fecha': nueva_fecha})


@bp.route('/api/auto-plan/runs', methods=['GET'])
def auto_plan_runs():
    """Histórico de ejecuciones del auto-plan."""
    u, err, code = _auth()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, ejecutado_at, ejecutado_por, tipo, horizonte_dias,
               producciones_creadas, compras_creadas, alertas_criticas,
               emails_enviados, error, duracion_ms
        FROM auto_plan_runs
        ORDER BY ejecutado_at DESC
        LIMIT 30
    """).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'runs': [dict(zip(cols, r)) for r in rows]})


# ── Configs CRUD ──────────────────────────────────────────────────────

@bp.route('/api/auto-plan/configs/sku', methods=['GET'])
def configs_sku():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT spc.*, fh.lote_size_kg
        FROM sku_planeacion_config spc
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(spc.producto_nombre))
        WHERE spc.activo = 1
        ORDER BY spc.prioridad, spc.producto_nombre
    """).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'configs': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/auto-plan/configs/sku/<int:config_id>', methods=['PUT'])
def configs_sku_update(config_id):
    u, err, code = _auth()
    if err:
        return err, code
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    campos = []
    params = []
    for col in ('cadencia_dias', 'cobertura_target_dias', 'cobertura_min_dias',
                'cobertura_max_dias', 'merma_pct', 'prioridad', 'categoria',
                'presentacion_default_id', 'notas', 'alias_calendar'):
        if col in d:
            campos.append(f'{col}=?')
            params.append(d[col])
    if not campos:
        return jsonify({'error': 'Sin cambios'}), 400
    campos.append("actualizado_en=datetime('now')")
    params.append(config_id)
    c.execute(f"UPDATE sku_planeacion_config SET {', '.join(campos)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/auto-plan/configs/mp', methods=['GET', 'POST'])
def configs_mp():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""
            INSERT OR REPLACE INTO mp_lead_time_config
              (material_id, material_nombre, proveedor_principal, lead_time_dias,
               buffer_dias, cobertura_min_dias, cobertura_ideal_dias, origen,
               es_envase, activo, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """, (
            d.get('material_id'), d.get('material_nombre'),
            d.get('proveedor_principal'), int(d.get('lead_time_dias') or 14),
            int(d.get('buffer_dias') or 30), int(d.get('cobertura_min_dias') or 30),
            int(d.get('cobertura_ideal_dias') or 60),
            d.get('origen') or 'local', 1 if d.get('es_envase') else 0,
        ))
        conn.commit()
        return jsonify({'ok': True})
    rows = c.execute("SELECT * FROM mp_lead_time_config WHERE activo=1 ORDER BY origen, material_nombre").fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'configs': [dict(zip(cols, r)) for r in rows]})


# ════════════════════════════════════════════════════════════════════════
# Asistente conversacional · Claude API con contexto de planta
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "asistente conversacional ya tenemos la cosa
# flotante" — conectar el chat flotante con Claude API + contexto de
# planta para que pueda responder preguntas como:
#   "¿Cuánto Suero AH puedo producir esta semana?"
#   "¿Por qué hay alerta crítica?"
#   "Programa 2 lotes de Vit C para el viernes"

def _build_planta_context(c):
    """Recolecta snapshot del estado de planta para el prompt de Claude."""
    snapshot = {}

    # KPIs
    try:
        snapshot['areas_planta'] = [
            dict(zip(['codigo', 'nombre', 'estado', 'puede_producir', 'puede_envasar'], r))
            for r in c.execute(
                "SELECT codigo, nombre, estado, puede_producir, puede_envasar "
                "FROM areas_planta WHERE activo=1 ORDER BY orden LIMIT 15"
            ).fetchall()
        ]
    except Exception:
        snapshot['areas_planta'] = []

    try:
        snapshot['equipos_resumen'] = [
            {'area_codigo': r[0], 'tipo': r[1], 'count': r[2]}
            for r in c.execute(
                "SELECT area_codigo, tipo, COUNT(*) FROM equipos_planta "
                "WHERE activo=1 AND tipo IN ('tanque','marmita','olla','envasadora') "
                "GROUP BY area_codigo, tipo"
            ).fetchall()
        ]
    except Exception:
        snapshot['equipos_resumen'] = []

    try:
        snapshot['operarios'] = [
            dict(zip(['nombre', 'rol'], r))
            for r in c.execute(
                "SELECT nombre, rol_predeterminado FROM operarios_planta WHERE activo=1"
            ).fetchall()
        ]
    except Exception:
        snapshot['operarios'] = []

    # Producciones próximas 14d
    try:
        snapshot['producciones_proximas'] = [
            {'producto': r[0], 'fecha': r[1], 'lotes': r[2], 'estado': r[3]}
            for r in c.execute(
                "SELECT producto, fecha_programada, lotes, estado FROM produccion_programada "
                "WHERE fecha_programada >= date('now') AND fecha_programada <= date('now','+14 days') "
                "ORDER BY fecha_programada ASC LIMIT 25"
            ).fetchall()
        ]
    except Exception:
        snapshot['producciones_proximas'] = []

    # Cadencias configuradas
    try:
        snapshot['cadencias_skus'] = [
            {'producto': r[0], 'cadencia_d': r[1], 'cobertura_d': r[2], 'merma_pct': r[3]}
            for r in c.execute(
                "SELECT producto_nombre, cadencia_dias, cobertura_target_dias, merma_pct "
                "FROM sku_planeacion_config WHERE activo=1 AND cadencia_dias IS NOT NULL "
                "ORDER BY prioridad LIMIT 10"
            ).fetchall()
        ]
    except Exception:
        snapshot['cadencias_skus'] = []

    # Último auto-plan run
    try:
        last_run = c.execute(
            "SELECT ejecutado_at, producciones_creadas, compras_creadas, alertas_criticas "
            "FROM auto_plan_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last_run:
            snapshot['ultimo_run'] = {
                'fecha': last_run[0], 'prods': last_run[1],
                'compras': last_run[2], 'alertas': last_run[3]
            }
    except Exception:
        pass

    return snapshot


@bp.route('/api/asistente/planta', methods=['POST'])
def asistente_planta():
    """Asistente conversacional con contexto de planta. Usa Claude API.
    Body: {pregunta: str, historial?: [{role, content}, ...]}"""
    import os
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    pregunta = (d.get('pregunta') or '').strip()
    if not pregunta:
        return jsonify({'error': 'pregunta requerida'}), 400
    historial = d.get('historial') or []

    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
    if not api_key:
        return jsonify({
            'respuesta': 'El asistente conversacional necesita ANTHROPIC_API_KEY configurada en Render. Cuando esté lista, podré responder con contexto completo de la planta.',
            'sin_api_key': True,
        })

    conn = get_db(); c = conn.cursor()
    try:
        ctx = _build_planta_context(c)
    except Exception as e:
        ctx = {}
        log.warning(f'asistente: no se pudo armar contexto: {e}')

    es_admin = user in ADMIN_USERS
    system_prompt = f"""Eres EOS Planta, el asistente experto de planta para Espagiria Laboratorios (HHA Group), laboratorio cosmético colombiano certificado INVIMA. Te creó Claude. Eres preciso, breve y útil — operativo, no chatbot genérico.

CONTEXTO ACTUAL (snapshot {datetime.now().isoformat()}):
{json.dumps(ctx, ensure_ascii=False, indent=2)}

REGLAS DE PLANEACIÓN:
- Vit C → cadencia 30d (oxida)
- Suero AH 1.5% → cadencia 90d, lote 90kg
- L/M/V producir · Ma/Ju acondicionar/envasar/conteo cíclico
- MP mínimo 30d, ideal 60d · Envases mínimo 90d (China lead 180d)
- 4 operarios: Mayerlin (dispensación fija), Camilo, Milton, Sebastián M.
- Áreas: FAB1/2/3, ENV1/2, DISP, LAV, ESC1, ACOND, FAB_FLOAT, CC, RECEP

ACCIONES DISPONIBLES (puedes sugerir al usuario que las dispare):
- Ejecutar Auto-Plan ahora → /api/auto-plan/aplicar (solo admin)
- Ver alertas críticas activas → tab "Plan Semanal" o /api/asistente/tool/listar_alertas
- Ver producciones próximas → tab "Plan Semanal" o /api/asistente/tool/listar_producciones_proximas
- Configurar cadencia → tab "🤖 Auto-Plan" → "Cadencias por SKU"
- Activar/desactivar cron → tab "🤖 Auto-Plan" → toggle (solo admin)

Usuario actual: {user} ({'ADMIN' if es_admin else 'usuario'})

INSTRUCCIONES:
- Responde en español, conciso (máximo 200 palabras salvo que pidan detalle).
- Si la pregunta es operativa (cuánto, cuándo, dónde), USA el contexto del snapshot para contestar con datos reales.
- Si te piden hacer algo destructivo (ejecutar, crear), describe los pasos y dile dónde hacer click — NO inventes acciones.
- Si no hay datos suficientes, dilo: "no tengo info sobre X — revisa Y".
- Si detectas riesgo (alertas críticas, MP en déficit, sala sin limpieza), señálalo proactivamente.
"""

    messages = []
    for h in historial[-10:]:
        if h.get('role') in ('user', 'assistant') and h.get('content'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': pregunta})

    try:
        import urllib.request, urllib.error
        body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 800,
            'system': system_prompt,
            'messages': messages,
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=body, method='POST',
            headers={
                'content-type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = (data.get('content') or [{}])[0].get('text', '').strip()
        return jsonify({
            'respuesta': text,
            'usage': data.get('usage', {}),
            'modelo': 'claude-haiku-4-5',
        })
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
        except Exception:
            err_body = str(e)
        log.warning(f'Claude API error: {err_body}')
        return jsonify({'error': f'Claude API: {e.code}', 'detalle': err_body[:200]}), 500
    except Exception as e:
        log.warning(f'Asistente fallo: {e}')
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════════════════
# Cron control desde UI (sin env var)
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/auto-plan/cron/state', methods=['GET'])
def cron_state():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    r = c.execute("SELECT habilitado, activado_por, activado_at, ultima_ejecucion_at, errores_consecutivos, notas FROM auto_plan_cron_state WHERE id=1").fetchone()
    if not r:
        return jsonify({'habilitado': False})
    return jsonify({
        'habilitado': bool(r[0]),
        'activado_por': r[1],
        'activado_at': r[2],
        'ultima_ejecucion_at': r[3],
        'errores_consecutivos': r[4],
        'notas': r[5],
    })


@bp.route('/api/auto-plan/cron/toggle', methods=['POST'])
def cron_toggle():
    u, err, code = _auth()
    if err:
        return err, code
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin'}), 403
    d = request.json or {}
    habilitar = bool(d.get('habilitar'))
    conn = get_db(); c = conn.cursor()
    if habilitar:
        c.execute("""
            UPDATE auto_plan_cron_state SET
              habilitado=1, activado_por=?, activado_at=datetime('now'),
              errores_consecutivos=0, notas=?
            WHERE id=1
        """, (u, 'Activado desde UI'))
    else:
        c.execute("UPDATE auto_plan_cron_state SET habilitado=0, notas=? WHERE id=1",
                  ('Desactivado desde UI',))
    conn.commit()
    return jsonify({'ok': True, 'habilitado': habilitar})


# ════════════════════════════════════════════════════════════════════════
# Email test real (envía email de prueba al rol/email)
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/auto-plan/configs/emails/test', methods=['POST'])
def email_test():
    u, err, code = _auth()
    if err:
        return err, code
    d = request.json or {}
    email_dest = (d.get('email') or '').strip()
    if not email_dest:
        return jsonify({'error': 'email requerido'}), 400
    asunto = '🤖 Test EOS Auto-Plan'
    html = f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,sans-serif;background:#f3f4f6;padding:20px">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.08)">
    <div style="background:linear-gradient(135deg,#7c3aed,#dc2626);color:#fff;padding:20px">
      <h2 style="margin:0">✅ Email funcionando</h2>
      <p style="margin:6px 0 0;opacity:.9;font-size:13px">EOS · Auto-Plan Maestro</p>
    </div>
    <div style="padding:20px;color:#1f2937;font-size:14px">
      <p>Hola,</p>
      <p>Este es un email de prueba enviado desde el módulo Auto-Plan de EOS.</p>
      <p>Si recibes esto, los emails automáticos del cron diario funcionarán correctamente.</p>
      <p style="margin-top:18px;font-size:12px;color:#6b7280">Disparado por: <b>{u}</b><br>Fecha: {datetime.now().isoformat()}</p>
    </div>
  </div>
</body></html>"""
    try:
        import threading, sys, os as _os
        sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        notif = SistemaNotificaciones()
        threading.Thread(
            target=notif._enviar_email,
            args=(asunto, html, [email_dest]),
            daemon=True
        ).start()
        return jsonify({'ok': True, 'mensaje': f'Email enviado a {email_dest} (puede tardar 30s)'})
    except Exception as e:
        return jsonify({'error': f'Error enviando email: {e}'}), 500


# ════════════════════════════════════════════════════════════════════════
# Conteo cíclico — endpoints
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/conteo-ciclico/calendario', methods=['GET'])
def conteo_calendario():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 30))
    except Exception:
        dias = 30
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, fecha, material_id, material_nombre, categoria_abc,
               asignado_a, estado, stock_esperado_g, stock_real_g, diferencia_g, notas
        FROM conteo_ciclico_calendario
        WHERE fecha BETWEEN date('now') AND date('now', '+' || ? || ' days')
        ORDER BY fecha, categoria_abc, material_nombre
    """, (dias,)).fetchall()
    cols = [d[0] for d in c.description]
    items = [dict(zip(cols, r)) for r in rows]
    pendientes = sum(1 for it in items if it['estado'] == 'programado')
    return jsonify({'items': items, 'total': len(items), 'pendientes': pendientes})


@bp.route('/api/conteo-ciclico/<int:item_id>/registrar', methods=['POST'])
def conteo_registrar(item_id):
    u, err, code = _auth()
    if err:
        return err, code
    d = request.json or {}
    stock_real = d.get('stock_real_g')
    if stock_real is None:
        return jsonify({'error': 'stock_real_g requerido'}), 400
    stock_real = float(stock_real)
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT material_id, stock_esperado_g FROM conteo_ciclico_calendario WHERE id=?",
        (item_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'Conteo no existe'}), 404
    material_id, stock_esperado = row
    # Calcular esperado si no está seteado: sumar movimientos
    if stock_esperado is None:
        r = c.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN tipo IN ('Ingreso','Ajuste','Devolucion') THEN cantidad
                     WHEN tipo IN ('Salida','Consumo') THEN -cantidad
                     ELSE 0 END
            ), 0) FROM movimientos WHERE material_id=?
        """, (material_id,)).fetchone()
        stock_esperado = float(r[0] if r else 0)
    diferencia = stock_real - (stock_esperado or 0)
    pct = abs(diferencia) / max(1, stock_esperado or 1) * 100
    estado = 'con_diferencia' if pct > 5 else 'cerrado'
    c.execute("""
        UPDATE conteo_ciclico_calendario SET
          stock_esperado_g=?, stock_real_g=?, diferencia_g=?,
          estado=?, terminado_at=datetime('now'), terminado_por=?,
          notas=COALESCE(?, notas)
        WHERE id=?
    """, (stock_esperado, stock_real, diferencia, estado, u, d.get('notas'), item_id))
    # Actualizar último conteo en config
    c.execute("""
        INSERT OR REPLACE INTO conteo_ciclico_config
          (material_id, categoria_abc, frecuencia_dias, ultimo_conteo_fecha,
           ultimo_conteo_diferencia, requiere_validacion, actualizado_en)
        SELECT material_id, COALESCE(categoria_abc,'C'), 90, date('now'), ?,
               CASE WHEN ABS(?) > stock_esperado_g * 0.05 THEN 1 ELSE 0 END,
               datetime('now')
        FROM conteo_ciclico_calendario WHERE id=?
    """, (diferencia, diferencia, item_id))
    conn.commit()
    return jsonify({'ok': True, 'diferencia_g': diferencia, 'estado': estado, 'pct_diferencia': round(pct, 2)})


@bp.route('/api/conteo-ciclico/configs', methods=['GET', 'POST'])
def conteo_configs():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""
            INSERT OR REPLACE INTO conteo_ciclico_config
              (material_id, categoria_abc, frecuencia_dias, actualizado_en)
            VALUES (?, ?, ?, datetime('now'))
        """, (d.get('material_id'), d.get('categoria_abc') or 'C',
              int(d.get('frecuencia_dias') or 90)))
        conn.commit()
        return jsonify({'ok': True})
    rows = c.execute(
        "SELECT * FROM conteo_ciclico_config ORDER BY categoria_abc, material_id"
    ).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'configs': [dict(zip(cols, r)) for r in rows]})


# ════════════════════════════════════════════════════════════════════════
# Perfil riesgo
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/auto-plan/configs/perfil-riesgo', methods=['GET', 'POST'])
def perfil_riesgo():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""
            INSERT OR REPLACE INTO producto_perfil_riesgo
              (producto_nombre, tiene_pigmento, color_descripcion, es_acido,
               requiere_asepsia_extra, riesgo_arrastre_pct, notas, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            d.get('producto_nombre'),
            1 if d.get('tiene_pigmento') else 0,
            d.get('color_descripcion'),
            1 if d.get('es_acido') else 0,
            1 if d.get('requiere_asepsia_extra') else 0,
            int(d.get('riesgo_arrastre_pct') or 5),
            d.get('notas'),
        ))
        conn.commit()
        return jsonify({'ok': True})
    rows = c.execute(
        "SELECT * FROM producto_perfil_riesgo ORDER BY producto_nombre"
    ).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'perfiles': [dict(zip(cols, r)) for r in rows]})


# ════════════════════════════════════════════════════════════════════════
# Asistente accionable — tools
# ════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════
# FORECAST MULTI-HORIZONTE — 1sem / 1m / 2m / 3m / 6m / 12m
# ════════════════════════════════════════════════════════════════════════
# Sebastian (30-abr-2026): "ideal que sea semanal, 1 mes, 2 meses 3 meses
# 6 meses 1 año... la app saca todo, necesidades completas, y quedan
# además las asignaciones semanales".
#
# Devuelve para el horizonte solicitado:
#  - producciones_por_mes (count, kg total, lotes)
#  - mp_consumo_mensual (gramos por material)
#  - envases_consumo_mensual (unidades por código MEE)
#  - capacidad_uso_pct por área por mes
#  - compras_urgentes (envases China que tocan comprar YA)
#  - alertas_capacidad
#  - costo_proyectado (estimado si hay precios de MP)

def _producciones_futuras_kg(c, producto):
    """Suma de kg de TODAS las producciones futuras (BD + Calendar) con
    matcher robusto + parser kg agresivo. Zero-error-enterprise.
    """
    total_kg = 0.0
    eventos_count = 0
    # BD
    rows = c.execute("""
        SELECT cantidad_kg FROM produccion_programada
        WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
          AND estado IN ('pendiente','en_proceso')
          AND fecha_programada >= date('now')
    """, (producto,)).fetchall()
    for r in rows:
        if r[0]:
            total_kg += float(r[0])
            eventos_count += 1
    # Calendar con match robusto
    eventos = _calendar_events_cached()
    alias = _alias_calendar_for(c, producto)
    fecha_hoy = datetime.now().date()
    for ev in eventos:
        try:
            f = datetime.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
            if f < fecha_hoy:
                continue
        except Exception:
            continue
        score = _match_producto_evento(producto, alias, ev.get('titulo'), ev.get('descripcion', ''))
        if score < 60:
            continue
        kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion', ''))
        if kg:
            total_kg += kg
            eventos_count += 1
        else:
            # Sin kg detectado pero match alto: usar lote_size_kg del producto
            r = c.execute(
                "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
                (producto,)
            ).fetchone()
            if r and r[0]:
                total_kg += float(r[0])
                eventos_count += 1
    return total_kg, eventos_count


def _factor_g_por_unidad(c, producto):
    """Devuelve el factor g/unidad. Fallback inteligente por categoría."""
    # 1) Presentación default
    r = c.execute("""
        SELECT factor_g_por_unidad, peso_g, volumen_ml FROM producto_presentaciones
        WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?)) AND activo=1
        ORDER BY es_default DESC, id ASC LIMIT 1
    """, (producto,)).fetchone()
    if r:
        if r[0] and r[0] > 0:
            return float(r[0])
        if r[1] and r[1] > 0:
            return float(r[1])
        if r[2] and r[2] > 0:
            return float(r[2])
    # 2) Fallback por categoría
    cat_row = c.execute(
        "SELECT categoria FROM sku_planeacion_config WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
        (producto,)
    ).fetchone()
    cat = (cat_row[0] if cat_row else '') or ''
    factores_cat = {
        'limpiador': 150.0,        # 150 mL
        'hidratante': 50.0,        # 50 mL airless
        'suero': 30.0,             # 30 mL típico
        'suero_vit_c': 30.0,
        'suero_ah': 30.0,
        'contorno': 12.0,          # 10-15 mL
        'contorno_ojos': 12.0,
        'maxlash': 4.5,
        'blush_balm': 6.0,
        'mascarilla': 50.0,
        'crema_corporal': 200.0,
        'esencia': 100.0,
    }
    if cat in factores_cat:
        return factores_cat[cat]
    # 3) Heurística por nombre del producto
    nombre_upper = (producto or '').upper()
    if 'LIMPIADOR' in nombre_upper:
        return 150.0
    if 'HIDRATANTE' in nombre_upper or 'EMULSION' in nombre_upper:
        return 50.0
    if 'CONTORNO' in nombre_upper:
        return 12.0
    if 'MAXLASH' in nombre_upper:
        return 4.5
    if 'CREMA CORPORAL' in nombre_upper:
        return 200.0
    if 'MASCARILLA' in nombre_upper:
        return 50.0
    return 30.0  # default suero


def _calcular_demanda_suministro(c, producto, dias_horizonte=60):
    """Lógica MRP: demanda proyectada vs suministro disponible.

    Sebastian (30-abr-2026): "sabemos cuanto se vende y cuanto se necesita
    por shopify, en el calendario aparece que se ha producido hasta hoy
    para excluirlos... dice cuantos kilos para que sepas cuanto hacer".

    Returns:
        dict con velocidad, stock, producciones_futuras_kg/unidades,
        demanda, suministro_total, deficit, cubierto_hasta_dias
    """
    velocidad, factor = _velocidad_total_producto(c, producto)
    velocidad_proj = velocidad * factor
    if velocidad_proj <= 0:
        velocidad_proj = 0.5  # fallback conservador
    stock_actual = _stock_actual_pt(c, producto)
    prod_kg, prod_count = _producciones_futuras_kg(c, producto)
    factor_g = _factor_g_por_unidad(c, producto)
    # Convertir kg producidos a unidades equivalentes
    suministro_futuro_unidades = (prod_kg * 1000) / max(factor_g, 1)
    suministro_total = stock_actual + suministro_futuro_unidades
    demanda = velocidad_proj * dias_horizonte
    cubierto_hasta_dias = suministro_total / max(velocidad_proj, 0.01)
    return {
        'velocidad_dia': velocidad_proj,
        'stock_actual_unid': stock_actual,
        'producciones_futuras_kg': round(prod_kg, 1),
        'producciones_futuras_count': prod_count,
        'suministro_futuro_unidades': round(suministro_futuro_unidades, 0),
        'suministro_total_unidades': round(suministro_total, 0),
        'demanda_unidades': round(demanda, 0),
        'deficit_unidades': round(max(0, demanda - suministro_total), 0),
        'cubierto_hasta_dias': round(cubierto_hasta_dias, 1),
        'factor_g': factor_g,
    }


def _generar_proyeccion_lotes(c, horizonte_meses):
    """Genera proyección de lotes con LÓGICA MRP REAL.

    Sebastian (30-abr-2026): "la lógica seria sabemos cuanto se vende y
    cuanto se necesita por shopify, en el calendario aparece que se ha
    producido hasta hoy para excluirlos".

    Para cada SKU:
      1. Calcula demanda (velocidad × cobertura objetivo)
      2. Resta suministro existente (stock + producciones futuras BD + Calendar)
      3. Si déficit > 0 O cubierto_hasta_dias < margen → programar lote(s)
      4. Si ya está cubierto → SKIP (no duplicar)
    """
    proyeccion = []
    skus = c.execute("""
        SELECT spc.producto_nombre, spc.cadencia_dias, spc.cobertura_target_dias,
               spc.cobertura_min_dias, spc.merma_pct, fh.lote_size_kg, spc.prioridad
        FROM sku_planeacion_config spc
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(spc.producto_nombre))
        WHERE spc.activo = 1 AND fh.lote_size_kg IS NOT NULL
        ORDER BY spc.prioridad ASC, spc.producto_nombre
    """).fetchall()

    fecha_hoy = datetime.now().date()
    fecha_fin = fecha_hoy + timedelta(days=horizonte_meses * 30)
    LOTES_MAX_POR_DIA = 2
    MARGEN_DIAS = 20  # Sebastian: producir 20d antes de agotar
    lotes_por_fecha = {}  # ISO → count

    def _ajustar_a_lmv_disponible(fecha_base):
        f = fecha_base
        for _ in range(120):
            while f.weekday() not in (0, 2, 4):
                f += timedelta(days=1)
            iso = f.isoformat()
            ya_hay_proj = lotes_por_fecha.get(iso, 0)
            try:
                ya_hay_bd = c.execute(
                    "SELECT COUNT(*) FROM produccion_programada WHERE date(fecha_programada)=? AND estado IN ('pendiente','en_proceso')",
                    (iso,)
                ).fetchone()[0]
            except Exception:
                ya_hay_bd = 0
            if (ya_hay_bd + ya_hay_proj) < LOTES_MAX_POR_DIA:
                return f
            f += timedelta(days=1)
        return f

    for producto, cadencia, cob_target, cob_min, merma, lote_kg, prioridad in skus:
        # ── LÓGICA MRP ──
        info = _calcular_demanda_suministro(c, producto, dias_horizonte=horizonte_meses * 30)
        velocidad_proj = info['velocidad_dia']
        cubierto_hasta = info['cubierto_hasta_dias']
        suministro_total = info['suministro_total_unidades']
        demanda = info['demanda_unidades']
        cob_target_efectivo = cob_target or 60
        margen_minimo = cob_min or MARGEN_DIAS

        # Solo SKIP si REALMENTE está cubierto MUY arriba del horizonte
        # (con buffer extra de margen). NO se basa en producciones_futuras_count
        # porque ese cuenta también producciones_programadas que aún hay que
        # producir — esas SÍ aparecen en el plan.
        if cubierto_hasta >= (horizonte_meses * 30 + margen_minimo):
            # Más cubierto que el horizonte+margen — definitivamente no necesita
            continue

        factor_g = info['factor_g']
        unidades_por_lote = (lote_kg * 1000) / max(factor_g, 1)

        # Calcular lotes necesarios
        unidades_faltan = max(0, demanda - suministro_total)
        lotes_a_programar = int((unidades_faltan / max(unidades_por_lote, 1)) + 0.5)

        # Fallback si NO hay velocidad (sin datos Shopify) o NO hay déficit:
        # programar según CADENCIA configurada — Sebastian: "monte todo
        # automáticamente, no quiero ver el calendario vacío".
        if cadencia and lotes_a_programar == 0:
            # Cuántos lotes caben en el horizonte según cadencia
            lotes_por_cadencia = max(1, int((horizonte_meses * 30) / cadencia))
            lotes_a_programar = lotes_por_cadencia
        elif lotes_a_programar == 0 and horizonte_meses >= 2:
            # Sin cadencia y sin déficit: al menos 1 lote por SKU en 2m+
            lotes_a_programar = 1

        if lotes_a_programar == 0:
            continue

        # Fecha del primer lote
        ultima_prod = _ultima_produccion(c, producto)
        if ultima_prod and cadencia:
            # Próximo según cadencia desde la última real
            dias_desde_ult = (fecha_hoy - ultima_prod).days
            if dias_desde_ult >= cadencia:
                # Ya tocaba — programar pronto
                dias_offset = max(2, (prioridad or 3))
            else:
                dias_offset = max(2, cadencia - dias_desde_ult)
        elif cubierto_hasta > margen_minimo:
            dias_offset = max(2, int(cubierto_hasta - margen_minimo))
        else:
            # Distribuir según prioridad para no saturar fecha_hoy
            dias_offset = max(2, (prioridad or 3) * 2)

        fecha_base = fecha_hoy + timedelta(days=dias_offset)
        siguiente = _ajustar_a_lmv_disponible(fecha_base)
        intervalo = cadencia if cadencia else max(int(unidades_por_lote / max(velocidad_proj, 0.5)), 14)

        for n_lote in range(lotes_a_programar):
            if siguiente > fecha_fin:
                break
            iso = siguiente.isoformat()
            lotes_por_fecha[iso] = lotes_por_fecha.get(iso, 0) + 1
            proyeccion.append({
                'producto': producto,
                'fecha': iso,
                'mes': siguiente.strftime('%Y-%m'),
                'lote_kg': lote_kg,
                'kg_con_merma': lote_kg * (1 + (merma or 0) / 100.0),
                'velocidad_dia': velocidad_proj,
                'tipo': 'mrp',
                'cadencia_dias': cadencia,
                'razon_mrp': f'demanda {demanda:.0f}u, suministro {suministro_total:.0f}u, déficit {unidades_faltan:.0f}u',
                'lote_num': n_lote + 1,
                'lotes_total_planeados': lotes_a_programar,
                'mrp_info': info,
            })
            siguiente = _ajustar_a_lmv_disponible(siguiente + timedelta(days=intervalo))

    return sorted(proyeccion, key=lambda x: x['fecha'])


@bp.route('/api/planta/forecast', methods=['GET'])
def planta_forecast():
    """Forecast multi-horizonte. Querystring:
       ?meses=1|2|3|6|12 (default 3)

    Devuelve plan COMPLETO + necesidades agregadas para el horizonte:
    - producciones_proyectadas (lista cronológica)
    - resumen_mensual: por mes, cuántos lotes, kg total
    - mp_consumo_mensual: por material × mes (g + kg)
    - envases_necesarios: por código envase × mes (unidades)
    - capacidad_uso: por área × mes (% capacidad usada)
    - compras_urgentes: lo que hay que pedir HOY por lead time
    - alertas: capacidad excedida, MP en déficit a futuro
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        meses = int(request.args.get('meses', 3))
    except Exception:
        meses = 3
    meses = max(1, min(meses, 12))

    conn = get_db(); c = conn.cursor()
    proyeccion = _generar_proyeccion_lotes(c, meses)

    # Resumen por mes
    resumen_mensual = {}
    for p in proyeccion:
        m = p['mes']
        if m not in resumen_mensual:
            resumen_mensual[m] = {'lotes': 0, 'kg_total': 0, 'productos_distintos': set()}
        resumen_mensual[m]['lotes'] += 1
        resumen_mensual[m]['kg_total'] += p['kg_con_merma']
        resumen_mensual[m]['productos_distintos'].add(p['producto'])
    for m in resumen_mensual:
        resumen_mensual[m]['productos_distintos'] = len(resumen_mensual[m]['productos_distintos'])
        resumen_mensual[m]['kg_total'] = round(resumen_mensual[m]['kg_total'], 1)

    # Consumo MP por mes
    mp_consumo = {}  # mes -> material_id -> {nombre, gramos}
    for p in proyeccion:
        items = c.execute("""
            SELECT material_id, material_nombre, COALESCE(cantidad_g_por_lote,0), porcentaje
            FROM formula_items
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
        """, (p['producto'],)).fetchall()
        for mat_id, mat_nom, cant_lote, pct in items:
            req_g = cant_lote
            if not req_g and pct:
                req_g = (pct / 100.0) * (p['lote_kg'] or 0) * 1000
            req_g = req_g * (1 + (p.get('merma_pct') or 0) / 100.0)
            m = p['mes']
            if m not in mp_consumo:
                mp_consumo[m] = {}
            if mat_id not in mp_consumo[m]:
                mp_consumo[m][mat_id] = {'nombre': mat_nom, 'gramos': 0}
            mp_consumo[m][mat_id]['gramos'] += req_g

    # Envases por mes (necesita producto_presentaciones)
    envases_consumo = {}
    for p in proyeccion:
        # Buscar presentación default y envase
        pres = c.execute("""
            SELECT envase_codigo, factor_g_por_unidad, etiqueta
            FROM producto_presentaciones
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND activo=1
            ORDER BY es_default DESC, id ASC
            LIMIT 1
        """, (p['producto'],)).fetchone()
        if not pres or not pres[0]:
            continue
        env_codigo, factor, etiqueta = pres
        if not factor or factor <= 0:
            # Estimar factor desde lote y volumen ml (asumiendo densidad ~1)
            continue
        unidades = (p['kg_con_merma'] * 1000) / factor
        m = p['mes']
        if m not in envases_consumo:
            envases_consumo[m] = {}
        if env_codigo not in envases_consumo[m]:
            envases_consumo[m][env_codigo] = {'etiqueta': etiqueta, 'unidades': 0, 'productos': set()}
        envases_consumo[m][env_codigo]['unidades'] += unidades
        envases_consumo[m][env_codigo]['productos'].add(p['producto'])
    # Convertir set a list para JSON
    for m in envases_consumo:
        for cod in envases_consumo[m]:
            envases_consumo[m][cod]['productos'] = list(envases_consumo[m][cod]['productos'])
            envases_consumo[m][cod]['unidades'] = int(envases_consumo[m][cod]['unidades'])

    # Capacidad por área por mes (cuántos lotes vs días disponibles L/M/V)
    capacidad_uso = {}
    for p in proyeccion:
        # Asignación implícita: por categoría
        # FAB1=lotes >50kg, FAB2=lotes 20-50kg, FAB3=lotes >100kg, FAB_FLOAT=<20kg
        kg = p['lote_kg'] or 0
        if kg >= 100:
            area = 'FAB3'
        elif kg >= 50:
            area = 'FAB1'
        elif kg >= 20:
            area = 'FAB2'
        else:
            area = 'FAB_FLOAT'
        m = p['mes']
        capacidad_uso.setdefault(m, {}).setdefault(area, 0)
        capacidad_uso[m][area] += 1
    # 12 días LMV/mes promedio (4.3 sem × 3 días)
    DIAS_LMV_MES = 13
    alertas_capacidad = []
    for m, areas in capacidad_uso.items():
        for area, lotes in areas.items():
            uso_pct = round((lotes / DIAS_LMV_MES) * 100)
            capacidad_uso[m][area] = {'lotes': lotes, 'uso_pct': uso_pct}
            if uso_pct > 90:
                alertas_capacidad.append({
                    'mes': m, 'area': area, 'lotes': lotes, 'uso_pct': uso_pct,
                    'severidad': 'critica' if uso_pct > 100 else 'alta',
                    'mensaje': f'{area} en {m}: {lotes} lotes vs ~{DIAS_LMV_MES} días disponibles ({uso_pct}%)'
                })

    # Compras urgentes: envases China con lead 180d
    compras_urgentes = []
    fecha_hoy = datetime.now().date()
    for m, envs in envases_consumo.items():
        for env_codigo, info in envs.items():
            try:
                mes_dt = datetime.strptime(m, '%Y-%m').date()
                dias_hasta_mes = (mes_dt - fecha_hoy).days
            except Exception:
                continue
            # Buscar lead time
            lt = c.execute(
                "SELECT lead_time_dias, origen FROM mp_lead_time_config WHERE material_id=?",
                (env_codigo,)
            ).fetchone()
            if not lt:
                lt = (14, 'local')
            lead, origen = lt
            # Si dias_hasta_mes < lead → debes comprar YA
            if dias_hasta_mes < lead:
                compras_urgentes.append({
                    'envase_codigo': env_codigo,
                    'etiqueta': info['etiqueta'],
                    'unidades_requeridas': info['unidades'],
                    'mes_objetivo': m,
                    'lead_time_dias': lead,
                    'origen': origen,
                    'dias_hasta_mes': dias_hasta_mes,
                    'urgencia': 'critica' if origen in ('china', 'usa', 'europa') else 'alta',
                })

    # Costo proyectado (si tenemos precios de MP)
    costo_total_estimado = 0
    try:
        for m, mats in mp_consumo.items():
            for mat_id, info in mats.items():
                pr = c.execute(
                    "SELECT precio_unitario FROM movimientos WHERE material_id=? AND precio_unitario>0 ORDER BY id DESC LIMIT 1",
                    (mat_id,)
                ).fetchone()
                precio_g = (pr[0] / 1000.0) if pr else 0
                costo_total_estimado += info['gramos'] * precio_g
    except Exception:
        pass

    return jsonify({
        'horizonte_meses': meses,
        'fecha_inicio': fecha_hoy.isoformat(),
        'fecha_fin': (fecha_hoy + timedelta(days=meses * 30)).isoformat(),
        'producciones_proyectadas': proyeccion,
        'resumen_mensual': resumen_mensual,
        'mp_consumo_mensual': mp_consumo,
        'envases_consumo_mensual': envases_consumo,
        'capacidad_uso_mensual': capacidad_uso,
        'compras_urgentes': compras_urgentes,
        'alertas_capacidad': alertas_capacidad,
        'costo_total_estimado': round(costo_total_estimado, 0),
        'kpis': {
            'total_lotes_proyectados': len(proyeccion),
            'total_kg_proyectados': round(sum(p['kg_con_merma'] for p in proyeccion), 1),
            'productos_distintos': len(set(p['producto'] for p in proyeccion)),
            'meses_con_alerta_capacidad': len(set(a['mes'] for a in alertas_capacidad)),
            'compras_urgentes_count': len(compras_urgentes),
        },
    })


# ════════════════════════════════════════════════════════════════════════
# ASIGNACIÓN SEMANAL — Qué se hace en cada área cada día
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/planta/asignacion-semanal', methods=['GET'])
def planta_asignacion_semanal():
    """Vista por área × día de la semana.

    Sebastian (30-abr-2026): "asignaciones semanales que sería diferente
    pues que se hace en cada área".

    Querystring: ?fecha=YYYY-MM-DD (default = lunes de esta semana)

    Devuelve:
      areas: [{codigo, nombre, dias: {lunes, martes, miercoles, jueves, viernes}}]
      cada día tiene: producciones[], envasados[], conteos[], limpiezas[], operarios[]
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            base = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except Exception:
            base = datetime.now().date()
    else:
        base = datetime.now().date()
    # Encontrar lunes de esa semana
    while base.weekday() != 0:
        base -= timedelta(days=1)
    dias_semana = [base + timedelta(days=i) for i in range(5)]  # L-V
    nombres_dia = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']

    conn = get_db(); c = conn.cursor()
    fecha_inicio = dias_semana[0].isoformat()
    fecha_fin = dias_semana[-1].isoformat()

    # Cargar áreas activas con flag de limpieza profunda
    areas = c.execute("""
        SELECT codigo, nombre, requiere_limpieza_profunda, puede_producir, puede_envasar, tipo
        FROM areas_planta WHERE activo=1
        ORDER BY orden
    """).fetchall()

    # Producciones programadas en la semana
    prods = c.execute("""
        SELECT pp.id, pp.producto, pp.fecha_programada, pp.lotes,
               pp.area_id, ap.codigo as area_codigo,
               op_disp.nombre || ' ' || COALESCE(op_disp.apellido,'') as op_disp_nombre,
               op_elab.nombre || ' ' || COALESCE(op_elab.apellido,'') as op_elab_nombre,
               op_env.nombre  || ' ' || COALESCE(op_env.apellido,'')  as op_env_nombre,
               pp.estado
        FROM produccion_programada pp
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        LEFT JOIN operarios_planta op_disp ON op_disp.id = pp.operario_dispensacion_id
        LEFT JOIN operarios_planta op_elab ON op_elab.id = pp.operario_elaboracion_id
        LEFT JOIN operarios_planta op_env  ON op_env.id  = pp.operario_envasado_id
        WHERE pp.fecha_programada BETWEEN ? AND ?
          AND pp.estado IN ('pendiente','en_proceso')
    """, (fecha_inicio, fecha_fin)).fetchall()

    # Limpieza profunda calendario
    limpiezas = c.execute("""
        SELECT fecha, area_codigo, asignado_a, estado, razon_asignacion
        FROM limpieza_profunda_calendario
        WHERE fecha BETWEEN ? AND ?
    """, (fecha_inicio, fecha_fin)).fetchall()

    # Conteos cíclicos
    conteos = c.execute("""
        SELECT fecha, material_id, material_nombre, asignado_a, estado, categoria_abc
        FROM conteo_ciclico_calendario
        WHERE fecha BETWEEN ? AND ?
    """, (fecha_inicio, fecha_fin)).fetchall()

    # Tareas operativas (acondicionamiento, etc)
    tareas = c.execute("""
        SELECT id, titulo, tipo, fecha_objetivo, asignado_a, producto_relacionado, estado
        FROM tareas_operativas
        WHERE fecha_objetivo BETWEEN ? AND ?
          AND estado IN ('pendiente','en_proceso')
    """, (fecha_inicio, fecha_fin)).fetchall()

    # Armar estructura por área
    resultado = []
    for area_codigo, area_nombre, req_limp, puede_prod, puede_env, tipo in areas:
        area_data = {
            'codigo': area_codigo, 'nombre': area_nombre,
            'tipo': tipo, 'requiere_limpieza_profunda': bool(req_limp),
            'puede_producir': bool(puede_prod), 'puede_envasar': bool(puede_env),
            'dias': {},
        }
        for i, dia in enumerate(dias_semana):
            dia_str = dia.isoformat()
            nombre_dia = nombres_dia[i]
            es_lmv = dia.weekday() in (0, 2, 4)
            area_data['dias'][nombre_dia] = {
                'fecha': dia_str,
                'es_dia_produccion': es_lmv,
                'es_dia_acond_conteo': not es_lmv,
                'producciones': [],
                'limpiezas': [],
                'conteos': [],
                'tareas': [],
            }
        # Llenar producciones
        for p in prods:
            if p[5] != area_codigo:
                continue
            try:
                f = datetime.strptime(p[2][:10], '%Y-%m-%d').date()
                idx = (f - dias_semana[0]).days
                if idx < 0 or idx > 4:
                    continue
                nd = nombres_dia[idx]
                area_data['dias'][nd]['producciones'].append({
                    'id': p[0], 'producto': p[1], 'lotes': p[3],
                    'op_dispensacion': (p[6] or '').strip() or None,
                    'op_elaboracion': (p[7] or '').strip() or None,
                    'op_envasado': (p[8] or '').strip() or None,
                    'estado': p[9],
                })
            except Exception:
                pass
        # Llenar limpiezas
        for l in limpiezas:
            if l[1] != area_codigo:
                continue
            try:
                f = datetime.strptime(l[0][:10], '%Y-%m-%d').date()
                idx = (f - dias_semana[0]).days
                if 0 <= idx <= 4:
                    area_data['dias'][nombres_dia[idx]]['limpiezas'].append({
                        'asignado_a': l[2], 'estado': l[3], 'razon': l[4]
                    })
            except Exception:
                pass
        # Conteos cíclicos van solo a áreas de almacén (ALMP, ALMPT, ALM_MP)
        if area_codigo in ('ALMP', 'ALMPT', 'ALM_MP', 'BDG'):
            for cn in conteos:
                try:
                    f = datetime.strptime(cn[0][:10], '%Y-%m-%d').date()
                    idx = (f - dias_semana[0]).days
                    if 0 <= idx <= 4:
                        area_data['dias'][nombres_dia[idx]]['conteos'].append({
                            'material': cn[2] or cn[1],
                            'asignado_a': cn[3], 'estado': cn[4], 'abc': cn[5],
                        })
                except Exception:
                    pass
        resultado.append(area_data)

    # Tareas no asociadas a área: sumarizar aparte
    tareas_globales = []
    for t in tareas:
        try:
            f = datetime.strptime((t[3] or '')[:10], '%Y-%m-%d').date()
            idx = (f - dias_semana[0]).days
            if 0 <= idx <= 4:
                tareas_globales.append({
                    'id': t[0], 'titulo': t[1], 'tipo': t[2],
                    'fecha': nombres_dia[idx], 'asignado_a': t[4],
                    'producto': t[5], 'estado': t[6],
                })
        except Exception:
            pass

    return jsonify({
        'semana_inicio': fecha_inicio,
        'semana_fin': fecha_fin,
        'dias': [{'nombre': nombres_dia[i], 'fecha': dias_semana[i].isoformat(),
                  'weekday': dias_semana[i].weekday(),
                  'es_lmv': dias_semana[i].weekday() in (0, 2, 4)} for i in range(5)],
        'areas': resultado,
        'tareas_globales': tareas_globales,
    })


# ════════════════════════════════════════════════════════════════════════
# Dossier de Lote PDF — INVIMA / trazabilidad completa
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/planta/dossier-lote/<lote>', methods=['GET'])
def dossier_lote_pdf(lote):
    """Genera PDF con TODA la trazabilidad de un lote PT:
       - Datos producto + presentación
       - Producción programada (fecha, área, operarios)
       - Eventos de envasado
       - Resultados microbiológicos
       - Disposición de cola_liberacion
       - Movimientos de MP consumidas

    Sebastian: "auto-evidencia regulatoria (INVIMA)" — sirve como
    documentación lista para auditoría."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from flask import Response
    conn = get_db(); c = conn.cursor()

    # Datos envasado
    env = c.execute("""
        SELECT pe.id, pe.produccion_id, pe.producto_nombre, pe.lote,
               pe.presentacion_etiqueta, pe.unidades_planeadas,
               pe.unidades_envasadas, pe.envase_codigo, pe.iniciado_at,
               pe.iniciado_por, pe.terminado_at, pe.terminado_por,
               pe.estado, pp.fecha_programada, pp.cantidad_kg,
               ap.codigo as area_codigo, ap.nombre as area_nombre
        FROM produccion_envasado pe
        LEFT JOIN produccion_programada pp ON pp.id = pe.produccion_id
        LEFT JOIN areas_planta ap ON ap.id = pp.area_id
        WHERE pe.lote = ?
        ORDER BY pe.id DESC LIMIT 1
    """, (lote,)).fetchone()

    if not env:
        return jsonify({'error': 'Lote no encontrado en envasados'}), 404

    # Resultados micro
    micro_rows = c.execute("""
        SELECT microorganismo, valor, estado, fecha_analisis, deadline_resultado
        FROM calidad_micro_resultados
        WHERE lote = ? ORDER BY fecha_analisis DESC
    """, (lote,)).fetchall()

    # Cola liberación
    cola = c.execute("""
        SELECT estado, disposicion, fecha_envasado, fecha_min_liberacion,
               aprobado_por, aprobado_at, notas
        FROM cola_liberacion WHERE lote = ?
        ORDER BY id DESC LIMIT 1
    """, (lote,)).fetchone()

    # Operarios asignados a la producción
    ops = c.execute("""
        SELECT op.nombre, op.apellido, op.rol_predeterminado
        FROM produccion_programada pp
        LEFT JOIN operarios_planta op ON op.id IN (
            pp.operario_dispensacion_id, pp.operario_elaboracion_id,
            pp.operario_envasado_id, pp.operario_acondicionamiento_id
        )
        WHERE pp.id = ? AND op.id IS NOT NULL
    """, (env[1],)).fetchall() if env[1] else []

    # Generar PDF
    try:
        from fpdf import FPDF
    except ImportError:
        return jsonify({'error': 'fpdf no disponible'}), 500

    class PDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f'Dossier · Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} · Pag. {self.page_no()}', align='C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    W = pdf.w - 20

    # Header
    pdf.set_fill_color(124, 58, 237)
    pdf.rect(10, 10, W, 22, 'F')
    pdf.set_xy(12, 13)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(W - 4, 8, 'ESPAGIRIA LABORATORIO S.A.S.', ln=True)
    pdf.set_x(12)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(220, 220, 220)
    pdf.cell(W - 4, 5, 'Dossier de lote · Trazabilidad INVIMA', ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Título
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(W, 8, f'DOSSIER LOTE: {lote}', ln=True, align='C')
    pdf.ln(4)

    # Producto
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(W, 7, ' PRODUCTO', border=1, fill=True, ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(50, 6, '  Nombre:', border='LB')
    pdf.cell(W - 50, 6, str(env[2] or ''), border='RB', ln=True)
    pdf.cell(50, 6, '  Presentación:', border='LB')
    pdf.cell(W - 50, 6, str(env[4] or '—'), border='RB', ln=True)
    pdf.cell(50, 6, '  Envase:', border='LB')
    pdf.cell(W - 50, 6, str(env[7] or '—'), border='RB', ln=True)
    pdf.cell(50, 6, '  Cantidad lote:', border='LB')
    pdf.cell(W - 50, 6, f'{env[14] or 0} kg', border='RB', ln=True)
    pdf.cell(50, 6, '  Unidades envasadas:', border='LB')
    pdf.cell(W - 50, 6, str(env[6] or 'pendiente'), border='RB', ln=True)
    pdf.ln(4)

    # Producción
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(W, 7, ' PRODUCCIÓN', border=1, fill=True, ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(50, 6, '  Fecha programada:', border='LB')
    pdf.cell(W - 50, 6, str(env[13] or '—'), border='RB', ln=True)
    pdf.cell(50, 6, '  Área:', border='LB')
    pdf.cell(W - 50, 6, f'{env[16] or "—"} ({env[15] or "—"})', border='RB', ln=True)
    if ops:
        pdf.cell(50, 6, '  Operarios:', border='LB')
        ops_txt = ', '.join(f'{o[0]} {o[1] or ""}'.strip() for o in ops)
        pdf.cell(W - 50, 6, ops_txt[:80], border='RB', ln=True)
    pdf.ln(4)

    # Envasado
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(W, 7, ' ENVASADO', border=1, fill=True, ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(50, 6, '  Iniciado:', border='LB')
    pdf.cell(W - 50, 6, f'{env[8] or "—"} por {env[9] or "—"}', border='RB', ln=True)
    pdf.cell(50, 6, '  Terminado:', border='LB')
    pdf.cell(W - 50, 6, f'{env[10] or "pendiente"} por {env[11] or "—"}', border='RB', ln=True)
    pdf.cell(50, 6, '  Estado:', border='LB')
    pdf.cell(W - 50, 6, str(env[12] or '—'), border='RB', ln=True)
    pdf.ln(4)

    # Microbiológicos
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(W, 7, ' RESULTADOS MICROBIOLÓGICOS', border=1, fill=True, ln=True)
    if not micro_rows:
        pdf.set_font('Helvetica', 'I', 9)
        pdf.cell(W, 6, '  Sin análisis registrados', border='LRB', ln=True)
    else:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(250, 250, 250)
        pdf.cell(50, 6, '  Microorganismo', border=1, fill=True)
        pdf.cell(30, 6, 'Valor', border=1, fill=True)
        pdf.cell(40, 6, 'Estado', border=1, fill=True)
        pdf.cell(W - 120, 6, 'Fecha', border=1, fill=True, ln=True)
        pdf.set_font('Helvetica', '', 8)
        for m in micro_rows:
            pdf.cell(50, 5, '  ' + str(m[0] or '')[:30], border='LR')
            pdf.cell(30, 5, str(m[1] or '—'), border='R')
            pdf.cell(40, 5, str(m[2] or '—'), border='R')
            pdf.cell(W - 120, 5, str(m[3] or '—'), border='R', ln=True)
        pdf.cell(W, 0, '', border='T', ln=True)
    pdf.ln(4)

    # Liberación
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(W, 7, ' LIBERACIÓN', border=1, fill=True, ln=True)
    pdf.set_font('Helvetica', '', 9)
    if cola:
        pdf.cell(50, 6, '  Estado:', border='LB')
        pdf.cell(W - 50, 6, str(cola[0] or '—'), border='RB', ln=True)
        pdf.cell(50, 6, '  Disposición:', border='LB')
        pdf.cell(W - 50, 6, str(cola[1] or 'pendiente'), border='RB', ln=True)
        pdf.cell(50, 6, '  Aprobado por:', border='LB')
        pdf.cell(W - 50, 6, f'{cola[4] or "—"} el {cola[5] or "—"}', border='RB', ln=True)
        if cola[6]:
            pdf.cell(50, 6, '  Notas:', border='LB')
            pdf.cell(W - 50, 6, str(cola[6])[:80], border='RB', ln=True)
    else:
        pdf.set_font('Helvetica', 'I', 9)
        pdf.cell(W, 6, '  Sin registro de liberación', border='LRB', ln=True)
    pdf.ln(8)

    # Footer firma
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(W, 5, f'Dossier auto-generado por EOS Auto-Plan · {datetime.now().isoformat()}', align='C', ln=True)

    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
    return Response(
        pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': f'inline; filename=dossier_{lote}.pdf'}
    )


@bp.route('/api/asistente/tool/<tool_name>', methods=['POST'])
def asistente_tool(tool_name):
    """Endpoints de tools que el asistente Claude puede invocar."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    args = request.json or {}
    conn = get_db(); c = conn.cursor()

    resultado = {}
    exitoso = True
    try:
        if tool_name == 'listar_alertas':
            # Buscar alertas activas (last auto_plan_run + envases déficit)
            r = c.execute("""
                SELECT ejecutado_at, alertas_criticas FROM auto_plan_runs
                ORDER BY id DESC LIMIT 1
            """).fetchone()
            resultado = {
                'ultimo_run': r[0] if r else None,
                'alertas_criticas': r[1] if r else 0,
            }
        elif tool_name == 'listar_producciones_proximas':
            dias = int(args.get('dias', 14))
            rows = c.execute("""
                SELECT producto, fecha_programada, lotes, estado
                FROM produccion_programada
                WHERE fecha_programada >= date('now')
                  AND fecha_programada <= date('now', '+' || ? || ' days')
                  AND estado IN ('pendiente','en_proceso')
                ORDER BY fecha_programada
            """, (dias,)).fetchall()
            resultado = {
                'producciones': [dict(zip(['producto', 'fecha', 'lotes', 'estado'], r)) for r in rows],
                'total': len(rows),
            }
        elif tool_name == 'capacidad_producir_sku':
            producto = args.get('producto', '').strip()
            fh = c.execute(
                "SELECT lote_size_kg FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
                (producto,)
            ).fetchone()
            if not fh:
                resultado = {'error': 'producto sin fórmula'}
            else:
                lote_kg = fh[0] or 0
                resultado = {'producto': producto, 'lote_kg': lote_kg, 'puede': lote_kg > 0}
        elif tool_name == 'ejecutar_auto_plan':
            if user not in ADMIN_USERS:
                exitoso = False
                resultado = {'error': 'Solo admin puede ejecutar auto-plan'}
            else:
                from blueprints.auto_plan_jobs import ejecutar_auto_plan_diario
                from flask import current_app
                import threading
                threading.Thread(
                    target=ejecutar_auto_plan_diario,
                    args=(current_app._get_current_object(),),
                    daemon=True
                ).start()
                resultado = {'mensaje': 'Auto-plan ejecutándose en background'}
        else:
            exitoso = False
            resultado = {'error': f'tool desconocido: {tool_name}'}
    except Exception as e:
        exitoso = False
        resultado = {'error': str(e)}

    # Log la acción
    try:
        c.execute("""
            INSERT INTO asistente_acciones_log
              (usuario, tool_invocado, tool_args, tool_resultado, exitoso)
            VALUES (?, ?, ?, ?, ?)
        """, (user, tool_name, json.dumps(args, ensure_ascii=False)[:500],
              json.dumps(resultado, ensure_ascii=False)[:1000], 1 if exitoso else 0))
        conn.commit()
    except Exception:
        pass

    return jsonify({'ok': exitoso, 'resultado': resultado})


@bp.route('/api/auto-plan/configs/emails', methods=['GET', 'POST'])
def configs_emails():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        rol = (d.get('rol') or '').strip()
        email = (d.get('email') or '').strip()
        if not rol:
            return jsonify({'error': 'rol requerido'}), 400
        c.execute("""
            UPDATE email_destinatarios_config SET
              email=?, nombre=COALESCE(?, nombre),
              recibe_resumen_diario=COALESCE(?, recibe_resumen_diario),
              recibe_alertas_criticas=COALESCE(?, recibe_alertas_criticas),
              recibe_compras_aprob=COALESCE(?, recibe_compras_aprob),
              recibe_calidad=COALESCE(?, recibe_calidad),
              recibe_agenda_personal=COALESCE(?, recibe_agenda_personal),
              actualizado_en=datetime('now')
            WHERE rol=?
        """, (
            email, d.get('nombre'),
            d.get('recibe_resumen_diario'), d.get('recibe_alertas_criticas'),
            d.get('recibe_compras_aprob'), d.get('recibe_calidad'),
            d.get('recibe_agenda_personal'), rol,
        ))
        if c.rowcount == 0:
            # Insertar nuevo si no existe
            c.execute("""
                INSERT INTO email_destinatarios_config
                  (rol, nombre, email, recibe_resumen_diario,
                   recibe_alertas_criticas, recibe_compras_aprob, recibe_calidad,
                   recibe_agenda_personal, activo, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
            """, (
                rol, d.get('nombre'), email,
                d.get('recibe_resumen_diario', 1),
                d.get('recibe_alertas_criticas', 0),
                d.get('recibe_compras_aprob', 0),
                d.get('recibe_calidad', 0),
                d.get('recibe_agenda_personal', 0),
            ))
        conn.commit()
        return jsonify({'ok': True})
    rows = c.execute(
        "SELECT * FROM email_destinatarios_config WHERE activo=1 ORDER BY rol"
    ).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'configs': [dict(zip(cols, r)) for r in rows]})
