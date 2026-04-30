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


def _ultima_produccion(c, producto):
    """Fecha de última producción (programada o real) del producto."""
    r = c.execute("""
        SELECT MAX(fecha_programada) FROM produccion_programada
        WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
          AND estado IN ('completado','en_proceso','pendiente')
    """, (producto,)).fetchone()
    if r and r[0]:
        try:
            return datetime.fromisoformat(r[0]).date()
        except Exception:
            try:
                return datetime.strptime(r[0][:10], '%Y-%m-%d').date()
            except Exception:
                return None
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

    for sku_row in skus:
        producto, categoria, cadencia, cob_target, cob_min, cob_max, merma_pct, prioridad, lote_size_kg = sku_row
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

        # Asignar fecha L/M/V que no esté ocupada
        fecha_objetivo = _next_dia_produccion(max(fecha_hoy + timedelta(days=2), ultima_prod + timedelta(days=cadencia or 0) if ultima_prod and cadencia else fecha_hoy + timedelta(days=2)))
        # Buscar siguiente L/M/V sin más de 1 producción del mismo SKU
        # Iterar hasta encontrar día disponible (max 3 intentos)
        for _ in range(8):
            ya_hay = c.execute("""
                SELECT COUNT(*) FROM produccion_programada
                WHERE date(fecha_programada) = ?
            """, (fecha_objetivo.isoformat(),)).fetchone()[0]
            if ya_hay < 3:  # max 3 producciones por día
                break
            fecha_objetivo = _next_dia_produccion(fecha_objetivo + timedelta(days=1))

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
        cur = c.execute("""
            INSERT INTO produccion_programada
              (producto, fecha_programada, lotes, estado, observaciones, origen, cantidad_kg)
            VALUES (?, ?, ?, 'pendiente', ?, 'auto_plan', ?)
        """, (
            prop['producto'], prop['fecha_programada'], prop['lotes'],
            f"AUTO-PLAN ({plan['fecha_hoy']}): {prop['razon']}",
            prop['kg_con_merma'],
        ))
        creadas_prod.append(cur.lastrowid)

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
                'presentacion_default_id', 'notas'):
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

def _generar_proyeccion_lotes(c, horizonte_meses):
    """Genera proyección de lotes para los próximos N meses considerando
    cadencias + velocidad + tendencia. NO crea registros, solo proyecta."""
    proyeccion = []
    skus = c.execute("""
        SELECT spc.producto_nombre, spc.cadencia_dias, spc.cobertura_target_dias,
               spc.cobertura_min_dias, spc.merma_pct, fh.lote_size_kg
        FROM sku_planeacion_config spc
        LEFT JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(spc.producto_nombre))
        WHERE spc.activo = 1 AND fh.lote_size_kg IS NOT NULL
    """).fetchall()

    fecha_hoy = datetime.now().date()
    fecha_fin = fecha_hoy + timedelta(days=horizonte_meses * 30)

    for producto, cadencia, cob_target, cob_min, merma, lote_kg in skus:
        velocidad, factor = _velocidad_total_producto(c, producto)
        velocidad_proj = velocidad * factor
        if velocidad_proj <= 0:
            velocidad_proj = 0.5  # fallback conservador
        stock_actual = _stock_actual_pt(c, producto)
        ultima_prod = _ultima_produccion(c, producto)

        # Generar lotes proyectados
        if cadencia:
            # Producción regular cada N días
            inicio = ultima_prod or fecha_hoy
            siguiente = inicio + timedelta(days=cadencia)
            while siguiente <= fecha_fin:
                if siguiente >= fecha_hoy:
                    proyeccion.append({
                        'producto': producto,
                        'fecha': siguiente.isoformat(),
                        'mes': siguiente.strftime('%Y-%m'),
                        'lote_kg': lote_kg,
                        'kg_con_merma': lote_kg * (1 + (merma or 0) / 100.0),
                        'velocidad_dia': velocidad_proj,
                        'tipo': 'cadencia',
                        'cadencia_dias': cadencia,
                    })
                siguiente += timedelta(days=cadencia)
        else:
            # Auto por umbral: cuándo bajará bajo cob_min
            stock_proj = stock_actual
            cursor_dia = fecha_hoy
            while cursor_dia <= fecha_fin:
                stock_proj -= velocidad_proj
                dias_restantes = stock_proj / max(velocidad_proj, 0.01)
                if dias_restantes < (cob_min or 30):
                    # Producir → cubrir cob_target
                    unidades_a_producir = velocidad_proj * (cob_target or 60)
                    proyeccion.append({
                        'producto': producto,
                        'fecha': cursor_dia.isoformat(),
                        'mes': cursor_dia.strftime('%Y-%m'),
                        'lote_kg': lote_kg,
                        'kg_con_merma': lote_kg * (1 + (merma or 0) / 100.0),
                        'velocidad_dia': velocidad_proj,
                        'tipo': 'umbral',
                        'cadencia_dias': None,
                    })
                    stock_proj += unidades_a_producir
                cursor_dia += timedelta(days=7)
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
