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


def _velocidad_y_tendencia(c, sku):
    """Velocidad de venta diaria + tendencia basada en regresión lineal
    sobre últimos 30 días Shopify. Devuelve (velocidad_actual, factor_tendencia).

    factor_tendencia:
      1.0 = estable
      >1 = subiendo (ej. 1.30 = +30%)
      <1 = bajando
    """
    # Buscar tabla con ventas históricas — varía por entorno
    # Usa 'ventas_diarias' o 'shopify_ventas_diarias' o calcula desde ordenes
    try:
        rows = c.execute("""
            SELECT fecha, COALESCE(SUM(cantidad),0)
            FROM ventas_diarias
            WHERE sku=? AND fecha >= date('now','-30 days')
            GROUP BY fecha ORDER BY fecha
        """, (sku,)).fetchall()
    except Exception:
        rows = []

    if not rows:
        # Fallback: usar consumo histórico simple
        try:
            r = c.execute("""
                SELECT COALESCE(SUM(cantidad),0)/30.0
                FROM ventas_diarias
                WHERE sku=? AND fecha >= date('now','-30 days')
            """, (sku,)).fetchone()
            return (float(r[0] or 0), 1.0)
        except Exception:
            return (0.0, 1.0)

    n = len(rows)
    if n < 5:
        avg = sum(r[1] for r in rows) / n if n else 0
        return (float(avg), 1.0)

    # Regresión lineal y = a + bx (x=día_idx, y=ventas)
    xs = list(range(n))
    ys = [float(r[1]) for r in rows]
    sum_x = sum(xs)
    sum_y = sum(ys)
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
    # Cap razonable
    factor = max(0.3, min(factor, 3.0))
    return (velocidad_actual, factor)


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

    system_prompt = f"""Eres el asistente experto de planta para Espagiria Laboratorios (HHA Group), un laboratorio cosmético colombiano con certificación INVIMA. La planta produce sueros, hidratantes, limpiadores, contornos y similares.

Tu nombre es EOS Planta y te creó Claude. Eres preciso, breve y útil — un asistente operativo, no un chatbot genérico.

CONTEXTO ACTUAL DE LA PLANTA (snapshot {datetime.now().isoformat()}):
{json.dumps(ctx, ensure_ascii=False, indent=2)}

REGLAS:
- Vit C → cadencia 30d (oxida)
- Suero AH 1.5% → cadencia 90d, lote 90kg
- L/M/V producir, Ma/Ju acondicionar/envasar/conteo cíclico
- MP mínimo 30d, ideal 60d
- Envases mínimo 90d (China lead 180d)
- 4 operarios: Mayerlin (dispensación fija), Camilo, Milton, Sebastián M.
- Áreas: FAB1/2/3, ENV1/2, DISP, LAV, ESC1, ACOND, FAB_FLOAT, CC, RECEP

Responde en español, conciso (máximo 150 palabras salvo que pidan detalle). Si te piden hacer algo (programar, crear, ejecutar), describe los pasos pero NO ejecutas — solo Sebastian/admin pueden ejecutar.

Usuario actual: {user}
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
