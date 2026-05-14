"""Blueprint plan · Plan v3 unificado de necesidades por cliente · 13-may-2026.

Incluye también /admin/verificar-codigos-mp para validar que los 146 códigos
del Excel de fórmulas Alejandro mayo-2026 existan en maestro_mps antes de
importar.

Sprint 2A · arquitectura escalable propuesta por Sebastián:
    Necesidades = bandeja de entrada (Animus DTC auto + B2B manual)
    Plan a programar = bandeja de salida (consolidador → Calendar)

Cada cliente B2B nuevo = 1 sección más en Necesidades, sin tocar arquitectura.

Endpoints:
    GET    /api/plan/necesidades         agregador (Animus + todos los B2B)
    GET    /api/pedidos-b2b              listar pedidos (filtros: cliente, estado)
    POST   /api/pedidos-b2b              crear pedido B2B
    PATCH  /api/pedidos-b2b/<id>         actualizar estado o cantidad
    DELETE /api/pedidos-b2b/<id>         cancelar (soft → estado='cancelado')

Permisos · MVP:
    - Crear/editar B2B: ADMIN_USERS o COMPRAS_ACCESS (Sebastián, Alejandro,
      Mayra, Catalina). Después, cuando exista portal cliente, el propio
      cliente podrá crear via /cliente-portal.
"""
import logging
from flask import Blueprint, jsonify, request, session

from database import get_db
from config import ADMIN_USERS, COMPRAS_ACCESS
from audit_helpers import audit_log

bp = Blueprint("plan", __name__)
log = logging.getLogger("plan")


def _require_admin_or_compras():
    user = session.get("compras_user", "")
    if not user:
        return None, ({"error": "login requerido"}, 401)
    if user in ADMIN_USERS or user in COMPRAS_ACCESS:
        return user, None
    return None, ({"error": "requiere admin o compras"}, 403)


def _require_login():
    if not session.get("compras_user"):
        return jsonify({"error": "login requerido"}), 401
    return None


# ─── CRUD pedidos_b2b ──────────────────────────────────────────────────────

@bp.route("/api/pedidos-b2b", methods=["GET"])
def listar_pedidos_b2b():
    err = _require_login()
    if err:
        return err
    cliente_id = (request.args.get("cliente_id") or "").strip()
    estado = (request.args.get("estado") or "").strip()
    incluir_terminales = request.args.get("incluir_terminales", "0") == "1"

    where, params = [], []
    if cliente_id:
        where.append("cliente_id = ?")
        params.append(cliente_id)
    if estado:
        where.append("estado = ?")
        params.append(estado)
    elif not incluir_terminales:
        # Por default ocultamos despachados/cancelados (ruido)
        where.append("estado NOT IN ('despachado','cancelado')")

    sql = """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                    cantidad_uds, ml_unidad, fecha_estimada, estado, notas,
                    creado_por, creado_at_utc, actualizado_at_utc
             FROM pedidos_b2b"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_estimada ASC, id DESC"

    rows = get_db().execute(sql, params).fetchall()
    items = [{
        "id": r[0],
        "cliente_id": r[1],
        "cliente_nombre": r[2],
        "producto_nombre": r[3],
        "cantidad_uds": r[4],
        "ml_unidad": r[5],
        "kg_equivalente": round((r[4] * r[5]) / 1000.0, 2),
        "fecha_estimada": r[6],
        "estado": r[7],
        "notas": r[8] or "",
        "creado_por": r[9],
        "creado_at_utc": r[10],
        "actualizado_at_utc": r[11],
    } for r in rows]
    return jsonify({"items": items, "total": len(items)})


@bp.route("/api/pedidos-b2b", methods=["POST"])
def crear_pedido_b2b():
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    cliente_id = (body.get("cliente_id") or "").strip()
    cliente_nombre = (body.get("cliente_nombre") or "").strip()
    producto = (body.get("producto_nombre") or "").strip()
    try:
        cantidad = int(body.get("cantidad_uds") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_uds inválida"}), 400
    try:
        ml = float(body.get("ml_unidad") or 30)
    except (ValueError, TypeError):
        return jsonify({"error": "ml_unidad inválida"}), 400
    fecha_estimada = (body.get("fecha_estimada") or "").strip()
    notas = (body.get("notas") or "").strip()

    if not cliente_id or not cliente_nombre or not producto:
        return jsonify({"error": "cliente_id, cliente_nombre y producto_nombre requeridos"}), 400
    if cantidad <= 0:
        return jsonify({"error": "cantidad_uds debe ser > 0"}), 400
    if ml <= 0:
        return jsonify({"error": "ml_unidad debe ser > 0"}), 400

    # Validar que producto exista (defensa básica)
    conn = get_db()
    cur = conn.cursor()
    prod_row = cur.execute(
        "SELECT producto_nombre FROM formula_headers WHERE producto_nombre = ?",
        (producto,),
    ).fetchone()
    if not prod_row:
        return jsonify({"error": f"producto '{producto}' no existe en formula_headers"}), 404

    cur.execute(
        """INSERT INTO pedidos_b2b
             (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
              ml_unidad, fecha_estimada, notas, creado_por)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (cliente_id, cliente_nombre, producto, cantidad, ml,
         fecha_estimada or None, notas, user),
    )
    pid = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="CREAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              despues={"cliente_id": cliente_id, "producto": producto,
                       "cantidad_uds": cantidad, "fecha": fecha_estimada})
    return jsonify({"ok": True, "id": pid}), 201


@bp.route("/api/pedidos-b2b/<int:pid>", methods=["PATCH"])
def actualizar_pedido_b2b(pid):
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT cliente_id, producto_nombre, cantidad_uds, estado, fecha_estimada
           FROM pedidos_b2b WHERE id = ?""", (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "pedido no encontrado"}), 404

    fields, params = [], []
    if "cantidad_uds" in body:
        try:
            c = int(body["cantidad_uds"])
        except (ValueError, TypeError):
            return jsonify({"error": "cantidad_uds inválida"}), 400
        if c <= 0:
            return jsonify({"error": "cantidad_uds debe ser > 0"}), 400
        fields.append("cantidad_uds = ?")
        params.append(c)
    if "fecha_estimada" in body:
        fields.append("fecha_estimada = ?")
        params.append((body["fecha_estimada"] or "").strip() or None)
    if "estado" in body:
        nuevo_estado = (body["estado"] or "").strip()
        if nuevo_estado not in ('pendiente','confirmado','en_produccion','despachado','cancelado'):
            return jsonify({"error": f"estado inválido: {nuevo_estado}"}), 400
        fields.append("estado = ?")
        params.append(nuevo_estado)
    if "notas" in body:
        fields.append("notas = ?")
        params.append((body["notas"] or "").strip())

    if not fields:
        return jsonify({"error": "sin campos para actualizar"}), 400

    params.append(pid)
    cur.execute(f"UPDATE pedidos_b2b SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    audit_log(cur, usuario=user, accion="ACTUALIZAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              antes={"cliente_id": row[0], "estado": row[3]},
              despues=body)
    return jsonify({"ok": True, "id": pid})


@bp.route("/api/pedidos-b2b/<int:pid>", methods=["DELETE"])
def cancelar_pedido_b2b(pid):
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT estado FROM pedidos_b2b WHERE id = ?", (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "pedido no encontrado"}), 404
    if row[0] in ('despachado', 'cancelado'):
        return jsonify({"error": f"pedido ya está en estado terminal: {row[0]}"}), 409

    cur.execute("UPDATE pedidos_b2b SET estado = 'cancelado' WHERE id = ?", (pid,))
    conn.commit()
    audit_log(cur, usuario=user, accion="CANCELAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              antes={"estado": row[0]}, despues={"estado": "cancelado"})
    return jsonify({"ok": True, "id": pid, "estado": "cancelado"})


# ─── Consolidador de necesidades ───────────────────────────────────────────

@bp.route("/api/plan/necesidades", methods=["GET"])
def plan_necesidades():
    """Agregador de necesidades por cliente · core del Plan v3.

    Devuelve estructura:
        clientes: [
            {cliente_id, cliente_nombre, tipo, productos: [...] | pedidos: [...]}
        ]

    Animus DTC (tipo='shopify_auto'): cards por producto activo con semáforo
        4 zonas: CRITICO (≤20d) · URGENTE (21-25d) · VIGILAR (26-45d) · OK (>45d)
    B2B (tipo='b2b_manual'): pedidos pendientes/confirmados agrupados.

    Query params:
        cobertura_dias_minimo: default 20 · umbral CRITICO
        cobertura_dias_alerta: default 25 · umbral URGENTE
        cobertura_dias_vigilar: default 45 · umbral VIGILAR
        ventana_ventas: default 60 · días Shopify para velocidad
    """
    err = _require_login()
    if err:
        return err

    try:
        cob_critico = max(7, int(request.args.get("cobertura_dias_minimo", 20)))
        cob_alerta = max(cob_critico + 1, int(request.args.get("cobertura_dias_alerta", 25)))
        cob_vigilar = max(cob_alerta + 1, int(request.args.get("cobertura_dias_vigilar", 45)))
        ventana = max(30, min(180, int(request.args.get("ventana_ventas", 60))))
    except Exception:
        cob_critico, cob_alerta, cob_vigilar, ventana = 20, 25, 45, 60

    conn = get_db()
    c = conn.cursor()

    # ─── Cliente 1: Animus DTC (Shopify auto) ─────────────────────────────
    # Re-usamos la lógica existente del endpoint animus-prioridad-agotamiento
    # pero ajustando umbrales a la lógica de Sebastián (20-25-45d).
    productos_animus = _calcular_animus_dtc(c, ventana, cob_critico, cob_alerta, cob_vigilar)

    # ─── Cliente 2+: B2B (Fernando + futuros) ─────────────────────────────
    pedidos_b2b = c.execute(
        """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                  cantidad_uds, ml_unidad, fecha_estimada, estado, notas
           FROM pedidos_b2b
           WHERE estado NOT IN ('despachado','cancelado')
           ORDER BY cliente_nombre ASC, fecha_estimada ASC""",
    ).fetchall()

    # Agrupar por cliente
    b2b_por_cliente = {}
    for r in pedidos_b2b:
        cid = r[1]
        if cid not in b2b_por_cliente:
            b2b_por_cliente[cid] = {
                "cliente_id": cid,
                "cliente_nombre": r[2],
                "tipo": "b2b_manual",
                "pedidos": [],
                "kg_total": 0,
            }
        kg = round((r[4] * r[5]) / 1000.0, 2)
        b2b_por_cliente[cid]["pedidos"].append({
            "id": r[0],
            "producto_nombre": r[3],
            "cantidad_uds": r[4],
            "ml_unidad": r[5],
            "kg_equivalente": kg,
            "fecha_estimada": r[6],
            "estado": r[7],
            "notas": r[8] or "",
        })
        b2b_por_cliente[cid]["kg_total"] += kg

    clientes = [{
        "cliente_id": "ANIMUS_DTC",
        "cliente_nombre": "Animus Lab DTC",
        "tipo": "shopify_auto",
        "productos": productos_animus,
    }] + list(b2b_por_cliente.values())

    # Resumen consolidado
    resumen = {
        "n_critico": sum(1 for p in productos_animus if p["urgencia"] == "CRITICO"),
        "n_urgente": sum(1 for p in productos_animus if p["urgencia"] == "URGENTE"),
        "n_vigilar": sum(1 for p in productos_animus if p["urgencia"] == "VIGILAR"),
        "n_ok": sum(1 for p in productos_animus if p["urgencia"] == "OK"),
        "n_sin_ventas": sum(1 for p in productos_animus if p["urgencia"] == "SIN_VENTAS"),
        "n_clientes_b2b": len(b2b_por_cliente),
        "n_pedidos_b2b_pendientes": sum(len(c["pedidos"]) for c in b2b_por_cliente.values()),
        "kg_total_b2b_pendientes": round(sum(c["kg_total"] for c in b2b_por_cliente.values()), 2),
    }

    return jsonify({
        "clientes": clientes,
        "resumen": resumen,
        "parametros": {
            "cobertura_dias_minimo": cob_critico,
            "cobertura_dias_alerta": cob_alerta,
            "cobertura_dias_vigilar": cob_vigilar,
            "ventana_ventas": ventana,
        },
    })


# ml por presentación · Sebastián 13-may-2026 ·
# "los sueros son de 30, los limpiadores de 150, geles e hidratantes de 50 ml"
# Si el producto contiene varios términos, gana el más específico (orden).
_ML_PRESENTACION_RULES = [
    # (substring case-insensitive, ml) · orden importa
    ("CONTORNO",          15),    # contornos de ojos chiquitos
    ("LIMPIADOR",         150),   # limpiadores faciales
    ("EMULSION LIMPIA",   150),   # emulsión limpiadora
    ("CREMA CORPORAL",    150),   # cuerpo
    ("CREMA DE UREA",     150),
    ("MASCARILLA",        100),
    ("GEL HIDRATANTE",    50),
    ("EMULSION HIDRATANTE", 50),
    ("ESENCIA",           100),   # esencias 100-200ml típico
    ("BLUSH BALM",        10),
    ("MAXLASH",           10),
    ("BOOSTER TENSOR",    30),
    ("HYDRAPEPTIDE",      30),
    ("LIP SERUM",         7),
    ("LIP SÉRUM",         7),
    ("HYDRA BALANCE",     50),
    ("HYDRA-BALANCE",     50),
    ("AZ HIBRID",         30),
    ("SUERO",             30),    # último · cualquier suero por defecto 30
]


def _inferir_ml_presentacion(producto_nombre):
    """Devuelve ml de la presentación principal del producto.

    Reglas explícitas por tipo · ver _ML_PRESENTACION_RULES.
    Default 30ml si no matchea (asume suero estándar).
    """
    if not producto_nombre:
        return 30.0
    upper = producto_nombre.upper()
    for sub, ml in _ML_PRESENTACION_RULES:
        if sub in upper:
            return float(ml)
    return 30.0


def _calcular_animus_dtc(c, ventana, cob_critico, cob_alerta, cob_vigilar):
    """Calcula necesidades Animus DTC con lógica semáforo Sebastián.

    Para cada producto ACTIVO con codigo_pt seedeado, agrega:
      - Stock actual (góndola) + pipeline 7d
      - Velocidad ventas 30ml + 10ml
      - Días de cobertura
      - Urgencia según umbrales (20/25/45)
      - kg recomendados producir = 1 lote bulk si urgencia ≠ OK
    """
    from datetime import date as _date, timedelta as _td
    import json as _json

    hoy = _hoy_colombia()
    ventana_desde = (hoy - _td(days=ventana)).isoformat()
    pipeline_desde = (hoy - _td(days=7)).isoformat()

    # 1. TODOS los productos activos · Sebastián 13-may-2026:
    # "necesito que aparezcan todos y en orden de necesidades"
    # · removí el filtro `codigo_pt IS NOT NULL` que ocultaba 22 productos.
    # · codigo_pt fallback: primeras 4 letras de producto_nombre upper si está vacío.
    productos = c.execute(
        """SELECT producto_nombre,
                  COALESCE(NULLIF(TRIM(codigo_pt),''),
                           UPPER(SUBSTR(REPLACE(REPLACE(producto_nombre,' ',''),'.',''),1,4)))
                       AS codigo,
                  COALESCE(lote_size_kg, 0),
                  COALESCE(tiene_10ml,0), COALESCE(uds_10ml_por_lote,0),
                  COALESCE(tipo_10ml,''),
                  COALESCE(imagen_url,'')
           FROM formula_headers
           WHERE COALESCE(activo,1) = 1
           ORDER BY producto_nombre""",
    ).fetchall()

    if not productos:
        return []

    # 2. Mapeo producto → sku_principal (para Shopify)
    # Estructura sku_producto_map: sku → producto_nombre
    sku_to_prod = {}
    prod_to_skus = {}  # inverso · diagnóstico: ¿qué SKUs mapean a cada producto?
    for r in c.execute(
        """SELECT sku, producto_nombre FROM sku_producto_map
           WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
             AND TRIM(producto_nombre) != ''""",
    ).fetchall():
        sku_up = r[0].upper()
        sku_to_prod[sku_up] = r[1]
        prod_to_skus.setdefault(r[1], []).append(sku_up)

    # 3. Stock por SKU (re-uso helper)
    from blueprints.programacion import _resolved_stock_por_sku
    resolved_stock = _resolved_stock_por_sku(c.connection, empresa='ANIMUS')
    # resolved_stock: {sku_upper: {descripcion, uds, fuente}}

    # 4. Ventas por SKU últimos N días
    ventas_por_sku = {}
    for r in c.execute(
        """SELECT sku_items FROM animus_shopify_orders
           WHERE date(creado_en) >= ?
             AND sku_items IS NOT NULL AND sku_items != ''""",
        (ventana_desde,),
    ).fetchall():
        try:
            items = _json.loads(r[0]) if r[0] else []
        except Exception:
            continue
        for it in items:
            sku = str(it.get("sku", "") or "").strip().upper()
            qty = int(it.get("qty", 0) or 0)
            if sku and qty > 0:
                ventas_por_sku[sku] = ventas_por_sku.get(sku, 0) + qty

    # 5. Pipeline 7d (lotes recién fabricados que aún no aparecen en Available)
    # Suma kg de produccion_programada con fin_real_at >= hoy-7d agrupado por producto
    pipeline_kg_por_prod = {}
    for r in c.execute(
        """SELECT producto, COALESCE(SUM(COALESCE(kg_real, cantidad_kg, 0)), 0)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= ?
             AND date(fin_real_at) <= date('now', '-5 hours')
           GROUP BY producto""",
        (pipeline_desde,),
    ).fetchall():
        if r[0]:
            pipeline_kg_por_prod[r[0]] = float(r[1] or 0)

    # 6. Procesar cada producto
    out = []
    for prod_nombre, codigo, lote_kg, tiene_10ml, uds_10ml, tipo_10ml, imagen in productos:
        # SKUs de este producto (puede haber varios: 30ml, 10ml, etc)
        skus_de_prod = [sku for sku, p in sku_to_prod.items() if p == prod_nombre]

        # Stock total uds + venta 30d agregada
        stock_uds_total = 0
        ventas_periodo_total = 0
        for sku in skus_de_prod:
            stk = resolved_stock.get(sku, {})
            stock_uds_total += int(stk.get("uds", 0) or 0)
            ventas_periodo_total += int(ventas_por_sku.get(sku, 0) or 0)

        # ml por presentación · Sebastián 13-may-2026: "los sueros son
        # de 30, los limpiadores de 150, geles e hidratantes de 50 ml".
        # Antes era hardcoded 30 para todo → bug que subestimaba stock_kg
        # y velocidad_kg para limpiadores y geles.
        ml_promedio = _inferir_ml_presentacion(prod_nombre)
        # Velocidad uds/día y kg/día
        velocidad_uds_dia = ventas_periodo_total / float(ventana)
        velocidad_kg_dia = (velocidad_uds_dia * ml_promedio) / 1000.0
        # Stock kg = uds × ml / 1000 + pipeline
        stock_kg_gondola = (stock_uds_total * ml_promedio) / 1000.0
        pipeline_kg = pipeline_kg_por_prod.get(prod_nombre, 0.0)
        stock_kg_total = stock_kg_gondola + pipeline_kg

        # Días de cobertura
        if velocidad_kg_dia > 0:
            dias_cobertura = round(stock_kg_total / velocidad_kg_dia, 1)
        else:
            dias_cobertura = None

        # Urgencia (lógica Sebastián 20-25-45)
        if velocidad_uds_dia <= 0.01:
            urgencia = "SIN_VENTAS"
        elif dias_cobertura is None:
            urgencia = "SIN_VENTAS"
        elif dias_cobertura <= cob_critico:
            urgencia = "CRITICO"
        elif dias_cobertura <= cob_alerta:
            urgencia = "URGENTE"
        elif dias_cobertura <= cob_vigilar:
            urgencia = "VIGILAR"
        else:
            urgencia = "OK"

        # Recomendación: 1 lote completo si urgencia en {CRITICO, URGENTE}
        # Para VIGILAR mostramos "próximo lote en X días" sin urgir
        if urgencia in ("CRITICO", "URGENTE"):
            n_lotes_recomendados = 1
            kg_a_producir = float(lote_kg)
        else:
            n_lotes_recomendados = 0
            kg_a_producir = 0.0

        # Sumar regalos 10ml si aplica (info para UI)
        regalos_extra_uds = 0
        if tiene_10ml == 1 and tipo_10ml == "regalo" and n_lotes_recomendados > 0:
            regalos_extra_uds = int(uds_10ml or 0) * n_lotes_recomendados

        out.append({
            "codigo_pt": codigo,
            "producto_nombre": prod_nombre,
            "imagen_url": imagen,
            "lote_bulk_kg": float(lote_kg or 0),
            "tiene_10ml": int(tiene_10ml or 0),
            "uds_10ml_por_lote": int(uds_10ml or 0),
            "tipo_10ml": tipo_10ml or "",
            "stock_uds_total": stock_uds_total,
            "stock_kg_gondola": round(stock_kg_gondola, 2),
            "pipeline_kg": round(pipeline_kg, 2),
            "stock_kg_total": round(stock_kg_total, 2),
            "ventas_periodo_uds": ventas_periodo_total,
            "velocidad_uds_dia": round(velocidad_uds_dia, 2),
            "velocidad_kg_dia": round(velocidad_kg_dia, 3),
            "ml_unidad": ml_promedio,
            "dias_cobertura": dias_cobertura,
            "urgencia": urgencia,
            "n_lotes_recomendados": n_lotes_recomendados,
            "kg_a_producir": kg_a_producir,
            "regalos_extra_uds": regalos_extra_uds,
        })

    # 6b. Match MPs por producto · Sebastián 13-may-2026:
    # "match de materias primas que diga si se puede hacer o no".
    # Para cada producto activo, leer su formula_items + stock MP actual ·
    # calcular faltantes para 1 lote bulk_kg.
    formula_por_prod = {}  # producto → [{material_id, nombre, necesario_g}]
    for r in c.execute(
        """SELECT fi.producto_nombre, fi.material_id,
                  COALESCE(fi.material_nombre, '') AS mat_nom,
                  COALESCE(fi.cantidad_g_por_lote, 0) AS cant_g,
                  COALESCE(fi.porcentaje, 0) AS pct,
                  COALESCE(fh.lote_size_kg, 0) AS lote_kg
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo, 1) = 1
             AND fi.material_id IS NOT NULL
             AND TRIM(fi.material_id) != ''""",
    ).fetchall():
        prod, mid, mnom, cant_g, pct, lote_kg = r
        nec_g = float(cant_g or 0)
        if nec_g <= 0 and pct > 0 and lote_kg > 0:
            nec_g = (float(pct) / 100.0) * float(lote_kg) * 1000.0
        if nec_g <= 0:
            continue
        formula_por_prod.setdefault(prod, []).append({
            "material_id": mid,
            "material_nombre": mnom[:50],
            "necesario_g": round(nec_g, 2),
        })

    # Stock MP por material_id · SUM(movimientos)
    mp_stock_g = {}
    for r in c.execute(
        """SELECT material_id,
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
                                    THEN cantidad ELSE -cantidad END), 0)
           FROM movimientos
           WHERE material_id IS NOT NULL AND TRIM(material_id) != ''
           GROUP BY material_id""",
    ).fetchall():
        mp_stock_g[str(r[0]).strip()] = max(float(r[1] or 0), 0)

    # 7. Lotes pendientes/en curso por producto (ya agendados)
    # Sebastián 13-may-2026: todo vive en EOS · sin Calendar. Cualquier lote
    # con estado pendiente/en_curso y sin fin_real_at cuenta como "en vuelo".
    lotes_pendientes = {}
    for r in c.execute(
        """SELECT producto,
                  COUNT(*) AS n,
                  COALESCE(SUM(cantidad_kg), 0) AS kg,
                  GROUP_CONCAT(fecha_programada, ',') AS fechas
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now', '-5 hours', '-7 day')
           GROUP BY producto""",
    ).fetchall():
        fechas = sorted(set([f.strip() for f in (r[3] or "").split(",") if f.strip()]))
        lotes_pendientes[r[0]] = {
            "n": r[1],
            "kg_total": round(float(r[2] or 0), 2),
            "proximas_fechas": fechas[:3],
        }

    # 8. Última producción COMPLETADA por producto (para el horizonte)
    # Sebastián 13-may-2026: "ya producido + que diga si se hizo tal día
    # y tanto alcanzará para tantos días + próxima sugerida".
    ultima_prod = {}
    for r in c.execute(
        """SELECT producto, MAX(fecha_programada) AS f
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND COALESCE(kg_real, cantidad_kg, 0) > 0
           GROUP BY producto""",
    ).fetchall():
        ultima_prod[r[0]] = {"fecha": r[1]}
    # Obtener kg de esa última (separadamente para evitar GROUP BY con MAX(fecha)
    # pero kg de otra fila)
    for prod, info in ultima_prod.items():
        row = c.execute(
            """SELECT COALESCE(kg_real, cantidad_kg, 0)
               FROM produccion_programada
               WHERE producto = ?
                 AND fin_real_at IS NOT NULL
                 AND fecha_programada = ?
               ORDER BY id DESC LIMIT 1""",
            (prod, info["fecha"]),
        ).fetchone()
        info["kg"] = round(float(row[0] or 0), 2) if row else 0.0

    # Inyectar lotes pendientes + horizonte en cada producto
    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()
    for p in out:
        info = lotes_pendientes.get(p["producto_nombre"])
        if info:
            p["lotes_pendientes_n"] = info["n"]
            p["lotes_pendientes_kg"] = info["kg_total"]
            p["lotes_pendientes_proximas_fechas"] = info["proximas_fechas"]
        else:
            p["lotes_pendientes_n"] = 0
            p["lotes_pendientes_kg"] = 0.0
            p["lotes_pendientes_proximas_fechas"] = []

        # Horizonte: última producción completada + cálculo próxima sugerida
        up = ultima_prod.get(p["producto_nombre"])
        if up and up["fecha"]:
            p["ultima_produccion_fecha"] = up["fecha"]
            p["ultima_produccion_kg"] = up["kg"]
            try:
                f = _date.fromisoformat(up["fecha"][:10])
                p["dias_desde_ultima"] = (hoy - f).days
            except Exception:
                p["dias_desde_ultima"] = None
            # Duración estimada del lote producido (kg / velocidad_kg_día)
            if p["velocidad_kg_dia"] > 0 and up["kg"] > 0:
                dur_dias = int(up["kg"] / p["velocidad_kg_dia"])
                p["duracion_lote_dias"] = dur_dias
                try:
                    f_ini = _date.fromisoformat(up["fecha"][:10])
                    # Próxima sugerida = última + duración - buffer 25d
                    proxima = f_ini + _td(days=max(1, dur_dias - cob_alerta))
                    p["proxima_sugerida_fecha"] = proxima.isoformat()
                    p["proxima_sugerida_dias"] = (proxima - hoy).days
                except Exception:
                    p["proxima_sugerida_fecha"] = None
                    p["proxima_sugerida_dias"] = None
            else:
                p["duracion_lote_dias"] = None
                p["proxima_sugerida_fecha"] = None
                p["proxima_sugerida_dias"] = None
        else:
            p["ultima_produccion_fecha"] = None
            p["ultima_produccion_kg"] = 0.0
            p["dias_desde_ultima"] = None
            p["duracion_lote_dias"] = None
            p["proxima_sugerida_fecha"] = None
            p["proxima_sugerida_dias"] = None

        # Diagnostic SKUs · ¿este producto tiene mapeo Shopify?
        skus_de_este = prod_to_skus.get(prod_nombre, [])
        p["skus_mapeados"] = skus_de_este
        p["n_skus_mapeados"] = len(skus_de_este)
        p["sin_mapeo_shopify"] = (len(skus_de_este) == 0)

        # Match MPs · ¿se puede fabricar 1 lote bulk con stock actual?
        # Sebastián 13-may-2026: "match de materias primas que diga si se
        # puede hacer o no".
        items_form = formula_por_prod.get(p["producto_nombre"], [])
        if not items_form:
            p["mps_status"] = "SIN_FORMULA"
            p["mps_faltantes"] = []
            p["mps_total_items"] = 0
            p["mps_n_faltantes"] = 0
            p["puede_fabricar"] = False
        else:
            faltantes = []
            for it in items_form:
                disponible_g = mp_stock_g.get(str(it["material_id"]).strip(), 0.0)
                falta = it["necesario_g"] - disponible_g
                if falta > 0.01:  # tolerancia gramos
                    faltantes.append({
                        "material_id": it["material_id"],
                        "material_nombre": it["material_nombre"],
                        "necesario_g": it["necesario_g"],
                        "disponible_g": round(disponible_g, 2),
                        "faltante_g": round(falta, 2),
                    })
            p["mps_total_items"] = len(items_form)
            p["mps_n_faltantes"] = len(faltantes)
            p["mps_faltantes"] = faltantes
            p["mps_status"] = "OK" if not faltantes else "FALTAN_MPS"
            p["puede_fabricar"] = len(faltantes) == 0

        # Escenarios inteligentes 30/60/90 días · Sebastián 13-may-2026:
        # "sugiero para 30 días tantos kilos, para 60 tantos, etc · elijo
        # y se agenda con un click". Cada escenario propone kg + fecha.
        # Fecha sugerida = max(hoy + 3d, cobertura - buffer 7d) para que
        # haya tiempo de planear sin agotamiento.
        vel_kg_dia = p["velocidad_kg_dia"] or 0
        escenarios = []
        if vel_kg_dia > 0:
            # Buffer: producir antes de que cobertura llegue a 0 (de hecho
            # antes del buffer 25d ideal del usuario). Aproximamos con
            # max(hoy + 3d, fecha_proxima_critica).
            dias_hasta_critico = (
                (p["dias_cobertura"] or 0) - cob_critico
                if p["dias_cobertura"] is not None else 0
            )
            from datetime import date as _date2, timedelta as _td2
            hoy2 = _date2.today()
            fecha_base = hoy2 + _td2(days=max(3, dias_hasta_critico))
            for d in (30, 60, 90):
                kg_d = round(vel_kg_dia * d, 1)
                # No bajar de 0.5kg ni superar 5× lote bulk (sanity)
                if kg_d < 0.5:
                    continue
                escenarios.append({
                    "dias_objetivo": d,
                    "kg_sugerido": kg_d,
                    "fecha_sugerida": fecha_base.isoformat(),
                    "etiqueta": f"Cubrir {d} días",
                    "recomendado": d == 90 and kg_d <= p["lote_bulk_kg"] * 1.2,
                })
            # Si el lote_bulk_kg no coincide con ninguno, agregar como opción
            if p["lote_bulk_kg"] > 0 and not any(
                abs(e["kg_sugerido"] - p["lote_bulk_kg"]) < 0.5 for e in escenarios
            ):
                lote_dias = int(p["lote_bulk_kg"] / vel_kg_dia)
                escenarios.append({
                    "dias_objetivo": lote_dias,
                    "kg_sugerido": p["lote_bulk_kg"],
                    "fecha_sugerida": fecha_base.isoformat(),
                    "etiqueta": f"Lote bulk completo (~{lote_dias} días)",
                    "recomendado": True,
                })
        p["escenarios"] = escenarios

    # Inyectar producciones agendadas activas por producto · Sebastián
    # 13-may-2026: "lo que hemos construido en plan en curso deberia
    # estar en necesidades pues alli puesto, para saber justo si ya
    # esta programado daria una vision mas sana".
    # Cada producto gana: planificacion[] con todas las producciones
    # programado / esperando_recurso / pendiente · ordenadas por fecha
    plan_por_producto = {}
    for r in c.execute(
        """SELECT pp.producto, pp.id, pp.fecha_programada, pp.estado,
                  pp.origen, COALESCE(pp.cantidad_kg, 0),
                  pp.motivo_pausa, pp.pausado_at, pp.observaciones
           FROM produccion_programada pp
           WHERE pp.estado IN ('pendiente','programado','en_curso','esperando_recurso')
             AND pp.fin_real_at IS NULL
           ORDER BY pp.fecha_programada ASC""",
    ).fetchall():
        prod_nombre = (r[0] or "").strip()
        if not prod_nombre:
            continue
        plan_por_producto.setdefault(prod_nombre, []).append({
            "id": int(r[1]),
            "fecha": (r[2] or "")[:10],
            "estado": r[3],
            "origen": r[4],
            "kg": float(r[5] or 0),
            "motivo_pausa": r[6],
            "pausado_at": r[7],
            "obs_preview": (r[8] or "")[:80],
        })

    for p in out:
        prod = p["producto_nombre"]
        agendados = plan_por_producto.get(prod, [])
        p["planificacion"] = agendados
        proximo = next((a for a in agendados if a["estado"] != 'esperando_recurso'), None)
        p["proximo_lote"] = proximo
        pausados = [a for a in agendados if a["estado"] == 'esperando_recurso']
        p["lotes_pausados"] = pausados
        p["tiene_pausa"] = len(pausados) > 0
        p["tiene_plan_activo"] = proximo is not None

        # Detectar duplicados · Sebastián 14-may-2026: "veo mucha cosa
        # repetida como producción esta semana y se repite la próxima, de
        # donde está tomando ese calendario". Causa típica: mig de
        # Calendar + Plan EOS crearon lotes del mismo producto con fechas
        # cercanas (< 21 días = considerado duplicado).
        # Agrupa pares (a, b) donde |fecha_a - fecha_b| < 21 días.
        from datetime import date as _date2
        duplicados_grupos = []
        for i, la in enumerate(agendados):
            for lb in agendados[i + 1:]:
                try:
                    fa = _date2.fromisoformat(la["fecha"][:10])
                    fb = _date2.fromisoformat(lb["fecha"][:10])
                    delta = abs((fa - fb).days)
                    if delta < 21:
                        duplicados_grupos.append({
                            "id_a": la["id"], "fecha_a": la["fecha"],
                            "origen_a": la["origen"], "kg_a": la["kg"],
                            "id_b": lb["id"], "fecha_b": lb["fecha"],
                            "origen_b": lb["origen"], "kg_b": lb["kg"],
                            "delta_dias": delta,
                        })
                except Exception:
                    pass
        p["duplicados_detectados"] = duplicados_grupos
        p["n_duplicados"] = len(duplicados_grupos)

        # Trazabilidad · Sebastián 13-may-2026: "trazabilidad del
        # calendario para saber ya esta programado o no, esa programación
        # alcanza o no alcanza, tambien ver materias primas alcanzan o no".
        vel_kd = p["velocidad_kg_dia"] or 0
        # 1. ¿La programación próxima ALCANZA? · suma kg de lotes
        #    programados/pausados activos + stock_efectivo / velocidad
        kg_plan_activo = sum(float(a["kg"] or 0) for a in agendados)
        cob_post_plan = None
        if vel_kd > 0.001:
            cob_post_plan = round((p["stock_kg_total"] + kg_plan_activo) / vel_kd, 1)
        p["cob_post_plan_dias"] = cob_post_plan
        # alcanza_sí si cob_post_plan >= cob_alerta+horizonte mínimo (45d)
        if proximo is None:
            p["plan_alcanza"] = None        # no hay plan que medir
        elif cob_post_plan is None:
            p["plan_alcanza"] = None
        elif cob_post_plan >= cob_vigilar:
            p["plan_alcanza"] = "SI"
        elif cob_post_plan >= cob_alerta:
            p["plan_alcanza"] = "AJUSTADO"
        else:
            p["plan_alcanza"] = "NO"

        # 2. ¿MPs alcanzan para producir el próximo lote?
        # Se basa en p['mps_status'] que ya viene del check upstream:
        #   OK = todas MPs disponibles · FALTAN_MPS = no · SIN_FORMULA = ?
        # Mapeo a etiquetas simples para UI:
        if p.get("mps_status") == "OK":
            p["mps_alcanza"] = "SI"
        elif p.get("mps_status") == "FALTAN_MPS":
            p["mps_alcanza"] = "NO"
        else:
            p["mps_alcanza"] = "DESCONOCIDO"

    # Ordenar por urgencia + días cobertura ascendente
    ORDEN = {"CRITICO": 0, "URGENTE": 1, "VIGILAR": 2, "OK": 3, "SIN_VENTAS": 4}
    out.sort(key=lambda x: (
        ORDEN.get(x["urgencia"], 9),
        x["dias_cobertura"] if x["dias_cobertura"] is not None else 99999,
    ))
    return out


# ─── Programar producción · todo vive en EOS · sin Calendar ───────────────

@bp.route("/api/plan/programar-produccion", methods=["POST"])
def programar_produccion():
    """Crea entrada en produccion_programada con origen='eos_plan'.

    Sebastián 13-may-2026: decisión arquitectónica · todo vive en EOS,
    Calendar deja de ser source of truth. Esta es la API que reemplaza
    el flujo manual de "agendar evento en Calendar" para programar producción.

    Body:
        producto_nombre: str (FK formula_headers)
        fecha_programada: str YYYY-MM-DD
        cantidad_kg: float > 0
        area_id: int opcional (FK areas_planta)
        notas: str opcional

    Response:
        201 {ok, id, producto, fecha, cantidad_kg}
        400 / 404 errores

    Permiso: admin o compras (mismo que pedidos B2B).
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    fecha = (body.get("fecha_programada") or "").strip()
    try:
        kg = float(body.get("cantidad_kg") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_kg inválida"}), 400
    try:
        area_id = int(body.get("area_id")) if body.get("area_id") else None
    except (ValueError, TypeError):
        return jsonify({"error": "area_id inválido"}), 400
    notas = (body.get("notas") or "").strip()

    # Validaciones
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    if not fecha or not _valida_fecha_iso(fecha):
        return jsonify({"error": "fecha_programada formato YYYY-MM-DD requerido"}), 400
    if kg <= 0:
        return jsonify({"error": "cantidad_kg debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Producto debe existir
    if not cur.execute(
        "SELECT 1 FROM formula_headers WHERE producto_nombre = ?", (producto,),
    ).fetchone():
        return jsonify({"error": f"producto '{producto}' no existe"}), 404

    # Si area_id provisto, validar
    if area_id is not None:
        if not cur.execute(
            "SELECT 1 FROM areas_planta WHERE id = ? AND activo = 1",
            (area_id,),
        ).fetchone():
            return jsonify({"error": f"area_id {area_id} no existe o inactiva"}), 404

    # Insertar con origen='eos_plan' (identifica origen post-Calendar)
    cur.execute(
        """INSERT INTO produccion_programada
             (producto, fecha_programada, cantidad_kg, lotes, estado,
              origen, observaciones, area_id, creado_en)
           VALUES (?, ?, ?, 1, 'pendiente', 'eos_plan', ?, ?, datetime('now', '-5 hours'))""",
        (producto, fecha, kg, notas, area_id),
    )
    pid = cur.lastrowid
    audit_log(cur, usuario=user, accion="PROGRAMAR_PRODUCCION",
              tabla="produccion_programada", registro_id=pid,
              despues={"producto": producto, "fecha": fecha,
                       "cantidad_kg": kg, "area_id": area_id,
                       "origen": "eos_plan", "notas": notas})
    conn.commit()
    return jsonify({
        "ok": True, "id": pid,
        "producto": producto, "fecha": fecha,
        "cantidad_kg": kg, "estado": "pendiente",
    }), 201


@bp.route("/admin/verificar-codigos-mp", methods=["GET"])
def verificar_codigos_mp_page():
    """Página admin · verifica los 146 códigos del Excel Alejandro
    contra maestro_mps en vivo."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/verificar-codigos-mp")
    from flask import Response
    return Response(_VERIFICAR_CODIGOS_HTML, mimetype="text/html")


_VERIFICAR_CODIGOS_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Verificar códigos MP del Excel · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1100px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:13px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
button:hover{opacity:.9}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;text-align:center;min-width:140px}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:24px;font-weight:800}
.ok{color:#16a34a}
.warn{color:#ea580c}
.crit{color:#dc2626}
.bad{color:#94a3b8}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:7px 8px;border-bottom:1px solid #f1f5f9}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;color:#1e40af}
a{color:#0f766e}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver al panel</a>
<div class="card">
  <h1>🔍 Verificar códigos MP del Excel</h1>
  <div class="muted">146 códigos del Excel <strong>FORMULAS_MAESTRO_v2_1 (2).xlsx</strong> de Alejandro mayo-2026 vs <code>maestro_mps</code> en BD.</div>
  <div style="margin-top:16px"><button onclick="verificar()">▶ Verificar 146 códigos contra BD</button></div>
  <div id="kpis" style="margin-top:16px"></div>
</div>
<div id="resultados"></div>
</div>
<script>
var CODES_EXCEL = __CODES_EXCEL__;

function csrf() {
  var m = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  return m ? decodeURIComponent(m[1]) : '';
}

async function verificar() {
  document.getElementById('resultados').innerHTML = '<div class="card">Verificando…</div>';
  try {
    // GET · read-only · sin body · sin CSRF · saltea bloqueo MFA admin
    var r = await fetch('/api/plan/check-codigos-mp');
    var raw = await r.text();
    var d;
    try { d = JSON.parse(raw); } catch(je) {
      document.getElementById('resultados').innerHTML = '<div class="card crit"><h3>Response no JSON · HTTP ' + r.status + '</h3><pre>' + escapeHtml(raw.substring(0, 500)) + '</pre></div>';
      return;
    }
    if (!r.ok) {
      document.getElementById('resultados').innerHTML = '<div class="card crit"><h3>Error HTTP ' + r.status + '</h3><pre>' + escapeHtml(JSON.stringify(d, null, 2)) + '</pre></div>';
      return;
    }
    render(d);
  } catch(e) {
    document.getElementById('resultados').innerHTML = '<div class="card crit"><h3>Error de red</h3><pre>' + escapeHtml(e.message) + '</pre></div>';
  }
}

function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function render(d) {
  var html = '';
  html += '<span class="kpi"><div class="kpi-lbl">Total Excel</div><div class="kpi-val">' + d.total_excel + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">✅ Match OK</div><div class="kpi-val ok">' + d.total_existentes_ok + '</div></span>';
  if (d.total_mismatches > 0) html += '<span class="kpi"><div class="kpi-lbl">🟠 Mismatches</div><div class="kpi-val warn">' + d.total_mismatches + '</div></span>';
  if (d.total_existentes_sin_info_bd > 0) html += '<span class="kpi"><div class="kpi-lbl">❓ Sin info BD</div><div class="kpi-val warn">' + d.total_existentes_sin_info_bd + '</div></span>';
  if (d.total_inactivos > 0) html += '<span class="kpi"><div class="kpi-lbl">⚠ Inactivos</div><div class="kpi-val warn">' + d.total_inactivos + '</div></span>';
  if (d.total_faltantes > 0) html += '<span class="kpi"><div class="kpi-lbl">🔴 Faltan</div><div class="kpi-val crit">' + d.total_faltantes + '</div></span>';
  document.getElementById('kpis').innerHTML = html;

  var out = '';

  // 🔴 Mismatches · CRÍTICO · el código existe pero el nombre BD ≠ Excel
  if (d.total_mismatches > 0) {
    out += '<div class="card" style="border:2px solid #dc2626"><h3 style="margin:0 0 8px;color:#dc2626">🟠 MISMATCHES · ' + d.total_mismatches + ' códigos con nombre BD distinto al Excel</h3>';
    out += '<div class="muted" style="margin-bottom:10px">El código existe pero la MP en BD parece ser DISTINTA a la del Excel. Importar fórmulas con estos códigos crearía formulas que referencian MPs equivocadas. Revisar uno a uno antes de proceder.</div>';
    out += '<table><thead><tr><th>Código</th><th>Excel · INCI</th><th>Excel · Comercial</th><th>BD · INCI</th><th>BD · Comercial</th></tr></thead><tbody>';
    d.mismatches.forEach(m => {
      var exInci = (m.info_excel && m.info_excel.inci) || '<span class="bad">—</span>';
      var exCom = (m.info_excel && m.info_excel.comercial) || '<span class="bad">—</span>';
      out += '<tr><td class="mono">' + escapeHtml(m.codigo) + '</td><td>' + escapeHtml(exInci) + '</td><td>' + escapeHtml(exCom) + '</td><td style="background:#fff7ed">' + escapeHtml(m.nombre_inci_bd || '—') + '</td><td style="background:#fff7ed">' + escapeHtml(m.nombre_comercial_bd || '—') + '</td></tr>';
    });
    out += '</tbody></table></div>';
  }

  if (d.total_existentes_sin_info_bd > 0) {
    out += '<details class="card"><summary style="cursor:pointer;color:#ea580c;font-weight:700">❓ Sin info BD (' + d.total_existentes_sin_info_bd + ') · click para revisar · BD vacío</summary>';
    out += '<div class="muted" style="margin:10px 0">Existen en maestro_mps pero nombre_inci y nombre_comercial están vacíos en BD. No se pudo comparar contra Excel. Recomendado: llenar los nombres en BD desde el Excel.</div>';
    out += '<table><thead><tr><th>Código</th><th>Excel · INCI</th><th>Excel · Comercial</th></tr></thead><tbody>';
    d.existentes_sin_info_bd.forEach(e => {
      var exInci = (e.info_excel && e.info_excel.inci) || '—';
      var exCom = (e.info_excel && e.info_excel.comercial) || '—';
      out += '<tr><td class="mono">' + escapeHtml(e.codigo) + '</td><td>' + escapeHtml(exInci) + '</td><td>' + escapeHtml(exCom) + '</td></tr>';
    });
    out += '</tbody></table></details>';
  }

  if (d.total_faltantes > 0) {
    out += '<div class="card"><h3 style="margin:0 0 8px;color:#dc2626">🔴 FALTANTES · ' + d.total_faltantes + ' MPs no existen en BD</h3>';
    out += '<table><thead><tr><th>Código</th><th>Nombre INCI (Excel)</th><th>Nombre Comercial (Excel)</th></tr></thead><tbody>';
    d.faltantes.forEach(f => {
      var inci = (f.info_excel && f.info_excel.inci) || '<span class="bad">—</span>';
      var com = (f.info_excel && f.info_excel.comercial) || '<span class="bad">—</span>';
      out += '<tr><td class="mono">' + escapeHtml(f.codigo) + '</td><td>' + escapeHtml(inci) + '</td><td>' + escapeHtml(com) + '</td></tr>';
    });
    out += '</tbody></table></div>';
  }

  if (d.total_inactivos > 0) {
    out += '<div class="card"><h3 style="margin:0 0 8px;color:#ea580c">⚠ INACTIVOS · existen pero activo=0</h3>';
    out += '<table><thead><tr><th>Código</th><th>Nombre Comercial BD</th><th>Nombre INCI BD</th></tr></thead><tbody>';
    d.inactivos.forEach(i => {
      out += '<tr><td class="mono">' + escapeHtml(i.codigo) + '</td><td>' + escapeHtml(i.nombre_comercial_bd) + '</td><td>' + escapeHtml(i.nombre_inci_bd) + '</td></tr>';
    });
    out += '</tbody></table></div>';
  }

  // Listo si TODO OK
  var totalProblems = d.total_mismatches + d.total_existentes_sin_info_bd + d.total_inactivos + d.total_faltantes;
  if (totalProblems === 0) {
    out += '<div class="card"><h3 style="margin:0;color:#16a34a">✅ Perfecto · ' + d.total_existentes_ok + '/146 codigos OK · listos para importar fórmulas.</h3></div>';
  } else if (d.total_existentes_ok > 0) {
    out += '<details class="card"><summary style="cursor:pointer;color:#16a34a;font-weight:700">✅ Match OK (' + d.total_existentes_ok + ') · click para expandir</summary>';
    out += '<table style="margin-top:10px"><thead><tr><th>Código</th><th>Nombre Comercial BD</th><th>Nombre INCI BD</th></tr></thead><tbody>';
    d.existentes.forEach(e => {
      out += '<tr><td class="mono">' + escapeHtml(e.codigo) + '</td><td>' + escapeHtml(e.nombre_comercial_bd) + '</td><td>' + escapeHtml(e.nombre_inci_bd) + '</td></tr>';
    });
    out += '</tbody></table></details>';
  }

  document.getElementById('resultados').innerHTML = out;
}

// NO auto-verificar · click manual del botón
// (si auto-verifica y hay error, no se ve el debug claro)
</script>
</body></html>"""


# Embed CODES_EXCEL inline (lista de los 146 codigos del Excel
# FORMULAS_MAESTRO_v2_1 Alejandro mayo-2026 · si Sebastián actualiza el
# Excel, regenerar estos arrays leyendo scripts/excel_mp_codigos.json
_EXCEL_INFO = {}
try:
    import json as __json, os as __os
    __json_path = __os.path.join(
        __os.path.dirname(__os.path.dirname(__os.path.dirname(__os.path.abspath(__file__)))),
        'scripts', 'excel_mp_codigos.json',
    )
    if __os.path.exists(__json_path):
        with open(__json_path, encoding='utf-8') as __f:
            _EXCEL_INFO = __json.load(__f)
except Exception:
    _EXCEL_INFO = {}

_CODES_EXCEL_LIST = [
    "MP00005", "MP00006", "MP00008", "MP00020", "MP00021", "MP00024",
    "MP00025", "MP00030", "MP00035", "MP00040", "MP00041", "MP00043",
    "MP00045", "MP00046", "MP00047", "MP00048", "MP00049", "MP00050",
    "MP00051", "MP00052", "MP00053", "MP00054", "MP00055", "MP00056",
    "MP00062", "MP00063", "MP00064", "MP00065", "MP00068", "MP00071",
    "MP00072", "MP00073", "MP00074", "MP00075", "MP00077", "MP00078",
    "MP00079", "MP00082", "MP00083", "MP00084", "MP00090", "MP00092",
    "MP00093", "MP00101", "MP00103", "MP00105", "MP00107", "MP00110",
    "MP00111", "MP00112", "MP00116", "MP00118", "MP00120", "MP00121",
    "MP00123", "MP00127", "MP00132", "MP00134", "MP00136", "MP00137",
    "MP00138", "MP00140", "MP00142", "MP00145", "MP00147", "MP00148",
    "MP00149", "MP00150", "MP00152", "MP00160", "MP00161", "MP00163",
    "MP00166", "MP00167", "MP00169", "MP00172", "MP00173", "MP00174",
    "MP00175", "MP00176", "MP00177", "MP00178", "MP00179", "MP00180",
    "MP00181", "MP00183", "MP00184", "MP00185", "MP00186", "MP00190",
    "MP00191", "MP00192", "MP00194", "MP00195", "MP00199", "MP00201",
    "MP00202", "MP00207", "MP00209", "MP00210", "MP00212", "MP00214",
    "MP00215", "MP00216", "MP00219", "MP00221", "MP00223", "MP00226",
    "MP00228", "MP00230", "MP00231", "MP00233", "MP00234", "MP00235",
    "MP00236", "MP00237", "MP00238", "MP00239", "MP00240", "MP00242",
    "MP00244", "MP00245", "MP00246", "MP00248", "MP00250", "MP00253",
    "MP00254", "MP00256", "MP00257", "MP00259", "MP00260", "MP00261",
    "MP00262", "MP00263", "MP00264", "MP00265", "MP00266", "MP00270",
    "MP00274", "MP00275", "MP00277", "MP00282", "MP00283", "MP00285",
    "MP00287", "MP00297",
]
import json as _json
_VERIFICAR_CODIGOS_HTML = _VERIFICAR_CODIGOS_HTML.replace(
    "__CODES_EXCEL__", _json.dumps(_CODES_EXCEL_LIST))


@bp.route("/admin/comparar-calendar-necesidades", methods=["GET"])
def comparar_calendar_page():
    """Análisis read-only · Calendar vs Necesidades · diagnóstico."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/comparar-calendar-necesidades")
    from flask import Response
    return Response(_COMPARAR_CALENDAR_HTML, mimetype="text/html")


@bp.route("/api/plan/comparar-calendar-necesidades", methods=["GET"])
def comparar_calendar_necesidades():
    """Compara lotes en Google Calendar vs necesidades calculadas Shopify.

    Sebastián 13-may-2026: "primero saber si lo de calendar está bien
    para decidir si migramos a Plan".

    Para cada producto Animus activo con codigo_pt:
    - kg_calendar_horizonte: SUM(cantidad_kg) de origen='calendar'/'manual'
                              en próximos N días
    - kg_necesario_horizonte: velocidad_kg_dia × horizonte_dias
    - diff = calendar - necesario
    - categoria:
      MATCH_OK · |diff| <= 20% de necesario · cumple
      SOBRE · calendar >> necesario (>20% más) · sobra capacidad
      SUB · calendar << necesario · falta producción
      URGENTE_SIN_AGENDAR · días cobertura < 25 Y calendar=0 · CRÍTICO
      AGENDADO_SIN_URGENCIA · cobertura > 45 Y calendar > 0 · revisar
      SIN_VENTAS_SIN_AGENDAR · OK · no se mide

    Query:
        horizonte_dias: 60/90/180 (default 90)
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    try:
        horizonte = max(30, min(365, int(request.args.get("horizonte_dias", 90))))
    except Exception:
        horizonte = 90

    # Reusar lógica de necesidades pero con horizonte custom
    conn = get_db()
    c = conn.cursor()
    # Calcular necesidades con umbrales default
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)
    # Mapear producto → necesidad
    nec_por_prod = {p["producto_nombre"]: p for p in necesidades}

    # Producciones en Calendar (y manual legacy) próximos N días
    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()
    fecha_hasta = (hoy + _td(days=horizonte)).isoformat()
    cal_por_prod = {}
    rows = c.execute(
        """SELECT producto,
                  GROUP_CONCAT(fecha_programada || '|' || COALESCE(cantidad_kg,0)),
                  COUNT(*),
                  COALESCE(SUM(cantidad_kg), 0),
                  GROUP_CONCAT(origen, ',')
           FROM produccion_programada
           WHERE origen IN ('calendar','manual')
             AND estado IN ('pendiente','programado','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now', '-5 hours')
             AND date(fecha_programada) <= date(?)
           GROUP BY producto""",
        (fecha_hasta,),
    ).fetchall()
    for r in rows:
        if not r[0]:
            continue
        items = []
        for item in (r[1] or "").split(","):
            if "|" in item:
                f, kg = item.split("|", 1)
                items.append({"fecha": f, "kg": float(kg or 0)})
        items.sort(key=lambda x: x["fecha"])
        cal_por_prod[r[0]] = {
            "n_lotes": int(r[2] or 0),
            "kg_total": round(float(r[3] or 0), 2),
            "fechas": items[:5],
        }

    # Producciones REALES finalizadas últimos 30d · pipeline + ya-en-góndola
    # Sebastián 13-may-2026: "en la misma app aparece cuántos kilos y fechas"
    reales_por_prod = {}
    rows_reales = c.execute(
        """SELECT pp.producto, pp.fin_real_at,
                  COALESCE(pp.kg_real, pp.cantidad_kg, 0),
                  pp.inicio_real_at,
                  COALESCE(pp.inventario_descontado_at, ''),
                  COALESCE(pp.estado, ''),
                  pp.id
           FROM produccion_programada pp
           WHERE pp.fin_real_at IS NOT NULL
             AND date(pp.fin_real_at) >= date('now','-5 hours','-30 day')
           ORDER BY pp.fin_real_at DESC""",
    ).fetchall()
    # numero_op vive en ebr_ejecuciones · lookup separado por produccion_id
    op_por_pp = {}
    try:
        for r in c.execute(
            """SELECT produccion_id, numero_op
               FROM ebr_ejecuciones
               WHERE numero_op IS NOT NULL AND produccion_id IS NOT NULL""",
        ).fetchall():
            op_por_pp[int(r[0])] = r[1]
    except Exception:
        pass

    for r in rows_reales:
        prod = r[0] or ""
        reales_por_prod.setdefault(prod, []).append({
            "fin_real_at": (r[1] or "")[:10],
            "kg_real": round(float(r[2] or 0), 2),
            "inicio_real_at": (r[3] or "")[:10] if r[3] else None,
            "inventario_descontado": bool(r[4]),
            "estado": r[5] or "",
            "numero_op": op_por_pp.get(int(r[6])) if r[6] else None,
        })

    # Comparar por producto · Sebastián 13-may-2026 v2:
    # NUEVA lógica · "producir 20 días antes de agotamiento"
    # - stock_efectivo = stock_gondola + pipeline_7d (ya producido)
    # - fecha_agotamiento = hoy + stock_efectivo / velocidad
    # - fecha_producir_sugerida = agotamiento - 20 días
    # - Comparar FECHA del PRIMER lote Calendar vs sugerido
    out = []
    for nec in necesidades:
        prod = nec["producto_nombre"]
        cal = cal_por_prod.get(prod, {"n_lotes": 0, "kg_total": 0, "fechas": []})
        vel_kg_dia = nec["velocidad_kg_dia"] or 0
        kg_necesario = round(vel_kg_dia * horizonte, 2)
        kg_calendar = cal["kg_total"]
        diff_kg = round(kg_calendar - kg_necesario, 2)
        diff_pct = (diff_kg / kg_necesario * 100) if kg_necesario > 0.01 else (100 if kg_calendar > 0 else 0)

        # Pipeline REAL · producciones finalizadas últimos 7d que aún no
        # están reflejadas en Shopify Available (tarda ~7d el sync)
        reales = reales_por_prod.get(prod, [])
        pipeline_7d_real = 0.0
        for rl in reales:
            try:
                f = _date.fromisoformat(rl["fin_real_at"][:10])
                if (hoy - f).days <= 7:
                    pipeline_7d_real += rl["kg_real"] or 0
            except Exception:
                pass

        # Stock efectivo · góndola + pipeline 7d real (lo recién producido)
        stock_kg_efectivo = (nec["stock_kg_gondola"] or 0) + pipeline_7d_real

        # Fecha agotamiento · con stock efectivo
        if vel_kg_dia > 0.001:
            dias_hasta_agotamiento = stock_kg_efectivo / vel_kg_dia
            try:
                fecha_agotamiento = (hoy + _td(days=int(dias_hasta_agotamiento))).isoformat()
            except Exception:
                fecha_agotamiento = None
        else:
            dias_hasta_agotamiento = None
            fecha_agotamiento = None

        # Fecha producir sugerida · 20 días antes de agotamiento
        if dias_hasta_agotamiento is not None:
            try:
                fecha_producir_sugerida = (hoy + _td(days=max(0, int(dias_hasta_agotamiento) - 20))).isoformat()
            except Exception:
                fecha_producir_sugerida = None
        else:
            fecha_producir_sugerida = None

        # Comparar primer lote Calendar vs sugerido
        primer_lote_fecha = cal["fechas"][0]["fecha"] if cal["fechas"] else None
        diff_dias_timing = None
        timing_status = None
        if primer_lote_fecha and fecha_producir_sugerida:
            try:
                f1 = _date.fromisoformat(primer_lote_fecha[:10])
                fs = _date.fromisoformat(fecha_producir_sugerida[:10])
                diff_dias_timing = (f1 - fs).days  # positivo = tarde, negativo = temprano
                if abs(diff_dias_timing) <= 7:
                    timing_status = "ALINEADO"  # ±1 semana
                elif diff_dias_timing > 7:
                    timing_status = "TARDE"  # Calendar después de sugerido
                else:
                    timing_status = "TEMPRANO"  # Calendar antes de sugerido
            except Exception:
                pass

        # Categorización · prioriza TIMING sobre cantidad
        dias_cob = nec["dias_cobertura"]
        urgencia = nec["urgencia"]
        if urgencia == "SIN_VENTAS":
            categoria = "SIN_VENTAS"
            if cal["n_lotes"] > 0:
                categoria = "AGENDADO_SIN_VENTAS"
        elif urgencia in ("CRITICO", "URGENTE") and cal["n_lotes"] == 0:
            categoria = "URGENTE_SIN_AGENDAR"
        elif timing_status == "TARDE":
            categoria = "TIMING_TARDE"  # NUEVA · más urgente que SUB
        elif urgencia == "OK" and cal["n_lotes"] > 0 and timing_status != "ALINEADO":
            categoria = "AGENDADO_SIN_URGENCIA"
        elif timing_status == "ALINEADO":
            categoria = "MATCH_OK"
        elif kg_necesario > 0 and abs(diff_pct) <= 20:
            categoria = "MATCH_OK"
        elif diff_pct < -20:
            categoria = "SUB_PRODUCCION"
        elif diff_pct > 20:
            categoria = "SOBRE_PRODUCCION"
        else:
            categoria = "MATCH_OK"

        out.append({
            "codigo_pt": nec["codigo_pt"],
            "producto_nombre": prod,
            "urgencia": urgencia,
            "dias_cobertura": dias_cob,
            "stock_uds": nec["stock_uds_total"],
            "stock_kg_gondola": round(nec["stock_kg_gondola"] or 0, 2),
            "pipeline_kg": round(pipeline_7d_real, 2),
            "stock_kg_efectivo": round(stock_kg_efectivo, 2),
            "producciones_reales_30d": reales,
            "velocidad_uds_dia": nec["velocidad_uds_dia"],
            "velocidad_kg_dia": round(vel_kg_dia, 3),
            "fecha_agotamiento": fecha_agotamiento,
            "fecha_producir_sugerida": fecha_producir_sugerida,
            "primer_lote_calendar_fecha": primer_lote_fecha,
            "diff_dias_timing": diff_dias_timing,
            "timing_status": timing_status,
            "kg_necesario_horizonte": kg_necesario,
            "kg_calendar_horizonte": kg_calendar,
            "diff_kg": diff_kg,
            "diff_pct": round(diff_pct, 1),
            "n_lotes_calendar": cal["n_lotes"],
            "fechas_calendar": cal["fechas"],
            "lote_bulk_kg": nec["lote_bulk_kg"],
            "categoria": categoria,
        })

    # Productos en Calendar SIN match en necesidades (productos no-Animus o
    # que no están en formula_headers · descontinuados?)
    productos_animus = {n["producto_nombre"] for n in necesidades}
    rows_huerfanos = c.execute(
        """SELECT producto, COUNT(*), SUM(cantidad_kg)
           FROM produccion_programada
           WHERE origen IN ('calendar','manual')
             AND estado IN ('pendiente','programado','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now', '-5 hours')
             AND date(fecha_programada) <= date(?)
           GROUP BY producto""",
        (fecha_hasta,),
    ).fetchall()
    huerfanos = [{
        "producto": r[0],
        "n_lotes": int(r[1] or 0),
        "kg_total": round(float(r[2] or 0), 2),
    } for r in rows_huerfanos if r[0] not in productos_animus]

    # Resumen
    cats = {}
    for o in out:
        cats[o["categoria"]] = cats.get(o["categoria"], 0) + 1

    return jsonify({
        "horizonte_dias": horizonte,
        "fecha_hasta": fecha_hasta,
        "total_productos": len(out),
        "total_calendar_lotes": sum(o["n_lotes_calendar"] for o in out) + sum(h["n_lotes"] for h in huerfanos),
        "resumen_categorias": cats,
        "productos": out,
        "huerfanos_calendar": huerfanos,
    })


_COMPARAR_CALENDAR_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Comparar Calendar vs Necesidades · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1400px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:13px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
select{padding:9px 14px;border:1px solid #cbd5e1;border-radius:8px;font-size:13px}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;margin-bottom:8px;text-align:center;min-width:130px;vertical-align:top}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:22px;font-weight:800}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer}
td{padding:7px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;color:#1e40af}
.cat-MATCH_OK{background:#dcfce7;color:#166534;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-URGENTE_SIN_AGENDAR{background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-AGENDADO_SIN_URGENCIA{background:#fef3c7;color:#854d0e;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-SUB_PRODUCCION{background:#fed7aa;color:#9a3412;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-SOBRE_PRODUCCION{background:#e9d5ff;color:#581c87;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-SIN_VENTAS{background:#f1f5f9;color:#64748b;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-AGENDADO_SIN_VENTAS{background:#fecaca;color:#7f1d1d;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.cat-TIMING_TARDE{background:#fecaca;color:#7f1d1d;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px}
.tim-OK{color:#166534;font-weight:700}
.tim-TARDE{color:#dc2626;font-weight:700}
.tim-TEMPRANO{color:#7c3aed;font-weight:700}
.diff-pos{color:#581c87;font-weight:700}
.diff-neg{color:#dc2626;font-weight:700}
.diff-ok{color:#166534}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver al panel</a>
<div class="card">
  <h1>📊 Comparar Google Calendar vs Necesidades reales</h1>
  <div class="muted">Análisis read-only · cruza producciones agendadas en Calendar contra lo que el sistema dice que necesitás producir (basado en Shopify ventas + stock actual). NO modifica nada.</div>
  <div style="display:flex;gap:10px;margin-top:14px;align-items:center;flex-wrap:wrap">
    Horizonte: <select id="hz">
      <option value="60">60 días</option>
      <option value="90" selected>90 días</option>
      <option value="180">180 días</option>
      <option value="365">1 año</option>
    </select>
    <button onclick="cargar()">▶ Analizar</button>
  </div>
  <div id="kpis" style="margin-top:14px"></div>
</div>
<div id="resultados"></div>
</div>
<script>
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

async function cargar() {
  document.getElementById('resultados').innerHTML = '<div class="card">Analizando…</div>';
  var hz = document.getElementById('hz').value;
  try {
    var r = await fetch('/api/plan/comparar-calendar-necesidades?horizonte_dias=' + hz);
    var d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
    render(d);
  } catch(e) { alert('Error: ' + e.message); }
}

const CAT_NAME = {
  MATCH_OK: '✅ Timing alineado',
  URGENTE_SIN_AGENDAR: '🔴 Urgente sin agendar',
  TIMING_TARDE: '🔴 Calendar TARDE (se agota antes)',
  AGENDADO_SIN_URGENCIA: '🟠 Agendado sin urgencia',
  SUB_PRODUCCION: '🟧 Sub-producción (kg)',
  SOBRE_PRODUCCION: '🟪 Sobre-producción (kg)',
  SIN_VENTAS: '⚪ Sin ventas',
  AGENDADO_SIN_VENTAS: '🔴 Agendado SIN VENTAS',
};

function render(d) {
  // KPIs
  var k = '';
  k += '<span class="kpi"><div class="kpi-lbl">Productos Animus</div><div class="kpi-val">' + d.total_productos + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">📅 Lotes Calendar</div><div class="kpi-val">' + d.total_calendar_lotes + '</div></span>';
  var cats = d.resumen_categorias || {};
  ['MATCH_OK','URGENTE_SIN_AGENDAR','AGENDADO_SIN_URGENCIA','SUB_PRODUCCION','SOBRE_PRODUCCION','AGENDADO_SIN_VENTAS','SIN_VENTAS'].forEach(c => {
    if (cats[c] > 0) k += '<span class="kpi"><div class="kpi-lbl">' + CAT_NAME[c] + '</div><div class="kpi-val">' + cats[c] + '</div></span>';
  });
  document.getElementById('kpis').innerHTML = k;

  // Veredicto resumen
  var veredicto = '';
  var totalProblemas = (cats.URGENTE_SIN_AGENDAR||0) + (cats.TIMING_TARDE||0) + (cats.AGENDADO_SIN_URGENCIA||0) + (cats.SUB_PRODUCCION||0) + (cats.SOBRE_PRODUCCION||0) + (cats.AGENDADO_SIN_VENTAS||0);
  if (totalProblemas === 0) {
    veredicto = '<div class="card" style="border:2px solid #16a34a;background:#f0fdf4"><h2 style="margin:0;color:#166534">✅ Calendar está alineado con necesidades · podrías migrar a Plan sin pérdida</h2></div>';
  } else if (totalProblemas > d.total_productos / 2) {
    veredicto = '<div class="card" style="border:2px solid #dc2626;background:#fef2f2"><h2 style="margin:0 0 6px;color:#991b1b">⚠ Calendar tiene desviación significativa (' + totalProblemas + ' de ' + d.total_productos + ')</h2><div class="muted">Antes de migrar · revisar uno a uno · varios casos no reflejan necesidad real.</div></div>';
  } else {
    veredicto = '<div class="card" style="border:2px solid #ca8a04;background:#fefce8"><h2 style="margin:0 0 6px;color:#854d0e">🟠 Calendar mayormente bien, pero ' + totalProblemas + ' casos requieren revisión</h2><div class="muted">Lista abajo · cada uno con su categoría · podés migrar después de ajustar.</div></div>';
  }

  // Tabla agrupada por categoría · ordenadas por urgencia
  var grupos = {};
  d.productos.forEach(p => { (grupos[p.categoria] = grupos[p.categoria]||[]).push(p); });

  var orden = ['URGENTE_SIN_AGENDAR','TIMING_TARDE','AGENDADO_SIN_VENTAS','SUB_PRODUCCION','SOBRE_PRODUCCION','AGENDADO_SIN_URGENCIA','MATCH_OK','SIN_VENTAS'];
  var tbl = '';
  orden.forEach(cat => {
    var g = grupos[cat];
    if (!g || g.length === 0) return;
    tbl += '<div class="card"><h3 style="margin:0 0 12px"><span class="cat-' + cat + '">' + CAT_NAME[cat] + '</span> · ' + g.length + ' productos</h3>';
    tbl += '<table><thead><tr>';
    tbl += '<th>Cód</th><th>Producto</th>';
    tbl += '<th>Stock kg<br><span style="font-weight:400;font-size:10px">+ pipeline</span></th>';
    tbl += '<th>Vel<br>kg/día</th>';
    tbl += '<th>Días<br>cob</th>';
    tbl += '<th>Se agota</th>';
    tbl += '<th>Producir<br>sugerido<br>(−20d)</th>';
    tbl += '<th>Producido<br>últ 30d</th>';
    tbl += '<th>Calendar<br>1er lote</th>';
    tbl += '<th>Δ timing</th>';
    tbl += '<th>Lote<br>típico</th>';
    tbl += '<th>kg<br>nec vs cal</th>';
    tbl += '<th>Otros lotes Cal</th>';
    tbl += '</tr></thead><tbody>';
    g.forEach(p => {
      var diffCls = Math.abs(p.diff_pct||0) <= 20 ? 'diff-ok' : ((p.diff_kg||0) < 0 ? 'diff-neg' : 'diff-pos');
      var timCls = p.timing_status === 'ALINEADO' ? 'tim-OK' : (p.timing_status === 'TARDE' ? 'tim-TARDE' : (p.timing_status === 'TEMPRANO' ? 'tim-TEMPRANO' : ''));
      var timTxt = p.diff_dias_timing != null ? (p.diff_dias_timing > 0 ? '+' + p.diff_dias_timing + 'd tarde' : (p.diff_dias_timing < 0 ? p.diff_dias_timing + 'd temprano' : 'mismo día')) : '—';
      var todasFechas = (p.fechas_calendar||[]).slice(1).map(f => f.fecha + ' (' + f.kg + 'kg)').join(' · ') || '—';
      var pipeline = (p.pipeline_kg||0) > 0 ? ' <span style="color:#0891b2;font-weight:700" title="ya producido últ 7d · aún no en Shopify">+' + p.pipeline_kg + ' pipe</span>' : '';
      var realesTxt = '—';
      if ((p.producciones_reales_30d||[]).length) {
        realesTxt = p.producciones_reales_30d.map(r => r.fin_real_at + ' (' + r.kg_real + 'kg' + (r.numero_op ? ' · ' + r.numero_op : '') + ')').join('<br>');
      }
      tbl += '<tr>';
      tbl += '<td class="mono">' + escapeHtml(p.codigo_pt||'') + '</td>';
      tbl += '<td><strong>' + escapeHtml(p.producto_nombre) + '</strong><br><span style="color:#64748b;font-size:10px">' + p.stock_uds + ' uds</span></td>';
      tbl += '<td style="text-align:right"><strong>' + (p.stock_kg_gondola||0) + '</strong>' + pipeline + '</td>';
      tbl += '<td style="text-align:right">' + (p.velocidad_kg_dia||0).toFixed(2) + '</td>';
      tbl += '<td style="text-align:center">' + (p.dias_cobertura != null ? p.dias_cobertura + 'd' : '—') + '</td>';
      tbl += '<td style="text-align:center;color:#dc2626;font-weight:600">' + (p.fecha_agotamiento || '—') + '</td>';
      tbl += '<td style="text-align:center;color:#166534;font-weight:700">' + (p.fecha_producir_sugerida || '—') + '</td>';
      tbl += '<td style="font-size:10px;color:#0891b2">' + realesTxt + '</td>';
      tbl += '<td style="text-align:center">' + (p.primer_lote_calendar_fecha || '—') + '</td>';
      tbl += '<td style="text-align:center" class="' + timCls + '">' + timTxt + '</td>';
      tbl += '<td style="text-align:right;color:#64748b;font-size:11px">' + (p.lote_bulk_kg ? p.lote_bulk_kg + 'kg' : '—') + '</td>';
      tbl += '<td style="text-align:right" class="' + diffCls + '">' + (p.kg_necesario_horizonte||0) + ' / ' + (p.kg_calendar_horizonte||0) + 'kg</td>';
      tbl += '<td style="font-size:10px;color:#64748b">' + escapeHtml(todasFechas) + '</td>';
      tbl += '</tr>';
    });
    tbl += '</tbody></table></div>';
  });

  // Huérfanos en Calendar
  if (d.huerfanos_calendar && d.huerfanos_calendar.length) {
    tbl += '<div class="card"><h3 style="margin:0 0 8px;color:#dc2626">🚧 Productos en Calendar que NO están en Animus DTC · ' + d.huerfanos_calendar.length + '</h3>';
    tbl += '<div class="muted" style="margin-bottom:8px">Probablemente: maquila B2B, productos descontinuados, errores de tipeo. Revisar manualmente.</div>';
    tbl += '<table><thead><tr><th>Producto</th><th>Lotes</th><th>kg total</th></tr></thead><tbody>';
    d.huerfanos_calendar.forEach(h => {
      tbl += '<tr><td>' + escapeHtml(h.producto) + '</td><td style="text-align:center">' + h.n_lotes + '</td><td style="text-align:right">' + h.kg_total + 'kg</td></tr>';
    });
    tbl += '</tbody></table></div>';
  }

  document.getElementById('resultados').innerHTML = veredicto + tbl;
}
cargar();
</script>
</body></html>"""


@bp.route("/admin/mps-buscar", methods=["GET"])
def mps_buscar_page():
    """Página admin · buscar MPs por nombre · ver stock individual + total + min."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/mps-buscar")
    from flask import Response
    return Response(_BUSCADOR_MPS_HTML, mimetype="text/html")


@bp.route("/api/plan/mps-buscar", methods=["GET"])
def mps_buscar():
    """Busca MPs cuyo nombre INCI/comercial contiene query.

    Sebastián 13-may-2026: "mira todas las centellas que hay · todos los
    lotes deben sumar entre sí para evitar alertas falsas".

    Devuelve grupo con suma de stocks + qué productos usan cada MP +
    stock_minimo de cada una. Útil para identificar MPs equivalentes
    candidatas a consolidación.

    Query: ?q=centella · normalizado (sin acentos)
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    q = (request.args.get("q") or "").strip().lower()
    if len(q) < 3:
        return jsonify({"error": "query mínimo 3 chars"}), 400

    conn = get_db()
    c = conn.cursor()

    # Stock por material_id
    mp_stock = {}
    for r in c.execute(
        """SELECT material_id,
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
                                    THEN cantidad ELSE -cantidad END), 0)
           FROM movimientos
           WHERE material_id IS NOT NULL AND TRIM(material_id) != ''
           GROUP BY material_id""",
    ).fetchall():
        mp_stock[str(r[0]).strip()] = max(float(r[1] or 0), 0)

    # Productos que usan cada MP (formula_items activos)
    usos = {}
    for r in c.execute(
        """SELECT fi.material_id, GROUP_CONCAT(DISTINCT fi.producto_nombre)
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo, 1) = 1
             AND fi.material_id IS NOT NULL AND TRIM(fi.material_id) != ''
           GROUP BY fi.material_id""",
    ).fetchall():
        usos[str(r[0]).strip()] = [p for p in (r[1] or "").split(",") if p]

    # Buscar en maestro_mps por nombre LIKE
    import unicodedata
    def _norm(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().lower())
        return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

    rows = c.execute(
        """SELECT codigo_mp,
                  COALESCE(nombre_comercial, ''),
                  COALESCE(nombre_inci, ''),
                  COALESCE(stock_minimo, 0),
                  COALESCE(activo, 1),
                  COALESCE(proveedor, '')
           FROM maestro_mps""",
    ).fetchall()
    q_norm = _norm(q)
    items = []
    for r in rows:
        cod, ncom, ninci, stmin, act, prov = r
        if q_norm in _norm(ncom) or q_norm in _norm(ninci):
            items.append({
                "codigo": cod,
                "nombre_comercial": ncom,
                "nombre_inci": ninci,
                "stock_minimo": float(stmin or 0),
                "stock_actual": round(mp_stock.get(cod, 0), 2),
                "activo": int(act),
                "proveedor": prov,
                "usado_en": usos.get(cod, [])[:5],
            })

    # Ordenar: activos primero · stock_actual DESC
    items.sort(key=lambda x: (-x["activo"], -x["stock_actual"]))
    stock_total = sum(it["stock_actual"] for it in items)
    stock_min_total = sum(it["stock_minimo"] for it in items)
    n_activos = sum(1 for it in items if it["activo"] == 1)
    return jsonify({
        "query": q,
        "total": len(items),
        "n_activos": n_activos,
        "stock_total_g": round(stock_total, 2),
        "stock_min_total_g": round(stock_min_total, 2),
        "items": items,
    })


_BUSCADOR_MPS_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Buscar MPs · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1300px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:13px}
input[type=text]{padding:10px 14px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;width:300px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;text-align:center;min-width:140px}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:24px;font-weight:800}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:7px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;color:#1e40af}
.ok{color:#16a34a}
.crit{color:#dc2626}
.inactivo{background:#fee2e2;color:#991b1b;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.suger{display:inline-block;background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:4px;cursor:pointer;text-decoration:none}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver al panel</a>
<div class="card">
  <h1>🔍 Buscar MPs · ver stock por grupo</h1>
  <div class="muted">Buscá una palabra clave (ej: <a class="suger" onclick="buscarTermino(&quot;centella&quot;)">centella</a>
  <a class="suger" onclick="buscarTermino(&quot;hialuronico&quot;)">hialurónico</a>
  <a class="suger" onclick="buscarTermino(&quot;pantenol&quot;)">pantenol</a>
  <a class="suger" onclick="buscarTermino(&quot;soda&quot;)">soda</a>
  <a class="suger" onclick="buscarTermino(&quot;niacinamida&quot;)">niacinamida</a>
  <a class="suger" onclick="buscarTermino(&quot;palmitoyl&quot;)">palmitoyl</a>) y mirá si hay varias MPs equivalentes con stock disperso.</div>
  <div style="margin-top:16px;display:flex;gap:10px;align-items:center">
    <input type="text" id="q" placeholder="ej: centella" onkeydown="if(event.key==='Enter')buscar()">
    <button onclick="buscar()">▶ Buscar</button>
  </div>
  <div id="kpis" style="margin-top:16px"></div>
</div>
<div id="resultados"></div>
</div>
<script>
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function buscarTermino(t){ document.getElementById('q').value = t; buscar(); }

async function buscar() {
  const q = document.getElementById('q').value.trim();
  if (q.length < 3) { alert('Ingresá al menos 3 caracteres'); return; }
  document.getElementById('resultados').innerHTML = '<div class="card">Buscando…</div>';
  try {
    var r = await fetch('/api/plan/mps-buscar?q=' + encodeURIComponent(q));
    var d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
    render(d);
  } catch(e) { alert('Error: ' + e.message); }
}

function render(d) {
  var k = '';
  k += '<span class="kpi"><div class="kpi-lbl">Resultados</div><div class="kpi-val">' + d.total + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">Activos</div><div class="kpi-val ok">' + d.n_activos + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">📦 Stock total grupo</div><div class="kpi-val">' + Number(d.stock_total_g).toLocaleString() + ' g</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">⚠ Min total</div><div class="kpi-val">' + Number(d.stock_min_total_g).toLocaleString() + ' g</div></span>';
  document.getElementById('kpis').innerHTML = k;

  if (!d.items.length) {
    document.getElementById('resultados').innerHTML = '<div class="card">Sin resultados para "' + escapeHtml(d.query) + '"</div>';
    return;
  }
  var out = '<div class="card"><h3 style="margin:0 0 8px">Resultados · "' + escapeHtml(d.query) + '"</h3>';
  out += '<table><thead><tr><th>Código</th><th>Comercial</th><th>INCI</th><th>Proveedor</th><th style="text-align:right">Stock actual</th><th style="text-align:right">Stock min</th><th>Estado</th><th>Usado en (productos)</th></tr></thead><tbody>';
  d.items.forEach(it => {
    var stockClass = (it.stock_actual === 0 ? 'crit' : (it.stock_actual < it.stock_minimo ? 'crit' : 'ok'));
    var estado = it.activo === 1 ? '✅ activo' : '<span class="inactivo">inactivo</span>';
    var usos = (it.usado_en || []).slice(0,3).map(escapeHtml).join(', ');
    if ((it.usado_en || []).length > 3) usos += ' +' + (it.usado_en.length - 3);
    out += '<tr><td class="mono">' + escapeHtml(it.codigo) + '</td>'
       + '<td>' + escapeHtml(it.nombre_comercial) + '</td>'
       + '<td style="font-size:11px;color:#64748b">' + escapeHtml(it.nombre_inci) + '</td>'
       + '<td style="font-size:11px">' + escapeHtml(it.proveedor) + '</td>'
       + '<td style="text-align:right" class="' + stockClass + '">' + Number(it.stock_actual).toLocaleString() + ' g</td>'
       + '<td style="text-align:right">' + Number(it.stock_minimo).toLocaleString() + ' g</td>'
       + '<td>' + estado + '</td>'
       + '<td style="font-size:11px;color:#475569">' + usos + '</td></tr>';
  });
  out += '</tbody></table></div>';
  document.getElementById('resultados').innerHTML = out;
}
</script>
</body></html>"""


@bp.route("/admin/detector-mps-renombre", methods=["GET"])
def detector_mps_renombre_page():
    """Página admin · detecta MPs usadas en fórmulas con stock=0 PERO con
    MP similares en BD que SÍ tienen stock · candidatas a renombre."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/detector-mps-renombre")
    from flask import Response
    return Response(_DETECTOR_RENOMBRE_HTML, mimetype="text/html")


@bp.route("/api/plan/detector-mps-renombre", methods=["GET"])
def detector_mps_renombre():
    """Para cada material_id usado en formula_items con stock=0,
    buscar candidatas en maestro_mps con nombre similar Y stock>0.

    Sebastián 13-may-2026: "me preocupa que esté sucediendo con otras
    materias primas · stock 0 pero salen como otras MPs".

    Response:
        sospechosos: [
            {codigo_formula, nombre_formula, stock_formula:0,
             usado_en_productos: [...],
             candidatas_renombre: [{codigo, nombre_comercial, nombre_inci,
                                     stock_g, similitud}]}
        ]
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    conn = get_db()
    c = conn.cursor()

    # 1. Stock por material_id
    mp_stock = {}
    for r in c.execute(
        """SELECT material_id,
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
                                    THEN cantidad ELSE -cantidad END), 0)
           FROM movimientos
           WHERE material_id IS NOT NULL AND TRIM(material_id) != ''
           GROUP BY material_id""",
    ).fetchall():
        mp_stock[str(r[0]).strip()] = max(float(r[1] or 0), 0)

    # 2. MPs usadas en formula_items activos · qué productos las usan
    usados = {}
    for r in c.execute(
        """SELECT fi.material_id, fi.material_nombre,
                  GROUP_CONCAT(DISTINCT fi.producto_nombre)
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo, 1) = 1
             AND fi.material_id IS NOT NULL
             AND TRIM(fi.material_id) != ''
           GROUP BY fi.material_id, fi.material_nombre""",
    ).fetchall():
        cod = str(r[0]).strip()
        usados[cod] = {
            "codigo_formula": cod,
            "nombre_formula": (r[1] or "")[:60],
            "stock_formula": round(mp_stock.get(cod, 0), 2),
            "usado_en_productos": [p for p in (r[2] or "").split(",") if p][:5],
        }

    # 3. Universo MPs en maestro_mps · nombre + stock
    maestro_mps_info = {}
    for r in c.execute(
        """SELECT codigo_mp,
                  COALESCE(nombre_comercial, ''),
                  COALESCE(nombre_inci, ''),
                  COALESCE(activo, 1)
           FROM maestro_mps""",
    ).fetchall():
        maestro_mps_info[r[0]] = {
            "codigo": r[0],
            "nombre_comercial": r[1],
            "nombre_inci": r[2],
            "activo": int(r[3]),
            "stock_g": round(mp_stock.get(r[0], 0), 2),
        }

    # 4. Buscar candidatas a renombre · para cada MP usada con stock=0,
    # buscar OTRA MP con nombre parecido Y stock > 0
    import unicodedata
    def _norm(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().lower())
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        for ch in ('.', ',', '-', '/', '(', ')', ' ', '\t', '\n', '%'):
            s = s.replace(ch, '')
        return s

    sospechosos = []
    for cod, info in usados.items():
        if info["stock_formula"] > 0.01:
            continue  # tiene stock · no sospechoso
        # Buscar candidatas con nombre similar Y stock > 0
        nom_formula = _norm(info["nombre_formula"])
        if len(nom_formula) < 4:
            continue
        candidatas = []
        for otro_cod, otro_info in maestro_mps_info.items():
            if otro_cod == cod:
                continue
            if otro_info["stock_g"] <= 0:
                continue
            nom_otro_com = _norm(otro_info["nombre_comercial"])
            nom_otro_inci = _norm(otro_info["nombre_inci"])
            # Match si prefijo 5-7 chars matchea
            match_score = 0
            if nom_formula[:6] and nom_otro_com[:6] and nom_formula[:6] == nom_otro_com[:6]:
                match_score = 90
            elif nom_formula[:6] and nom_otro_inci[:6] and nom_formula[:6] == nom_otro_inci[:6]:
                match_score = 85
            elif nom_formula[:4] in nom_otro_com or nom_otro_com[:4] in nom_formula:
                match_score = 60
            elif nom_formula[:4] in nom_otro_inci or nom_otro_inci[:4] in nom_formula:
                match_score = 55
            if match_score >= 55:
                candidatas.append({
                    "codigo": otro_cod,
                    "nombre_comercial": otro_info["nombre_comercial"],
                    "nombre_inci": otro_info["nombre_inci"],
                    "stock_g": otro_info["stock_g"],
                    "similitud": match_score,
                })
        if candidatas:
            candidatas.sort(key=lambda x: -x["similitud"])
            info["candidatas_renombre"] = candidatas[:5]
            sospechosos.append(info)

    sospechosos.sort(key=lambda x: -len(x.get("candidatas_renombre", [])))
    return jsonify({
        "total_sospechosos": len(sospechosos),
        "total_mps_usadas_sin_stock": sum(1 for u in usados.values() if u["stock_formula"] <= 0.01),
        "total_mps_usadas": len(usados),
        "sospechosos": sospechosos,
    })


_DETECTOR_RENOMBRE_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Detector MPs renombre · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1300px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#dc2626;font-size:22px}
.muted{color:#64748b;font-size:13px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;text-align:center;min-width:140px}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:24px;font-weight:800}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:7px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;color:#1e40af}
.crit{color:#dc2626}
.bad{color:#94a3b8}
.sim-alta{background:#dcfce7;color:#166534;padding:2px 6px;border-radius:4px;font-weight:700}
.sim-media{background:#fef3c7;color:#854d0e;padding:2px 6px;border-radius:4px;font-weight:700}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver al panel</a>
<div class="card">
  <h1>🔍 Detector MPs renombre · stock 0 con candidatas</h1>
  <div class="muted">Busca MPs usadas en fórmulas activas con stock=0 PERO con otra MP de nombre similar que SÍ tiene stock. Probable causa: rename de Alejandro · stock quedó en código viejo.</div>
  <div style="margin-top:16px"><button onclick="cargar()">▶ Buscar candidatas</button></div>
  <div id="kpis" style="margin-top:16px"></div>
</div>
<div id="resultados"></div>
</div>
<script>
function csrf() { var m = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/); return m ? decodeURIComponent(m[1]) : ''; }
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

async function cargar() {
  document.getElementById('resultados').innerHTML = '<div class="card">Buscando…</div>';
  try {
    var r = await fetch('/api/plan/detector-mps-renombre');
    var d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
    render(d);
  } catch(e) { alert('Error: ' + e.message); }
}

function render(d) {
  var k = '';
  k += '<span class="kpi"><div class="kpi-lbl">Total MPs usadas</div><div class="kpi-val">' + d.total_mps_usadas + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">Sin stock</div><div class="kpi-val crit">' + d.total_mps_usadas_sin_stock + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">🔍 Sospechosas</div><div class="kpi-val crit">' + d.total_sospechosos + '</div></span>';
  document.getElementById('kpis').innerHTML = k;

  if (!d.sospechosos.length) {
    document.getElementById('resultados').innerHTML = '<div class="card"><h3 style="margin:0;color:#16a34a">✅ Sin sospechosos · todas las MPs sin stock no tienen candidatas con stock similar</h3></div>';
    return;
  }
  var out = '<div class="card"><h3 style="margin:0 0 8px;color:#dc2626">🔍 ' + d.sospechosos.length + ' MPs sospechosas · posibles renombres</h3>';
  out += '<div class="muted" style="margin-bottom:12px">Cada fila muestra una MP de la fórmula con stock=0 + candidatas en BD con stock>0 y nombre similar. Revisar manualmente y consolidar.</div>';
  out += '<table><thead><tr><th>Código fórmula</th><th>Nombre fórmula</th><th>Productos</th><th>Candidatas (código · nombre · stock · similitud)</th></tr></thead><tbody>';
  d.sospechosos.forEach(s => {
    var cands = '';
    s.candidatas_renombre.forEach(c => {
      var sim = c.similitud >= 80 ? 'sim-alta' : 'sim-media';
      cands += '<div style="margin-bottom:4px"><span class="mono">' + escapeHtml(c.codigo) + '</span> · <strong>' + escapeHtml(c.nombre_comercial || c.nombre_inci) + '</strong> · <span style="background:#dbeafe;padding:2px 6px;border-radius:4px">' + c.stock_g + 'g</span> · <span class="' + sim + '">' + c.similitud + '%</span></div>';
    });
    out += '<tr><td class="mono">' + escapeHtml(s.codigo_formula) + '</td><td>' + escapeHtml(s.nombre_formula) + '</td><td style="font-size:11px;color:#475569">' + (s.usado_en_productos || []).map(escapeHtml).join(', ') + '</td><td>' + cands + '</td></tr>';
  });
  out += '</tbody></table></div>';
  document.getElementById('resultados').innerHTML = out;
}
</script>
</body></html>"""


@bp.route("/api/plan/debug-origenes", methods=["GET"])
def plan_debug_origenes():
    """Diagnóstico · de dónde sale cada lote del plan + detección de
    duplicados globales.

    Sebastián 14-may-2026: "veo mucha cosa repetida como producción
    esta semana y se repite la proxima, de donde esta tomando ese
    calendario".

    Devuelve:
      por_origen: {calendar: N, eos_plan: M, eos_canonico: K, ...}
      duplicados: pares de lotes mismo producto + < 21 días entre fechas
      total_activos: lotes pendientes/programados/en_curso/esperando
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()
    from datetime import date as _date

    # Conteo por origen
    rows = c.execute(
        """SELECT COALESCE(origen,'(NULL)'), COUNT(*),
                  GROUP_CONCAT(producto || '|' || fecha_programada || '|' ||
                              COALESCE(cantidad_kg,0) || '|' || id, '~~')
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','en_curso','esperando_recurso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now', '-5 hours', '-7 day')
             AND date(fecha_programada) <= date('now', '-5 hours', '+365 day')
           GROUP BY origen""",
    ).fetchall()
    por_origen = {}
    todos_lotes = []
    for r in rows:
        origen = r[0]
        n = int(r[1] or 0)
        por_origen[origen] = n
        for entry in (r[2] or "").split("~~"):
            parts = entry.split("|")
            if len(parts) == 4:
                todos_lotes.append({
                    "producto": parts[0],
                    "fecha": parts[1][:10],
                    "kg": float(parts[2] or 0),
                    "id": int(parts[3]),
                    "origen": origen,
                })

    # Detectar duplicados globales · mismo producto + < 21 días
    duplicados = []
    by_prod = {}
    for lt in todos_lotes:
        by_prod.setdefault(lt["producto"], []).append(lt)
    for prod, lotes in by_prod.items():
        lotes_sorted = sorted(lotes, key=lambda x: x["fecha"])
        for i, la in enumerate(lotes_sorted):
            for lb in lotes_sorted[i + 1:]:
                try:
                    fa = _date.fromisoformat(la["fecha"])
                    fb = _date.fromisoformat(lb["fecha"])
                    delta = (fb - fa).days
                    if delta < 21:
                        duplicados.append({
                            "producto": prod,
                            "id_temprano": la["id"], "fecha_temprano": la["fecha"],
                            "origen_temprano": la["origen"], "kg_temprano": la["kg"],
                            "id_tardio": lb["id"], "fecha_tardio": lb["fecha"],
                            "origen_tardio": lb["origen"], "kg_tardio": lb["kg"],
                            "delta_dias": delta,
                            "sugerencia_cancelar_id": lb["id"] if lb["origen"] == 'calendar' else la["id"],
                            "sugerencia_razon": "Calendar legacy reemplazado por EOS" if (lb["origen"] == 'calendar' or la["origen"] == 'calendar') else "Doble agendamiento",
                        })
                    else:
                        break  # ordenado, demás están más lejos
                except Exception:
                    pass

    return jsonify({
        "por_origen": por_origen,
        "total_activos": sum(por_origen.values()),
        "duplicados": duplicados,
        "n_duplicados": len(duplicados),
        "info_origenes": {
            "calendar": "Mirror de Google Calendar (legacy · animuslb.com)",
            "manual": "Calendar legacy manual (antes de EOS Plan)",
            "eos_plan": "Programado desde Plan-Sugerido o modal Solicitar",
            "eos_canonico": "Programación recurrente (cada N días)",
            "eos_retroactivo": "Back-fill · producción real ya completada",
        },
    })


@bp.route("/api/plan/debug-tz", methods=["GET"])
def plan_debug_tz():
    """Diagnóstico timezone · UTC vs Colombia · valida fix Sebastián.

    "veo errores en la programacion las fechas estan raras... te pasaba
    cuando lo extraias de google calendar". Causa: Render en UTC, planta
    en UTC-5. Después de 7pm Colombia, date.today() salta al día siguiente.
    """
    err = _require_login()
    if err:
        return err
    from datetime import datetime as _dt, date as _date, timezone as _tz
    import time as _time
    now_utc = _dt.now(_tz.utc)
    now_col = _now_colombia()
    hoy_buggy = _date.today()        # depende de TZ del servidor
    hoy_correcto = _hoy_colombia()   # siempre Colombia

    # SQLite comparison
    conn = get_db()
    c = conn.cursor()
    sql_now_utc = c.execute("SELECT datetime('now', '-5 hours')").fetchone()[0]
    sql_now_col = c.execute("SELECT datetime('now', '-5 hours')").fetchone()[0]
    sql_date_utc = c.execute("SELECT date('now', '-5 hours')").fetchone()[0]
    sql_date_col = c.execute("SELECT date('now', '-5 hours')").fetchone()[0]

    es_consistente = (hoy_correcto.isoformat() == sql_date_col)
    bug_activo = (hoy_buggy != hoy_correcto) or (sql_date_utc != sql_date_col)

    return jsonify({
        "now_utc": now_utc.isoformat(),
        "now_colombia": now_col.isoformat(),
        "hoy_buggy_servidor": hoy_buggy.isoformat(),
        "hoy_correcto_colombia": hoy_correcto.isoformat(),
        "sqlite_datetime_now_utc": sql_now_utc,
        "sqlite_datetime_now_colombia": sql_now_col,
        "sqlite_date_now_utc": sql_date_utc,
        "sqlite_date_now_colombia": sql_date_col,
        "es_consistente_python_vs_sqlite": es_consistente,
        "bug_activo_ahora_mismo": bug_activo,
        "diagnostico": (
            "✅ Plan v3 usa hoy_correcto_colombia y date('now','-5 hours') "
            "para evitar inconsistencias. Si bug_activo_ahora_mismo=true significa que "
            "el server está después de 7pm Colombia y los cálculos legacy "
            "estarían 1 día desplazados (pero plan v3 está protegido)."
        ),
    })


@bp.route("/api/plan/festivos", methods=["GET"])
def plan_festivos():
    """Lista festivos colombianos para uno o varios años.

    Sebastián 13-may-2026: usado para verificar visualmente que la lista
    coincide con la realidad antes de programar producciones automáticas.
    Calculado algoritmicamente (Butcher para Pascua + Ley Emiliani).

    Query: ?year=2026 · ?year=2026,2027 · default año actual + siguiente
    """
    err = _require_login()
    if err:
        return err
    from datetime import date as _date
    years_param = (request.args.get("year") or "").strip()
    if years_param:
        try:
            years = [int(y) for y in years_param.split(",")]
        except ValueError:
            return jsonify({"error": "year debe ser entero (separados por coma)"}), 400
    else:
        hoy = _hoy_colombia()
        years = [hoy.year, hoy.year + 1]

    NOMBRES = {
        (1, 1): "Año Nuevo",
        (5, 1): "Día del Trabajo",
        (7, 20): "Independencia",
        (8, 7): "Batalla de Boyacá",
        (12, 8): "Inmaculada Concepción",
        (12, 25): "Navidad",
    }
    DIAS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

    out = {}
    for year in years:
        fest = sorted(_festivos_colombia_year(year))
        pascua = _calcular_pascua(year)
        from datetime import timedelta as _td2
        # Mapeo fecha → descripción derivada
        descripciones = {}
        descripciones[pascua - _td2(days=3)] = "Jueves Santo"
        descripciones[pascua - _td2(days=2)] = "Viernes Santo"
        items = []
        for f in fest:
            nombre = NOMBRES.get((f.month, f.day))
            if not nombre:
                nombre = descripciones.get(f, "Festivo movido (Ley Emiliani)")
            items.append({
                "fecha": f.isoformat(),
                "dia": DIAS_ES[f.weekday()],
                "nombre": nombre,
            })
        out[str(year)] = items

    return jsonify({"festivos_por_year": out, "pascua_por_year": {
        str(y): _calcular_pascua(y).isoformat() for y in years
    }})


@bp.route("/api/plan/plan-sugerido", methods=["GET"])
def plan_sugerido():
    """Genera el plan COMPLETO de producción aplicando todas las reglas.

    Sebastián 13-may-2026: "solo usa lo del excel esa es la realidad,
    y continua". Cruza:
      - Necesidades de Animus DTC + pedidos B2B (consolidador)
      - Producciones reales últ 30d (pipeline + ya en góndola)
      - Festivos colombianos (skip)
      - Lote_size_kg del Excel mig 121 (no inventa cantidades)
      - Reglas operativas:
          · Lote >50kg → 1/día solo
          · Vit C / Triactive → solo Lun/Mié
          · Pares ≤50kg en Lun/Mié/Vie preferido
      - Productos SIN fórmula del Excel → flag separado (no programar)
      - Producciones ya agendadas (Calendar / EOS) → ocupan capacidad

    Query: ?horizonte_semanas=4 (default)

    Devuelve:
      slots[]: {fecha, dia_semana, productos: [{nombre, kg, motivo}]}
      sin_formula[]: productos del análisis pero sin fórmula en Excel
      cancelables_calendar[]: lotes Calendar que se vuelven innecesarios
      backfills[]: producciones completadas a registrar (fin_real_at)
    """
    err = _require_login()
    if err:
        return err
    from datetime import date as _date, timedelta as _td

    # Sebastián 14-may-2026: "queria que hubiera un autoplan que programe
    # 15 dias, 30 dias, 60 dias 90 dias y 120 dias automaticamente".
    # Acepta horizonte_dias directo (15/30/60/90/120) además de _semanas.
    hd_param = request.args.get("horizonte_dias")
    if hd_param:
        try:
            horizonte_dias = max(7, min(365, int(hd_param)))
        except ValueError:
            horizonte_dias = 35
        horizonte_semanas = horizonte_dias // 7
    else:
        horizonte_semanas = int(request.args.get("horizonte_semanas") or 4)
        horizonte_dias = horizonte_semanas * 7 + 7

    conn = get_db()
    c = conn.cursor()

    # 1) Necesidades
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)

    # 2) Producciones reales últ 30d
    reales_por_prod = {}
    rows_reales = c.execute(
        """SELECT producto, fin_real_at,
                  COALESCE(kg_real, cantidad_kg, 0)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= date('now','-5 hours','-30 day')""",
    ).fetchall()
    for r in rows_reales:
        reales_por_prod.setdefault(r[0] or "", []).append({
            "fin_real_at": (r[1] or "")[:10],
            "kg_real": float(r[2] or 0),
        })

    # 3) Productos con fórmula del Excel · whitelist
    productos_con_formula = {}
    for r in c.execute(
        """SELECT producto_nombre, lote_size_kg, COALESCE(activo, 1)
           FROM formula_headers""",
    ).fetchall():
        if r[2]:
            productos_con_formula[(r[0] or "").upper().strip()] = float(r[1] or 0)

    # 4) Iterar necesidades y proponer slots
    # Sebastián 14-may-2026: "ya no lo haga esta semana si no que empiece
    # la proxima colocando todo lo que falta · si la necesidad es mucha
    # puede poner producciones una diaria de lunes a viernes, o dos en un
    # dia si son pequeñas y la formula no es compleja · ser error cero".
    hoy = _hoy_colombia()
    # Saltar a próximo lunes (skip semana actual)
    # weekday() · 0=lun ... 4=vie ... 6=dom
    dias_hasta_lunes = (7 - hoy.weekday()) % 7
    if dias_hasta_lunes == 0:
        dias_hasta_lunes = 7  # si hoy es lunes, saltar al lunes siguiente
    fecha_inicio = hoy + _td(days=dias_hasta_lunes)
    # Si próximo lunes es festivo, _proxima_fecha_habil saltará automáticamente

    slots = []  # cada slot = un día con productos
    slots_por_fecha = {}  # fecha_iso → {fecha, productos}
    sin_formula = []
    plan_items = []  # lista de productos a programar
    # Tracking detallado de productos por día para la regla "2 solo si
    # ambos pequeños Y no complejos"
    detalle_por_fecha = {}  # iso → [{kg, complejo}]

    def _registrar_slot_temporal(producto_nombre, lote_kg, motivo):
        """Devuelve fecha asignada respetando reglas duras:
        - Empieza próxima semana (fecha_inicio = lun siguiente)
        - Skip fines de semana + festivos colombianos
        - Lotes grandes (>50kg) ocupan el día solos
        - Productos complejos (Vit C / Triactive) solo Lun o Mié
        - 2 producciones mismo día SOLO si:
            · Ambos ≤ 50kg
            · Ninguno es complejo
            · El producto entrante no es complejo
          Caso contrario, busca otro día.
        - Si hay alta necesidad y L/M/V están llenos, usa Mar/Jue
          (no fuerza espacios largos)
        """
        cur = fecha_inicio
        es_grande = lote_kg > LOTE_GRANDE_KG
        es_complejo = _es_producto_complejo(producto_nombre)

        for _ in range(400):
            if cur.weekday() in DIAS_HABILES and not es_festivo_colombia(cur):
                # Productos complejos: solo Lun o Mié (regla dura)
                if es_complejo and cur.weekday() not in {0, 2}:
                    cur = cur + _td(days=1)
                    continue

                # Datos del día · BD + slots in-memory
                db_rows = c.execute(
                    """SELECT COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0),
                              pp.producto
                       FROM produccion_programada pp
                       LEFT JOIN formula_headers fh
                         ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
                       WHERE date(pp.fecha_programada) = ?
                         AND pp.estado IN ('pendiente','programado','en_curso')""",
                    (cur.isoformat(),),
                ).fetchall()
                items_db = [{
                    "kg": float(r[0] or 0),
                    "complejo": _es_producto_complejo(r[1] or ""),
                } for r in db_rows]
                items_mem = detalle_por_fecha.get(cur.isoformat(), [])
                items_dia = items_db + items_mem

                count = len(items_dia)
                ya_grande = any(it["kg"] > LOTE_GRANDE_KG for it in items_dia)
                ya_complejo = any(it["complejo"] for it in items_dia)

                # Lote grande: solo si día vacío
                if es_grande:
                    if count == 0:
                        return cur
                    cur = cur + _td(days=1)
                    continue

                # Día con grande: rechaza cualquier otro
                if ya_grande:
                    cur = cur + _td(days=1)
                    continue

                # Día con complejo: NO permite 2 (error cero)
                if ya_complejo:
                    cur = cur + _td(days=1)
                    continue

                # Lote complejo entrante: día debe estar vacío (no comparte)
                if es_complejo and count > 0:
                    cur = cur + _td(days=1)
                    continue

                # Caso normal: lote pequeño/mediano no-complejo
                # Permite 2 SOLO si ambos ≤50kg Y ningún complejo (asegurado arriba)
                if count == 0:
                    return cur
                if count == 1 and not es_complejo and items_dia[0]["kg"] <= LOTE_GRANDE_KG:
                    return cur
                # Día lleno · siguiente
            cur = cur + _td(days=1)
        return None

    def _commit_slot(fecha_obj, producto_nombre, lote_kg):
        """Helper · actualiza tracking in-memory tras asignar slot."""
        iso = fecha_obj.isoformat()
        detalle_por_fecha.setdefault(iso, []).append({
            "kg": lote_kg,
            "complejo": _es_producto_complejo(producto_nombre),
        })

    # Ordenar por restricciones DESC + urgencia ASC · Sebastián 13-may-2026
    # "fechas estan raras salta mucho no tiene consistencia". Causa: si
    # asignábamos solo por urgencia, productos restrictivos (grandes,
    # complejos) llegaban tarde y eran forzados a saltar semanas porque
    # los días que podían usar ya estaban ocupados. Solución: asignar
    # primero los más restrictivos para que tomen sus huecos óptimos.
    # Orden: (complejos, grandes, medianos+pequeños) × urgencia ASC
    def _prioridad_asig(n):
        prod = n["producto_nombre"] or ""
        nombre_upper = prod.upper().strip()
        lote_kg = productos_con_formula.get(nombre_upper, 0)
        es_compl = _es_producto_complejo(prod)
        es_grande = lote_kg > LOTE_GRANDE_KG
        # Tier: 0=complejos (más restrictivos), 1=grandes, 2=otros
        tier = 0 if es_compl else (1 if es_grande else 2)
        cob = n["dias_cobertura"] if n["dias_cobertura"] is not None else 99999
        return (tier, cob)
    ordenadas = sorted(necesidades, key=_prioridad_asig)

    # Sumar pipeline reciente al stock para recalcular cobertura
    for nec in ordenadas:
        prod = nec["producto_nombre"]
        nombre_upper = prod.upper().strip()
        velocidad_kg_dia = nec["velocidad_kg_dia"] or 0

        # Pipeline reciente (suma kg producidos últ 7d)
        pipe_7d = sum(r["kg_real"] for r in reales_por_prod.get(prod, [])
                       if r["fin_real_at"] and (hoy - _date.fromisoformat(r["fin_real_at"])).days <= 30)

        stock_efectivo = (nec["stock_kg_gondola"] or 0) + pipe_7d
        if velocidad_kg_dia > 0.001:
            cob_dias = stock_efectivo / velocidad_kg_dia
        else:
            cob_dias = 99999

        # Sin ventas O cobertura > horizonte → no programar ahora
        if velocidad_kg_dia < 0.01 or cob_dias > horizonte_dias + 30:
            continue

        # Verificar fórmula en Excel
        if nombre_upper not in productos_con_formula:
            sin_formula.append({
                "producto": prod,
                "stock_kg": round(stock_efectivo, 2),
                "cob_dias": round(cob_dias, 1),
                "razon": "no_en_excel_mig_121",
            })
            continue

        lote_kg = productos_con_formula[nombre_upper]
        if lote_kg <= 0.01:
            # Productos con lote mini (0.1, 0.2) · sub-producción especial
            continue

        # Asignar slot
        fecha_asig = _registrar_slot_temporal(prod, lote_kg,
                                                f"cob {cob_dias:.0f}d")
        if fecha_asig is None:
            continue
        _commit_slot(fecha_asig, prod, lote_kg)

        slots.append({
            "fecha": fecha_asig.isoformat(),
            "producto": prod,
            "kg": lote_kg,
            "complejo": _es_producto_complejo(prod),
            "grande": lote_kg > LOTE_GRANDE_KG,
        })
        plan_items.append({
            "fecha": fecha_asig.isoformat(),
            "producto": prod,
            "kg": lote_kg,
            "cob_dias_actual": round(cob_dias, 1),
            "stock_efectivo_kg": round(stock_efectivo, 2),
            "pipeline_7d_kg": round(pipe_7d, 2),
            "motivo": "urgente" if cob_dias < 25 else ("adelanto" if cob_dias < 60 else "buffer"),
        })

    # Agrupar slots por fecha
    by_date = {}
    for s in slots:
        by_date.setdefault(s["fecha"], []).append(s)
    plan_por_dia = sorted([
        {"fecha": f, "productos": prods,
         "n_productos": len(prods),
         "total_kg": round(sum(p["kg"] for p in prods), 2)}
        for f, prods in by_date.items()
    ], key=lambda x: x["fecha"])

    # 5) Cancelables Calendar · todo Calendar/manual dentro del horizonte
    #    cuyo producto está cubierto >horizonte por las producciones reales
    fecha_hasta = (hoy + _td(days=horizonte_dias)).isoformat()
    cancelables = []
    for r in c.execute(
        """SELECT pp.id, pp.producto, pp.fecha_programada, pp.cantidad_kg
           FROM produccion_programada pp
           WHERE pp.origen IN ('calendar','manual')
             AND pp.estado IN ('pendiente','programado','en_curso')
             AND pp.fin_real_at IS NULL
             AND date(pp.fecha_programada) >= date('now', '-5 hours')
             AND date(pp.fecha_programada) <= date(?)""",
        (fecha_hasta,),
    ).fetchall():
        pid, prod, fecha, kg = r[0], r[1], r[2], r[3]
        # Si el producto YA está en mi plan nuevo, sugerir cancelar el Calendar
        en_plan_nuevo = any(s["producto"] == prod for s in slots)
        # O si tiene cobertura por producción reciente
        pipe = sum(rr["kg_real"] for rr in reales_por_prod.get(prod, []))
        nec_match = next((n for n in necesidades if n["producto_nombre"] == prod), None)
        vel = nec_match["velocidad_kg_dia"] if nec_match else 0
        stock_total = (nec_match["stock_kg_gondola"] if nec_match else 0) + pipe
        cob_post_real = stock_total / vel if vel > 0.001 else 99999
        razon = None
        if en_plan_nuevo:
            razon = "reemplazado_por_plan_eos"
        elif cob_post_real > horizonte_dias + 30:
            razon = f"cobertura_{int(cob_post_real)}d_con_pipeline"
        if razon:
            cancelables.append({
                "id": pid, "producto": prod, "fecha_programada": fecha,
                "cantidad_kg": kg, "razon": razon,
            })

    return jsonify({
        "horizonte_semanas": horizonte_semanas,
        "horizonte_dias": horizonte_dias,
        "fecha_inicio": fecha_inicio.isoformat(),
        "plan_por_dia": plan_por_dia,
        "plan_items": plan_items,
        "total_producciones": len(plan_items),
        "sin_formula": sin_formula,
        "cancelables_calendar": cancelables,
        "reglas_aplicadas": {
            "lote_grande_kg": LOTE_GRANDE_KG,
            "productos_complejos_substr": list(PRODUCTOS_COMPLEJOS_SUBSTR),
            "max_producciones_por_dia": MAX_PRODUCCIONES_POR_DIA,
            "dias_habiles": "Lun-Vie excluyendo festivos colombianos",
            "dias_preferidos": "Lun/Mié/Vie",
        },
    })


@bp.route("/admin/plan-sugerido", methods=["GET"])
def plan_sugerido_page():
    """Página admin · UI completa del plan sugerido automático."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/plan-sugerido")
    from flask import Response
    return Response(_PLAN_SUGERIDO_HTML, mimetype="text/html")


@bp.route("/admin/plan-calendario", methods=["GET"])
def plan_calendario_page():
    """Calendario propio · vista mes/semana de producciones programadas
    + sugerencias autoplan · reemplaza Google Calendar.

    Sebastián 14-may-2026: "queria que hubiera un autoplan que programe
    15 dias, 30 dias, 60 dias 90 dias y 120 dias automaticamente,
    que producciones hacer segun las necesidades, y que eos tenga como
    el calendario ya propuesto, y permita moverlo en caso tal, es como
    si existiera google calendar dentro pero autonomo".
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/plan-calendario")
    from flask import Response
    return Response(_PLAN_CALENDARIO_HTML, mimetype="text/html")


_PLAN_CALENDARIO_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>📅 Calendario EOS · Plan autónomo</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:18px}
.wrap{max-width:1500px;margin:0 auto}
.card{background:white;border-radius:12px;padding:16px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 4px;color:#0f766e;font-size:20px}
.muted{color:#64748b;font-size:12px}
button{background:#0f766e;color:white;border:none;padding:8px 14px;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;margin:2px}
button:hover{background:#0d635c}
button.secondary{background:#475569}
button.warn{background:#ca8a04}
button.success{background:#16a34a}
button.danger{background:#dc2626}
button:disabled{background:#94a3b8;cursor:not-allowed}
select,input{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px}
.horiz-btn{padding:10px 16px;border:2px solid #e2e8f0;background:white;color:#475569;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;margin:2px}
.horiz-btn.active{border-color:#0f766e;background:#0f766e;color:white}
.horiz-btn:hover{border-color:#0f766e}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-top:8px}
.cal-head{background:#f1f5f9;padding:8px;text-align:center;font-weight:800;color:#475569;font-size:12px;border-radius:6px}
.cal-day{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:6px;min-height:110px;position:relative;font-size:11px}
.cal-day.festivo{background:#fef2f2;border-color:#fca5a5}
.cal-day.weekend{background:#f8fafc;opacity:.7}
.cal-day.hoy{border:2px solid #0f766e;background:#f0fdfa}
.cal-day.suggest{background:linear-gradient(135deg,#f0fdfa,#ecfeff)}
.day-num{font-weight:800;color:#1e293b;font-size:13px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center}
.day-num .festivo-tag{font-size:9px;background:#fecaca;color:#7f1d1d;padding:1px 5px;border-radius:3px;font-weight:700}
.lote{background:#dbeafe;color:#1e40af;padding:3px 5px;border-radius:4px;margin-bottom:3px;font-size:10px;font-weight:600;cursor:pointer;border-left:3px solid #1e40af;display:flex;justify-content:space-between;align-items:center;gap:3px}
.lote:hover{background:#bfdbfe}
.lote.calendar{background:#fef9c3;border-left-color:#ca8a04;color:#854d0e}
.lote.eos_plan{background:#dcfce7;border-left-color:#16a34a;color:#166534}
.lote.eos_canonico{background:#e0e7ff;border-left-color:#6366f1;color:#3730a3}
.lote.esperando_recurso{background:#fde68a;border-left-color:#d97706;color:#78350f;opacity:.85}
.lote.sugerido{background:#fef3c7;border-left-color:#f59e0b;color:#92400e;border-style:dashed;border-width:1px}
.lote.grande{font-weight:800;border-left-width:4px}
.lote[draggable=true]{cursor:grab}
.lote[draggable=true]:active{cursor:grabbing}
.cal-day.drop-target{background:#dcfce7 !important;border:2px dashed #16a34a !important}
.cal-day.drop-invalid{background:#fee2e2 !important;border:2px dashed #dc2626 !important}
.modal-back{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.55);z-index:1000;justify-content:center;align-items:center;padding:20px;overflow-y:auto}
.modal-back.show{display:flex}
.modal-box{background:white;border-radius:14px;max-width:560px;width:100%;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.modal-head{background:linear-gradient(90deg,#0f766e,#0891b2);padding:14px 22px;border-radius:14px 14px 0 0;color:white;display:flex;justify-content:space-between;align-items:center}
.modal-body{padding:18px 22px}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.metric-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px}
.metric-lbl{font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:3px}
.metric-val{font-size:16px;font-weight:800;color:#1e293b}
.metric-sub{font-size:11px;color:#64748b;margin-top:2px}
.banner-inline{padding:10px 14px;border-radius:8px;margin:10px 0;font-size:12px;border-left:4px solid}
.banner-inline.ok{background:#dcfce7;border-color:#16a34a;color:#166534}
.banner-inline.warn{background:#fef3c7;border-color:#ca8a04;color:#854d0e}
.banner-inline.danger{background:#fee2e2;border-color:#dc2626;color:#991b1b}
.banner-inline.info{background:#dbeafe;border-color:#1e40af;color:#1e40af}
.lote-action{background:transparent;border:none;padding:0;color:inherit;cursor:pointer;font-size:10px;opacity:.6}
.lote-action:hover{opacity:1}
.kpi{display:inline-block;background:white;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;margin-right:8px;margin-bottom:6px;text-align:center;min-width:100px;vertical-align:top}
.kpi-lbl{font-size:10px;color:#64748b;text-transform:uppercase}
.kpi-val{font-size:20px;font-weight:800}
.legend{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:4px}
.legend-dot{width:10px;height:10px;border-radius:2px;display:inline-block}
.banner{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:12px}
.banner.success{background:#dcfce7;color:#166534;border:1px solid #86efac}
.banner.warn{background:#fef3c7;color:#854d0e;border:1px solid #fde68a}
.banner.info{background:#dbeafe;color:#1e40af;border:1px solid #bfdbfe}
.actions-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-top:10px}
.suggest-list{max-height:280px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px}
.suggest-row{padding:6px 10px;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;font-size:11px}
.suggest-row:hover{background:#f0fdfa}
.suggest-row .info{flex:1}
.suggest-row .actions{display:flex;gap:3px}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>📅 Calendario EOS · Plan autónomo</h1>
  <div class="muted">Calendario propio · reemplaza Google Calendar · genera autoplan según ventas Shopify + lote_size del Excel + reglas operativas (festivos · lun-vie · max 2/día · grandes solos · Vit C/Triactive lun-mié)</div>
  <div class="actions-bar" style="margin-top:10px">
    <div>
      <span class="muted" style="margin-right:8px">Horizonte autoplan:</span>
      <button class="horiz-btn" data-h="15" onclick="setHoriz(15)">15 días</button>
      <button class="horiz-btn active" data-h="30" onclick="setHoriz(30)">30 días</button>
      <button class="horiz-btn" data-h="60" onclick="setHoriz(60)">60 días</button>
      <button class="horiz-btn" data-h="90" onclick="setHoriz(90)">90 días</button>
      <button class="horiz-btn" data-h="120" onclick="setHoriz(120)">120 días</button>
    </div>
    <div>
      <button onclick="cargar()" class="secondary">↻ Recargar</button>
      <button onclick="autoplanIA()" class="warn" id="btn-ia">🤖 Autoplan con IA</button>
    </div>
  </div>
  <div id="ia-comentario" style="margin-top:10px"></div>
  <div id="kpis" style="margin-top:10px"></div>
</div>

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <button onclick="cambiarMes(-1)" class="secondary">← Anterior</button>
      <strong id="mesActual" style="font-size:16px;margin:0 10px;color:#1e293b">—</strong>
      <button onclick="cambiarMes(1)" class="secondary">Siguiente →</button>
      <button onclick="irHoy()" class="secondary">Hoy</button>
    </div>
    <div>
      <button onclick="confirmarAplicar()" class="success" id="btn-aplicar" disabled>✅ Confirmar y programar TODO</button>
    </div>
  </div>
  <div class="legend">
    <span><span class="legend-dot" style="background:#16a34a"></span>EOS Plan</span>
    <span><span class="legend-dot" style="background:#6366f1"></span>Canónico</span>
    <span><span class="legend-dot" style="background:#ca8a04"></span>Calendar legacy</span>
    <span><span class="legend-dot" style="background:#d97706"></span>⏸ Pausado</span>
    <span><span class="legend-dot" style="background:#f59e0b;opacity:.7"></span>✨ Sugerido (autoplan)</span>
    <span><span class="legend-dot" style="background:#fca5a5"></span>Festivo</span>
  </div>
  <div id="cal-grid-wrap"></div>
</div>

<div class="card">
  <h2 style="margin:0 0 8px;color:#475569;font-size:15px">📋 Lista del autoplan · ' + horizonte + ' días</h2>
  <div id="sugerencias-lista"></div>
</div>

<!-- Modal detalle lote · Sebastián 14-may-2026: "cuando le de al producto
     en calendario me abra, diga cuanto se vende al dia y al mes...
     tambien deberia poder mover el producto en el calendario asi como
     calendar permite mover eventos" -->
<div id="loteModal" class="modal-back" onclick="if(event.target===this)cerrarLoteModal()">
  <div class="modal-box">
    <div class="modal-head">
      <h3 id="lote-titulo" style="margin:0;font-size:16px;font-weight:800">Lote</h3>
      <button onclick="cerrarLoteModal()" style="background:transparent;border:none;color:white;font-size:22px;cursor:pointer;line-height:1">✕</button>
    </div>
    <div class="modal-body" id="lote-body"></div>
  </div>
</div>

</div>
<script>
let HORIZONTE = 30;
let MES_OFFSET = 0;  // 0 = mes actual · -1/+1 navegar
let PLAN_DATA = null;
const DIAS = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];
const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function getCSRF(){return document.cookie.split(';').find(c=>c.trim().startsWith('csrf_token='))?.split('=')[1] || '';}

function setHoriz(h){
  HORIZONTE = h;
  document.querySelectorAll('.horiz-btn').forEach(b => b.classList.toggle('active', parseInt(b.dataset.h) === h));
  cargar();
}

function cambiarMes(delta){ MES_OFFSET += delta; render(); }
function irHoy(){ MES_OFFSET = 0; render(); }

async function cargar(){
  document.getElementById('cal-grid-wrap').innerHTML = '<div class="muted" style="padding:30px;text-align:center">Generando autoplan…</div>';
  try {
    // Plan sugerido (lotes propuestos sin agendar todavía)
    const rPlan = await fetch('/api/plan/plan-sugerido?horizonte_dias=' + HORIZONTE);
    const dPlan = await rPlan.json();
    if (!rPlan.ok){ alert('Error plan: ' + (dPlan.error || rPlan.status)); return; }

    // Producciones ya agendadas (calendar/eos_plan/canonico/manual/esperando)
    const rAgendadas = await fetch('/api/programacion/produccion-programada/listado');
    const dAgendadas = await rAgendadas.json();
    if (!rAgendadas.ok){ alert('Error agendadas: ' + rAgendadas.status); return; }

    // Festivos colombianos del rango
    const year = new Date().getFullYear();
    const rFest = await fetch('/api/plan/festivos?year=' + year + ',' + (year + 1));
    const dFest = await rFest.json();
    const festivosSet = new Set();
    Object.values(dFest.festivos_por_year || {}).forEach(arr => arr.forEach(f => festivosSet.add(f.fecha)));

    PLAN_DATA = {plan: dPlan, agendadas: dAgendadas.producciones || [], festivos: festivosSet};
    document.getElementById('btn-aplicar').disabled = (dPlan.total_producciones || 0) === 0;
    render();
  } catch(e){ alert('Error: ' + e.message); }
}

function render(){
  if (!PLAN_DATA) return;

  // KPIs
  const k = PLAN_DATA.plan;
  let html = '';
  html += '<span class="kpi"><div class="kpi-lbl">📅 Sugeridas</div><div class="kpi-val" style="color:#16a34a">' + (k.total_producciones || 0) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">🗑 Cancelables</div><div class="kpi-val" style="color:#dc2626">' + ((k.cancelables_calendar || []).length) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">⚠ Sin fórmula</div><div class="kpi-val" style="color:#ca8a04">' + ((k.sin_formula || []).length) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">📅 Ya agendadas</div><div class="kpi-val" style="color:#475569">' + (PLAN_DATA.agendadas.length || 0) + '</div></span>';
  document.getElementById('kpis').innerHTML = html;

  // Calcular mes a mostrar
  const hoy = new Date();
  const ref = new Date(hoy.getFullYear(), hoy.getMonth() + MES_OFFSET, 1);
  document.getElementById('mesActual').textContent = MESES[ref.getMonth()] + ' ' + ref.getFullYear();

  // Agrupar lotes por fecha · ya agendadas
  const lotesPorFecha = {};
  PLAN_DATA.agendadas.forEach(ag => {
    const f = (ag.fecha_programada || '').slice(0, 10);
    if (!f) return;
    (lotesPorFecha[f] = lotesPorFecha[f] || []).push({
      tipo: 'agendado',
      id: ag.id,
      producto: ag.producto,
      kg: ag.kg || 0,
      estado: ag.estado,
      origen: ag.origen,
    });
  });
  // Lotes sugeridos del autoplan (no agendados aún)
  (k.plan_items || []).forEach(it => {
    const f = it.fecha;
    if (!f) return;
    (lotesPorFecha[f] = lotesPorFecha[f] || []).push({
      tipo: 'sugerido',
      producto: it.producto,
      kg: it.kg || 0,
      motivo: it.motivo,
      cob: it.cob_dias_actual,
    });
  });

  // Grid 6 semanas × 7 días · semana empieza lunes
  // Encontrar el lunes de la primera semana que contiene día 1
  const dia1 = new Date(ref.getFullYear(), ref.getMonth(), 1);
  const offsetLun = (dia1.getDay() + 6) % 7;  // 0=lun ... 6=dom
  const inicio = new Date(dia1);
  inicio.setDate(dia1.getDate() - offsetLun);
  const hoyStr = hoy.toISOString().slice(0, 10);

  let grid = '<div class="cal-grid">';
  DIAS.forEach(d => grid += '<div class="cal-head">' + d + '</div>');
  for (let sem = 0; sem < 6; sem++){
    for (let d = 0; d < 7; d++){
      const fecha = new Date(inicio);
      fecha.setDate(inicio.getDate() + sem * 7 + d);
      const fStr = fecha.toISOString().slice(0, 10);
      const isWeekend = d >= 5;
      const isFestivo = PLAN_DATA.festivos.has(fStr);
      const isHoy = fStr === hoyStr;
      const isOtroMes = fecha.getMonth() !== ref.getMonth();
      const lotes = lotesPorFecha[fStr] || [];

      let cls = 'cal-day';
      if (isHoy) cls += ' hoy';
      if (isFestivo) cls += ' festivo';
      if (isWeekend && !isFestivo) cls += ' weekend';
      if (lotes.some(l => l.tipo === 'sugerido')) cls += ' suggest';

      grid += '<div class="' + cls + '" data-date="' + fStr + '" data-weekend="' + (isWeekend ? '1':'0') + '" data-festivo="' + (isFestivo ? '1':'0') + '" style="' + (isOtroMes ? 'opacity:.4' : '') + '">';
      grid += '<div class="day-num"><span>' + fecha.getDate() + '</span>';
      if (isFestivo) grid += '<span class="festivo-tag">FEST</span>';
      grid += '</div>';

      lotes.forEach((lt, lotIdx) => {
        const ltCls = 'lote ' + (lt.tipo === 'sugerido' ? 'sugerido' : (lt.estado === 'esperando_recurso' ? 'esperando_recurso' : (lt.origen || 'eos_plan')));
        const esGrande = (lt.kg || 0) > 50 ? ' grande' : '';
        const prodCorto = (lt.producto || '').slice(0, 18);
        // Identificador único para localizar el lote en drop · sugeridos
        // usan sug:<idx> · agendados usan id:<id>
        const dragKey = lt.tipo === 'sugerido' ? 'sug:' + lotIdx + ':' + fStr : 'id:' + lt.id;
        if (lt.tipo === 'sugerido'){
          grid += '<div class="' + ltCls + esGrande + '" draggable="true" data-key="' + dragKey + '" data-prod="' + escapeHtml(lt.producto) + '" data-kg="' + lt.kg + '" data-from="' + fStr + '" ondragstart="onDragStart(event)" ondragend="onDragEnd(event)" title="' + escapeHtml(lt.producto + ' · ' + lt.kg + 'kg · arrastrá para mover') + '">';
          grid += '<span>✨ ' + escapeHtml(prodCorto) + '<br><span style="opacity:.7">' + lt.kg + 'kg</span></span>';
          grid += '</div>';
        } else {
          grid += '<div class="' + ltCls + esGrande + '" draggable="true" data-key="' + dragKey + '" data-prod="' + escapeHtml(lt.producto) + '" data-kg="' + lt.kg + '" data-from="' + fStr + '" ondragstart="onDragStart(event)" ondragend="onDragEnd(event)" onclick="abrirLoteModal(' + lt.id + ',&quot;' + escapeHtml(lt.producto) + '&quot;,&quot;' + fStr + '&quot;,' + lt.kg + ')" title="' + escapeHtml(lt.producto + ' · ' + lt.kg + 'kg · click detalle · arrastrá para mover') + '">';
          grid += '<span>' + escapeHtml(prodCorto) + '<br><span style="opacity:.7">' + lt.kg + 'kg</span></span>';
          grid += '</div>';
        }
      });

      grid += '</div>';
    }
  }
  grid += '</div>';

  document.getElementById('cal-grid-wrap').innerHTML = grid;
  // Activar drop en cada cal-day
  document.querySelectorAll('.cal-day').forEach(cell => {
    cell.addEventListener('dragover', onDragOver);
    cell.addEventListener('dragleave', onDragLeave);
    cell.addEventListener('drop', onDrop);
  });

  // Lista sugeridas con acciones
  renderListaSugerencias();
}

function renderListaSugerencias(){
  const items = (PLAN_DATA.plan.plan_items || []);
  if (!items.length){
    document.getElementById('sugerencias-lista').innerHTML = '<div class="muted" style="padding:20px;text-align:center">No hay sugerencias para este horizonte · todo cubierto</div>';
    return;
  }
  let html = '<div class="suggest-list">';
  items.sort((a, b) => (a.fecha || '').localeCompare(b.fecha || ''));
  items.forEach((it, i) => {
    const motivoColor = it.motivo === 'urgente' ? '#dc2626' : (it.motivo === 'adelanto' ? '#ca8a04' : '#475569');
    const iaTag = it.from_ia ? ' <span style="background:#fef3c7;color:#854d0e;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:700">🤖 IA' + (it.confianza ? ' ' + Math.round(it.confianza * 100) + '%' : '') + '</span>' : '';
    const razonTip = it.razonamiento_ia ? ' title="' + escapeHtml(it.razonamiento_ia) + '"' : '';
    html += '<div class="suggest-row"' + razonTip + '>';
    html += '<div class="info"><strong>' + escapeHtml(it.fecha) + '</strong> · ' + escapeHtml(it.producto) + ' · ' + it.kg + 'kg <span style="color:' + motivoColor + ';font-weight:700">[' + (it.motivo || '?') + ']</span> · cob ' + (it.cob_dias_actual || 0) + 'd' + iaTag + (it.razonamiento_ia ? '<div style="font-size:10px;color:#64748b;margin-top:2px">💭 ' + escapeHtml(it.razonamiento_ia.slice(0, 120)) + '</div>' : '') + '</div>';
    html += '<div class="actions">';
    html += '<button onclick="moverSugerencia(' + i + ')" class="secondary" style="padding:3px 8px;font-size:10px">📅</button>';
    html += '<button onclick="ignorarSugerencia(' + i + ')" class="danger" style="padding:3px 8px;font-size:10px">✕</button>';
    html += '</div>';
    html += '</div>';
  });
  html += '</div>';
  document.getElementById('sugerencias-lista').innerHTML = html;
}

function moverSugerencia(i){
  const it = PLAN_DATA.plan.plan_items[i];
  if (!it) return;
  const nueva = prompt('Mover sugerencia\\n\\n' + it.producto + '\\nFecha actual: ' + it.fecha + '\\n\\nNueva fecha (YYYY-MM-DD):', it.fecha);
  if (!nueva || nueva === it.fecha) return;
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(nueva.trim())){ alert('Formato inválido'); return; }
  const fechaPrev = it.fecha;
  it.fecha = nueva.trim();
  // Feedback IA · si era sugerencia IA, registra "movida"
  if (it.from_ia && it.decision_id){
    feedbackIA(it.decision_id, 'movida', it.kg, it.fecha, 'Movida de ' + fechaPrev);
  }
  render();
}

function ignorarSugerencia(i){
  if (!confirm('¿Descartar esta sugerencia del autoplan?')) return;
  const it = PLAN_DATA.plan.plan_items[i];
  if (it && it.from_ia && it.decision_id){
    feedbackIA(it.decision_id, 'ignorada', null, null, null);
  }
  PLAN_DATA.plan.plan_items.splice(i, 1);
  document.getElementById('btn-aplicar').disabled = PLAN_DATA.plan.plan_items.length === 0;
  render();
}

// ═══════ MODAL DETALLE LOTE ═══════
// Sebastián 14-may-2026: "cuando le de al producto en calendario me abra,
// diga cuanto se vende al dia y al mes, que diga esta menos tantos dias o
// esta bien calculado, que diga volumen del envase, kg para producir, y
// diga nueva produccion en tal fecha y que esta sea automatica la calcule
// segun los kilos programados"
function cerrarLoteModal(){
  document.getElementById('loteModal').classList.remove('show');
}

function buscarNecesidadProducto(producto){
  // Busca info de Necesidades sobre el producto · velocidad, ml, etc
  if (!PLAN_DATA || !PLAN_DATA.plan) return null;
  const ctx = (PLAN_DATA.plan.contexto_enviado && PLAN_DATA.plan.contexto_enviado.productos) || [];
  return ctx.find(p => (p.nombre || '').toUpperCase() === producto.toUpperCase()) || null;
}

// Normaliza · sin acentos · upper · trim · útil para matching de nombres
function _norm(s){
  return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().trim().replace(/\s+/g, ' ');
}

async function abrirLoteModal(id, producto, fecha, kg){
  document.getElementById('lote-titulo').textContent = '📅 ' + producto;
  document.getElementById('lote-body').innerHTML = '<div class="muted" style="padding:30px;text-align:center">Cargando datos del producto…</div>';
  document.getElementById('loteModal').classList.add('show');

  // Obtener datos del producto desde /api/plan/necesidades
  let info = null;
  let errFetch = '';
  try {
    const r = await fetch('/api/plan/necesidades');
    if (!r.ok){
      errFetch = 'Status ' + r.status + ' · ' + (await r.text()).slice(0, 200);
    } else {
      const d = await r.json();
      const animus = (d.clientes || []).find(c => c.cliente_id === 'ANIMUS_DTC');
      const todosProds = (animus && animus.productos) || [];
      const target = _norm(producto);
      // 1) match exacto normalizado
      info = todosProds.find(p => _norm(p.producto_nombre) === target);
      // 2) match parcial (uno contiene al otro) si no encontró
      if (!info){
        info = todosProds.find(p => {
          const n = _norm(p.producto_nombre);
          return n.includes(target) || target.includes(n);
        });
      }
    }
  } catch(e){ errFetch = e.message; }

  if (!info){
    // Sin datos · al menos mostrar acciones (no quedar colgado)
    let html = '<div class="banner-inline warn">⚠ Sin datos detallados (' + escapeHtml(producto) + ' no está en /necesidades' + (errFetch ? ' · ' + escapeHtml(errFetch) : '') + ')</div>';
    html += '<div class="metric-grid">';
    html += '<div class="metric-card"><div class="metric-lbl">Kg a producir</div><div class="metric-val">' + kg + ' kg</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Fecha programada</div><div class="metric-val">' + fecha + '</div></div>';
    html += '</div>';
    html += _renderAccionesLote(id, producto, fecha);
    document.getElementById('lote-body').innerHTML = html;
    return;
  }

  // Cálculos clave
  const ml = info.ml_unidad || 30;
  const velUds = info.velocidad_uds_dia || 0;
  const velMes = Math.round(velUds * 30);
  const stockUds = info.stock_uds_total || 0;
  const stockKg = info.stock_kg_total || 0;
  const diasCob = info.dias_cobertura;
  const velKgDia = info.velocidad_kg_dia || 0;

  // ¿Está bien calculado? · comparar fecha programada vs fecha-óptima (20d antes agotar)
  // fecha agotamiento aproximada · hoy + diasCob días
  // fecha óptima producción · agotamiento - 20d
  let diagFecha = null;
  let diagFechaTxt = '';
  if (diasCob != null && diasCob > 0){
    const hoy = new Date();
    const fAgot = new Date(hoy); fAgot.setDate(fAgot.getDate() + diasCob);
    const fOpt = new Date(fAgot); fOpt.setDate(fOpt.getDate() - 20);
    const fProg = new Date(fecha + 'T12:00:00');
    const diffDias = Math.round((fProg - fOpt) / 86400000);
    if (Math.abs(diffDias) <= 7){
      diagFecha = 'ok'; diagFechaTxt = '✅ Bien calculado · está dentro de ±7 días del óptimo';
    } else if (diffDias > 0){
      diagFecha = 'tarde'; diagFechaTxt = '⚠ TARDE · está ' + diffDias + ' días después del óptimo (stock se agota antes)';
    } else {
      diagFecha = 'temprano'; diagFechaTxt = '📌 TEMPRANO · está ' + Math.abs(diffDias) + ' días antes del óptimo (no urgente)';
    }
  }

  // Próxima producción sugerida según los kg programados ahora
  // kg programados / velKgDia = días que va a durar el lote
  let proximaSugerida = null;
  let proximaTxt = '';
  if (velKgDia > 0.001 && kg > 0){
    const diasDura = kg / velKgDia;
    const diasHastaProx = diasDura - 20;  // producir 20d antes de agotar el nuevo lote
    const fProx = new Date(fecha + 'T12:00:00');
    fProx.setDate(fProx.getDate() + Math.round(diasHastaProx));
    proximaSugerida = fProx.toISOString().slice(0, 10);
    proximaTxt = 'Este lote de ' + kg + 'kg durará ~' + Math.round(diasDura) + ' días al ritmo actual · próxima producción sugerida: <strong>' + proximaSugerida + '</strong>';
  }

  let html = '';

  // Sección 1: Datos de venta y stock
  html += '<div class="metric-grid">';
  html += '<div class="metric-card"><div class="metric-lbl">Volumen envase</div><div class="metric-val">' + ml + ' ml</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Kg a producir</div><div class="metric-val">' + kg + ' kg</div><div class="metric-sub">' + Math.round(kg * 1000 / ml) + ' uds aprox</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Vende/día</div><div class="metric-val">' + velUds.toFixed(1) + '</div><div class="metric-sub">' + velKgDia.toFixed(2) + ' kg/día</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Vende/mes</div><div class="metric-val">' + velMes + '</div><div class="metric-sub">' + (velKgDia * 30).toFixed(1) + ' kg/mes</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Stock actual</div><div class="metric-val">' + stockUds + ' uds</div><div class="metric-sub">' + stockKg.toFixed(1) + ' kg</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Cobertura</div><div class="metric-val">' + (diasCob != null ? diasCob + 'd' : '—') + '</div><div class="metric-sub">' + (info.urgencia || '') + '</div></div>';
  html += '</div>';

  // Sección 2: Diagnóstico fecha programada
  if (diagFechaTxt){
    const cls = diagFecha === 'ok' ? 'ok' : (diagFecha === 'tarde' ? 'danger' : 'info');
    html += '<div class="banner-inline ' + cls + '"><strong>Fecha programada: ' + fecha + '</strong><br>' + diagFechaTxt + '</div>';
  }

  // Sección 3: Próxima producción sugerida
  if (proximaTxt){
    html += '<div class="banner-inline ok">🔁 ' + proximaTxt + '</div>';
  }

  // Sección 4: Acciones
  html += _renderAccionesLote(id, producto, fecha);
  document.getElementById('lote-body').innerHTML = html;
}

function _renderAccionesLote(id, producto, fecha){
  let html = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:1px solid #e2e8f0">';
  html += '<button onclick="loteAccion(' + id + ',&quot;M&quot;,&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="secondary">📅 Mover fecha</button>';
  html += '<button onclick="loteAccion(' + id + ',&quot;P&quot;,&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="warn">⏸ Pausar</button>';
  html += '<button onclick="loteAccion(' + id + ',&quot;R&quot;,&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="success">▶ Reactivar</button>';
  html += '<button onclick="loteAccion(' + id + ',&quot;C&quot;,&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="danger">✕ Cancelar</button>';
  html += '<div style="flex-basis:100%;font-size:11px;color:#64748b;margin-top:6px">💡 También podés arrastrar el lote a otro día del calendario para moverlo</div>';
  html += '</div>';
  return html;
}

async function loteAccion(id, accion, producto, fecha){
  cerrarLoteModal();
  if (accion === 'M'){
    const nueva = prompt('Nueva fecha (YYYY-MM-DD):', fecha);
    if (!nueva) return;
    await reprogramarLote(id, nueva.trim(), 'manual_modal');
  } else if (accion === 'P'){
    const motivo = prompt('Motivo de pausa:', 'falta_mp');
    if (!motivo) return;
    const r = await fetch('/api/plan/proximas/' + id + '/pausar', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      body: JSON.stringify({motivo_pausa: motivo.trim()}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  } else if (accion === 'C'){
    if (!confirm('¿Cancelar lote?')) return;
    const r = await fetch('/api/plan/proximas/' + id, {
      method:'DELETE', headers:{'X-CSRF-Token':getCSRF()},
    });
    if (!r.ok){ const d = await r.json(); alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  } else if (accion === 'R'){
    const r = await fetch('/api/plan/proximas/' + id + '/reactivar', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      body: JSON.stringify({}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  }
}

async function reprogramarLote(id, nuevaFecha, razon){
  try {
    let r = await fetch('/api/plan/proximas/' + id + '/reprogramar', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({nueva_fecha: nuevaFecha, razon: razon || 'drag_calendario'}),
    });
    let txt = '';
    let d = null;
    try { d = await r.json(); } catch(e){ txt = await r.text(); }
    const errMsg = (d && (d.error || d.message)) || txt || ('HTTP ' + r.status);

    if (r.status === 422){
      if (confirm('⚠ ' + errMsg + '\\n\\n¿Forzar la reprogramación de todos modos?')){
        const r2 = await fetch('/api/plan/proximas/' + id + '/reprogramar', {
          method:'POST',
          headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
          credentials: 'same-origin',
          body: JSON.stringify({nueva_fecha: nuevaFecha, razon: razon || 'drag_calendario', skip_validacion_dia: true}),
        });
        let d2 = null; let txt2 = '';
        try { d2 = await r2.json(); } catch(e){ txt2 = await r2.text(); }
        if (!r2.ok){
          const errMsg2 = (d2 && (d2.error || d2.message)) || txt2 || ('HTTP ' + r2.status);
          alert('❌ No se pudo mover (forzado):\\n\\n' + errMsg2 +
                '\\n\\nStatus: ' + r2.status +
                (r2.status === 403 ? '\\n\\nProbable causa: MFA no activado. Ir a /seguridad para configurar.' : ''));
          return;
        }
      } else {
        return;  // usuario canceló
      }
    } else if (!r.ok){
      alert('❌ No se pudo mover:\\n\\n' + errMsg +
            '\\n\\nStatus: ' + r.status +
            (r.status === 403 ? '\\n\\nProbable causa: MFA no activado. Ir a /seguridad para configurar MFA.' :
             (r.status === 401 ? '\\n\\nProbable causa: sesión expirada. Recargá la página.' : '')));
      return;
    }
    cargar();
  } catch(e){
    alert('❌ Error de red: ' + e.message);
  }
}

// ═══════ DRAG & DROP ═══════
let _dragLote = null;

function onDragStart(ev){
  _dragLote = {
    key: ev.currentTarget.dataset.key,
    prod: ev.currentTarget.dataset.prod,
    kg: parseFloat(ev.currentTarget.dataset.kg),
    from: ev.currentTarget.dataset.from,
  };
  ev.currentTarget.style.opacity = '.4';
  ev.dataTransfer.effectAllowed = 'move';
}

function onDragEnd(ev){
  ev.currentTarget.style.opacity = '';
  document.querySelectorAll('.cal-day.drop-target, .cal-day.drop-invalid').forEach(el => {
    el.classList.remove('drop-target', 'drop-invalid');
  });
}

function onDragOver(ev){
  if (!_dragLote) return;
  const fecha = ev.currentTarget.dataset.date;
  if (!fecha || fecha === _dragLote.from) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = 'move';
  const isWE = ev.currentTarget.dataset.weekend === '1';
  const isFest = ev.currentTarget.dataset.festivo === '1';
  document.querySelectorAll('.cal-day.drop-target, .cal-day.drop-invalid').forEach(el => {
    el.classList.remove('drop-target', 'drop-invalid');
  });
  if (isWE || isFest){
    ev.currentTarget.classList.add('drop-invalid');
  } else {
    ev.currentTarget.classList.add('drop-target');
  }
}

function onDragLeave(ev){
  ev.currentTarget.classList.remove('drop-target', 'drop-invalid');
}

async function onDrop(ev){
  ev.preventDefault();
  ev.currentTarget.classList.remove('drop-target', 'drop-invalid');
  if (!_dragLote) return;
  const fechaNueva = ev.currentTarget.dataset.date;
  if (!fechaNueva || fechaNueva === _dragLote.from) { _dragLote = null; return; }
  const k = _dragLote.key;
  if (k.startsWith('sug:')){
    // Sugerencia del autoplan · solo modificar in-memory
    const parts = k.split(':');
    // Buscar el item correspondiente en plan_items
    const it = (PLAN_DATA.plan.plan_items || []).find(x => x.producto === _dragLote.prod && x.fecha === _dragLote.from);
    if (it){
      it.fecha = fechaNueva;
      if (it.from_ia && it.decision_id) feedbackIA(it.decision_id, 'movida', it.kg, fechaNueva, 'Drag desde ' + _dragLote.from);
    }
    _dragLote = null;
    render();
  } else if (k.startsWith('id:')){
    // Lote agendado real · llamar /reprogramar
    const id = parseInt(k.slice(3));
    _dragLote = null;
    await reprogramarLote(id, fechaNueva, 'drag_calendario');
  }
}

async function autoplanIA(){
  const btn = document.getElementById('btn-ia');
  btn.disabled = true;
  btn.textContent = '🤖 Consultando IA...';
  document.getElementById('ia-comentario').innerHTML = '<div class="banner info">⏳ La IA está analizando ventas, stock, MPs y feedback previo… esto toma ~15-30 segundos</div>';
  try {
    const r = await fetch('/api/plan/autoplan-ia', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      body: JSON.stringify({cliente:'ANIMUS_DTC', horizonte_dias: HORIZONTE, forzar_recalcular: true}),
    });
    const d = await r.json();
    if (!r.ok){
      document.getElementById('ia-comentario').innerHTML = '<div class="banner warn">⚠ ' + escapeHtml(d.error || 'Error IA') + (d.error && d.error.includes('ANTHROPIC_API_KEY') ? ' · Configurá la variable en Render → Environment.' : '') + '</div>';
      return;
    }
    // Inyectar las sugerencias IA en el plan
    if (PLAN_DATA && d.sugerencias && d.sugerencias.length){
      PLAN_DATA.plan.plan_items = d.sugerencias.map((s, i) => ({
        producto: s.producto, fecha: s.fecha, kg: s.kg,
        motivo: s.motivo, cob_dias_actual: s.cobertura_post_dias,
        razonamiento_ia: s.razonamiento, confianza: s.confianza,
        decision_id: (d.ids_decisiones || [])[i],
        from_ia: true,
      }));
      PLAN_DATA.plan.total_producciones = d.sugerencias.length;
      document.getElementById('btn-aplicar').disabled = false;
    }
    const cacheTag = d.cache_hit ? ' <span style="background:#dbeafe;color:#1e40af;padding:1px 5px;border-radius:3px;font-size:10px">cache 24h</span>' : '';
    document.getElementById('ia-comentario').innerHTML =
      '<div class="banner success">🤖 <strong>IA (' + escapeHtml(d.modelo_ia || '') + '):</strong> ' +
      escapeHtml(d.comentario_general || '(sin comentario)') + cacheTag +
      ' · ' + (d.sugerencias || []).length + ' sugerencias · aprendí de ' +
      (d.n_historial_aprendido || 0) + ' decisiones previas · ' +
      (d.tokens_usados || 0) + ' tokens</div>';
    render();
  } catch(e){
    document.getElementById('ia-comentario').innerHTML = '<div class="banner warn">⚠ Error: ' + escapeHtml(e.message) + '</div>';
  } finally {
    btn.disabled = false;
    btn.textContent = '🤖 Autoplan con IA';
  }
}

async function feedbackIA(decisionId, accion, kgReal, fechaReal, comentario){
  if (!decisionId) return;
  try {
    await fetch('/api/plan/autoplan-ia/feedback', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      body: JSON.stringify({
        decision_id: decisionId, accion: accion,
        kg_real: kgReal, fecha_real: fechaReal, comentario: comentario,
      }),
    });
  } catch(e){}  // silencioso · feedback es best-effort
}

async function confirmarAplicar(){
  const items = (PLAN_DATA.plan.plan_items || []);
  const cancelables = (PLAN_DATA.plan.cancelables_calendar || []).filter(c => c.razon === 'reemplazado_por_plan_eos');
  if (!items.length){ alert('Nada que aplicar'); return; }
  const msg = '¿Aplicar autoplan?\\n\\n' +
              '• ' + items.length + ' producciones nuevas se programarán\\n' +
              '• ' + cancelables.length + ' lotes Calendar legacy se cancelarán\\n\\n' +
              'Esto persiste en EOS · podés mover/cancelar después con click en cada lote.';
  if (!confirm(msg)) return;
  const payload = {
    programar: items.map(it => ({
      producto: it.producto, fecha: it.fecha, kg: it.kg, motivo: it.motivo
    })),
    cancelar_ids: cancelables.map(c => c.id),
    backfills: [],
  };
  try {
    const r = await fetch('/api/plan/plan-sugerido/ejecutar', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    // Feedback IA · marcá como aceptadas las que vinieron de IA
    items.forEach(it => {
      if (it.from_ia && it.decision_id){
        feedbackIA(it.decision_id, 'aceptada', it.kg, it.fecha, null);
      }
    });
    alert('✅ Aplicado\\n\\n• ' + d.programadas + ' programadas\\n• ' + d.canceladas + ' canceladas\\n• ' + d.total_errores + ' errores');
    cargar();
  } catch(e){ alert('Error: ' + e.message); }
}

cargar();
</script>
</body></html>"""


def _ia_autoplan_sugerir(payload_contexto, modelo="claude-haiku-4-5-20251001"):
    """Llama a Anthropic con el contexto · devuelve plan estructurado.

    payload_contexto debe incluir:
        cliente, productos[{nombre, ml_unidad, lote_size_kg, stock_kg,
          velocidad_uds_dia, velocidad_uds_mes, dias_cobertura, urgencia,
          mps_status, ultima_produccion_fecha, ultima_produccion_kg,
          producciones_recientes_30d (lista), ya_agendado[]}]
        horizonte_dias, reglas{festivos, lun_mie_vie, max_2_dia, ...}
        historial_decisiones · últimas 20 con accion_usuario para feedback

    Devuelve: lista de {producto, fecha, kg, motivo, confianza,
              cobertura_post_dias} ó None si falla.
    """
    import os, json as _json
    import urllib.request as _ureq
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        return None, "ANTHROPIC_API_KEY no configurada en Render"

    system_prompt = (
        "Eres el jefe de producción de un laboratorio cosmético colombiano. "
        "Tu trabajo es decidir QUÉ producir, CUÁNDO y CUÁNTO según las "
        "ventas reales y reglas operativas. Devolvés SOLO JSON válido sin "
        "explicaciones extras.\n\n"
        "REGLAS DURAS — ERROR CERO:\n"
        "1. NUNCA programar producciones esta semana (semana actual). "
        "Empezar siempre la PRÓXIMA semana en adelante.\n"
        "2. Producir 20 días antes de agotar (ideal 25d).\n"
        "3. Solo días hábiles (Lun-Vie) · NUNCA en sábado, domingo ni "
        "festivos colombianos.\n"
        "4. Si la necesidad es alta, podés usar TODA la semana L-V "
        "(no solo Lun/Mié/Vie). Una producción por día.\n"
        "5. DOS producciones el mismo día SOLO si: ambas ≤50kg Y "
        "ninguna es fórmula compleja. Si una es Vitamina C o Triactive "
        "(complejos · envasado mismo día), ese día queda con UNA SOLA.\n"
        "6. Lotes grandes (>50kg) ocupan el día ENTERO solos.\n"
        "7. Vitamina C y Triactive (cualquier variante) solo Lunes o "
        "Miércoles (necesitan envasado mismo día).\n"
        "8. Si las MPs faltan (mps_status=FALTAN_MPS): NO programar · "
        "comentar que primero hay que comprar MPs.\n"
        "9. Si el producto ya tiene un lote agendado en el horizonte, "
        "NO duplicar.\n"
        "10. Aprender del historial: si el usuario movió/canceló "
        "sugerencias previas, ajustar criterio (frecuencia, fecha o kg).\n"
        "11. Distribuir parejo: no concentrar 3+ productos un mismo día. "
        "Si la lista de urgencias es larga, distribuir a lo largo de "
        "varias semanas (L-V), una/dos por día según las reglas.\n\n"
        "FORMATO RESPUESTA (JSON estricto):\n"
        "{\"sugerencias\":[{\"producto\":\"...\",\"fecha\":\"YYYY-MM-DD\","
        "\"kg\":N,\"motivo\":\"urgente|adelanto|buffer\","
        "\"cobertura_post_dias\":N,\"confianza\":0.0-1.0,"
        "\"razonamiento\":\"...\"}],\"comentario_general\":\"...\"}"
    )
    user_msg = (
        f"Contexto del cliente y productos:\n"
        f"{_json.dumps(payload_contexto, ensure_ascii=False, default=str)[:8000]}\n\n"
        f"Generá el autoplan para horizonte {payload_contexto.get('horizonte_dias', 30)} días. "
        f"Devolvé SOLO JSON."
    )

    body = _json.dumps({
        "model": modelo,
        "max_tokens": 2500,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_msg}],
    }).encode("utf-8")
    req = _ureq.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with _ureq.urlopen(req, timeout=45) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as ex:
        return None, f"Error llamando Anthropic: {ex}"

    try:
        text = data["content"][0]["text"]
        # IA a veces devuelve con ```json
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = _json.loads(text.strip())
    except Exception as ex:
        return None, f"Respuesta IA no parseable: {ex} · raw: {data}"

    tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
    return {"sugerencias": parsed.get("sugerencias", []),
            "comentario": parsed.get("comentario_general", ""),
            "tokens": tokens, "modelo": modelo}, None


@bp.route("/api/plan/autoplan-ia", methods=["POST"])
def autoplan_ia():
    """Autoplan inteligente con Anthropic · aprende del feedback histórico.

    Sebastián 14-may-2026: "tenemos clientes, eso son necesidades, ellos
    cargan sus necesidades el ejemplo de animus lab es que sale de shopy
    pero no hay una sugerencia de produccion para que sepamos que se debe
    producir, podemos usar api kay de antropic para que lo haga, ya
    sabemos las necesidades hay que ponerle reglas, exportan el tamaño
    del producto, cuanto se vende al mes, y ver si se hace para 30 dias
    60 o 90 asi va aprendiendo".

    Body:
        cliente: str (default "ANIMUS_DTC")
        horizonte_dias: int (15/30/60/90/120 default 30)
        forzar_recalcular: bool (si False y hay decisión <24h vieja, devuelve cache)

    Returns:
        sugerencias[]: cada una con razonamiento de la IA y confianza
        comentario_general: insight global del jefe de producción IA
        contexto_enviado: para auditar qué leyó la IA
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    cliente = (body.get("cliente") or "ANIMUS_DTC").strip()
    try:
        horizonte = max(7, min(180, int(body.get("horizonte_dias") or 30)))
    except (ValueError, TypeError):
        horizonte = 30
    forzar = bool(body.get("forzar_recalcular"))

    conn = get_db()
    c = conn.cursor()

    # 1) Cache 24h · evita gastar tokens si nada cambió
    if not forzar:
        cache_row = c.execute(
            f"""SELECT payload_completo, fecha_decision FROM autoplan_decisiones
                WHERE cliente = ? AND horizonte_dias = ?
                  AND accion_usuario IS NULL
                  AND datetime(fecha_decision) >= datetime('now','-5 hours','-1 day')
                ORDER BY fecha_decision DESC LIMIT 1""",
            (cliente, horizonte),
        ).fetchone()
        if cache_row and cache_row[0]:
            try:
                import json as _json
                cached = _json.loads(cache_row[0])
                cached["cache_hit"] = True
                cached["cache_fecha"] = cache_row[1]
                return jsonify(cached)
            except Exception:
                pass  # cache corrupto · ignorar y recalcular

    # 2) Construir contexto · solo Animus DTC por ahora (Fernando B2B después)
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)

    # Filtrar a productos relevantes · con velocidad real Y fórmula
    productos_ctx = []
    for n in necesidades:
        if (n.get("velocidad_uds_dia") or 0) < 0.1:
            continue  # sin ventas, no programar
        if n.get("mps_status") == "SIN_FORMULA":
            continue
        productos_ctx.append({
            "nombre": n["producto_nombre"],
            "codigo_pt": n.get("codigo_pt", ""),
            "ml_unidad": n.get("ml_unidad", 30),
            "lote_size_kg": n.get("lote_bulk_kg", 0),
            "stock_uds": n.get("stock_uds_total", 0),
            "stock_kg": n.get("stock_kg_total", 0),
            "velocidad_uds_dia": round(n.get("velocidad_uds_dia", 0), 2),
            "velocidad_uds_mes": int((n.get("velocidad_uds_dia", 0) or 0) * 30),
            "velocidad_kg_dia": round(n.get("velocidad_kg_dia", 0), 3),
            "dias_cobertura": n.get("dias_cobertura"),
            "urgencia": n.get("urgencia"),
            "mps_status": n.get("mps_status"),
            "mps_n_faltantes": n.get("mps_n_faltantes", 0),
            "ultima_produccion_fecha": n.get("ultima_produccion_fecha"),
            "ultima_produccion_kg": n.get("ultima_produccion_kg"),
            "dias_desde_ultima": n.get("dias_desde_ultima"),
            "lotes_agendados": [{
                "fecha": a["fecha"], "kg": a["kg"], "estado": a["estado"]
            } for a in (n.get("planificacion") or [])][:5],
        })

    # 3) Historial reciente para feedback · últimas 20 decisiones
    historial_rows = c.execute(
        """SELECT producto_nombre, sugerencia_kg, sugerencia_fecha,
                  motivo_ia, accion_usuario, kg_real, fecha_real,
                  comentario_usuario
           FROM autoplan_decisiones
           WHERE cliente = ?
             AND accion_usuario IS NOT NULL
           ORDER BY accion_at DESC LIMIT 20""",
        (cliente,),
    ).fetchall()
    historial = [{
        "producto": r[0],
        "sugerencia_kg": r[1],
        "sugerencia_fecha": r[2],
        "motivo": r[3],
        "accion": r[4],         # 'aceptada' / 'movida' / 'cancelada' / 'ignorada'
        "kg_real": r[5],
        "fecha_real": r[6],
        "comentario": r[7],
    } for r in historial_rows]

    # 4) Reglas resumidas para la IA
    from datetime import timedelta as _td_ia
    hoy_dt = _hoy_colombia()
    dias_a_lunes = (7 - hoy_dt.weekday()) % 7
    if dias_a_lunes == 0:
        dias_a_lunes = 7
    fecha_inicio_minima = (hoy_dt + _td_ia(days=dias_a_lunes)).isoformat()

    # Festivos colombianos del horizonte para que la IA los vea explícitos
    festivos_horizonte = []
    for offset in range(horizonte + dias_a_lunes + 7):
        d = hoy_dt + _td_ia(days=offset)
        if es_festivo_colombia(d):
            festivos_horizonte.append(d.isoformat())

    reglas = {
        "fecha_inicio_minima": fecha_inicio_minima,
        "regla_inicio": "NO programar esta semana · empezar el " + fecha_inicio_minima + " (próximo lunes)",
        "producir_dias_antes_agotar": 20,
        "ideal_dias_antes": 25,
        "dias_habiles": "Lun-Vie",
        "dias_uso_completo": "Si necesidad alta, usar L-V completo (no solo L/M/V)",
        "max_producciones_por_dia": MAX_PRODUCCIONES_POR_DIA,
        "regla_2_por_dia": "Solo si ambos ≤50kg Y ninguno es complejo · si hay complejo, queda con UNO",
        "lote_grande_umbral_kg": LOTE_GRANDE_KG,
        "lote_grande_regla": "Día entero solo · no comparte",
        "productos_complejos": list(PRODUCTOS_COMPLEJOS_SUBSTR),
        "productos_complejos_regla": "Solo Lun o Mié (envasado mismo día) + queda con UNA producción ese día",
        "festivos_colombianos": festivos_horizonte,
        "festivos_skip": True,
        "no_duplicar_si_ya_agendado": True,
        "horizontes_validos": [15, 30, 60, 90, 120],
        "principio": "ERROR CERO · prefiere distribuir a lo largo de la semana",
    }

    payload_contexto = {
        "cliente": cliente,
        "horizonte_dias": horizonte,
        "fecha_hoy": _hoy_colombia().isoformat(),
        "fecha_inicio_minima_plan": fecha_inicio_minima,
        "n_productos": len(productos_ctx),
        "productos": productos_ctx,
        "historial_feedback": historial,
        "reglas_operativas": reglas,
    }

    # 5) Llamar IA
    resultado, err_msg = _ia_autoplan_sugerir(payload_contexto)
    if not resultado:
        return jsonify({"error": err_msg or "Error llamando IA",
                        "contexto_enviado": payload_contexto}), 502

    # 6) Persistir cada sugerencia en autoplan_decisiones
    fecha_dec = _now_colombia().isoformat()
    ids_creados = []
    import json as _json
    payload_str = _json.dumps({
        "sugerencias": resultado["sugerencias"],
        "comentario": resultado["comentario"],
        "modelo": resultado["modelo"],
        "tokens": resultado["tokens"],
        "horizonte_dias": horizonte,
    }, ensure_ascii=False)

    for s in resultado["sugerencias"]:
        prod_nom = (s.get("producto") or "").strip()
        if not prod_nom:
            continue
        prod_ctx = next((p for p in productos_ctx if p["nombre"].upper() == prod_nom.upper()), None)
        cur = c.execute(
            f"""INSERT INTO autoplan_decisiones
                (cliente, producto_nombre, fecha_decision, horizonte_dias,
                 stock_kg, velocidad_uds_mes, ml_unidad, lote_size_kg,
                 sugerencia_kg, sugerencia_fecha, sugerencia_cobertura_dias,
                 motivo_ia, usuario, modelo_ia, tokens_usados, confianza_ia,
                 payload_completo)
                VALUES (?,?,{SQLITE_NOW_COL},?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cliente, prod_nom, horizonte,
             prod_ctx.get("stock_kg") if prod_ctx else None,
             prod_ctx.get("velocidad_uds_mes") if prod_ctx else None,
             prod_ctx.get("ml_unidad") if prod_ctx else None,
             prod_ctx.get("lote_size_kg") if prod_ctx else None,
             s.get("kg"), s.get("fecha"), s.get("cobertura_post_dias"),
             s.get("motivo"), user, resultado["modelo"], resultado["tokens"],
             s.get("confianza"), payload_str),
        )
        ids_creados.append(cur.lastrowid)
    conn.commit()

    return jsonify({
        "cliente": cliente,
        "horizonte_dias": horizonte,
        "fecha_generacion": fecha_dec,
        "modelo_ia": resultado["modelo"],
        "tokens_usados": resultado["tokens"],
        "sugerencias": resultado["sugerencias"],
        "comentario_general": resultado["comentario"],
        "ids_decisiones": ids_creados,
        "contexto_enviado": payload_contexto,
        "n_historial_aprendido": len(historial),
        "cache_hit": False,
    })


@bp.route("/api/plan/autoplan-ia/feedback", methods=["POST"])
def autoplan_ia_feedback():
    """Registra la acción del usuario sobre una sugerencia IA · para
    que el siguiente autoplan aprenda.

    Body:
        decision_id: int (del autoplan_decisiones)
        accion: str · 'aceptada' / 'movida' / 'cancelada' / 'ignorada'
        kg_real: float (opcional · si movió cantidad)
        fecha_real: str YYYY-MM-DD (opcional · si movió fecha)
        comentario: str (opcional · ej: "muy temprano · prefiero al final mes")
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    try:
        decision_id = int(body.get("decision_id") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "decision_id inválido"}), 400
    accion = (body.get("accion") or "").strip()
    if accion not in ("aceptada", "movida", "cancelada", "ignorada"):
        return jsonify({"error": "accion debe ser aceptada/movida/cancelada/ignorada"}), 400

    conn = get_db()
    c = conn.cursor()
    existing = c.execute(
        "SELECT id, producto_nombre FROM autoplan_decisiones WHERE id = ?",
        (decision_id,),
    ).fetchone()
    if not existing:
        return jsonify({"error": "decision_id no encontrado"}), 404

    c.execute(
        f"""UPDATE autoplan_decisiones
            SET accion_usuario = ?, accion_at = {SQLITE_NOW_COL},
                kg_real = ?, fecha_real = ?, comentario_usuario = ?
            WHERE id = ?""",
        (accion, body.get("kg_real"), body.get("fecha_real"),
         body.get("comentario"), decision_id),
    )
    conn.commit()
    audit_log(c, usuario=user, accion="AUTOPLAN_IA_FEEDBACK",
              tabla="autoplan_decisiones", registro_id=decision_id,
              antes={"producto": existing[1]},
              despues={"accion": accion, "comentario": body.get("comentario")})
    conn.commit()
    return jsonify({"ok": True, "decision_id": decision_id, "accion": accion})


@bp.route("/api/plan/plan-sugerido/ejecutar", methods=["POST"])
def plan_sugerido_ejecutar():
    """Aplica acciones del plan sugerido en lote.

    Sebastián 13-may-2026: "si armaloi". Batch endpoint para programar
    el plan completo + cancelar Calendar legacy + back-fill producciones
    reales pasadas. Cada acción es independiente · si falla una, las
    demás siguen.

    Body JSON:
        programar: [{producto, fecha, kg, motivo?}, ...]
        cancelar_ids: [int, ...] · ids de produccion_programada a cancelar
        backfills: [{producto, kg, fecha}, ...] · registros retroactivos

    Returns:
        programadas: count + lista de IDs creados
        canceladas: count + lista de IDs afectados
        backfills_creados: count + lista
        errores: [{accion, indice, error}, ...]
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    programar = body.get("programar") or []
    cancelar_ids = body.get("cancelar_ids") or []
    backfills = body.get("backfills") or []

    if not isinstance(programar, list) or not isinstance(cancelar_ids, list) or not isinstance(backfills, list):
        return jsonify({"error": "campos deben ser listas"}), 400

    conn = get_db()
    c = conn.cursor()
    from datetime import date as _date, timedelta as _td

    programadas_ids = []
    canceladas_ids = []
    backfills_ids = []
    errores = []

    # 1) PROGRAMAR · producciones futuras
    for i, item in enumerate(programar):
        try:
            prod = (item.get("producto") or "").strip()
            fecha = (item.get("fecha") or "").strip()
            kg = float(item.get("kg") or 0)
            motivo = (item.get("motivo") or "eos_plan").strip()
            if not prod or not fecha or kg <= 0:
                errores.append({"accion": "programar", "indice": i,
                                "error": "producto/fecha/kg requeridos"})
                continue
            if not _valida_fecha_iso(fecha):
                errores.append({"accion": "programar", "indice": i,
                                "error": "fecha formato YYYY-MM-DD"})
                continue
            # Verificar producto existe en formula_headers
            hdr = c.execute(
                """SELECT producto_nombre FROM formula_headers
                   WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
                (prod,),
            ).fetchone()
            if not hdr:
                errores.append({"accion": "programar", "indice": i,
                                "error": f"producto sin fórmula: {prod}"})
                continue
            producto_canonico = hdr[0]
            # INSERT produccion_programada
            c.execute(
                """INSERT INTO produccion_programada
                       (producto, fecha_programada, cantidad_kg, estado,
                        origen, observaciones, lotes)
                   VALUES (?, ?, ?, 'programado', 'eos_plan', ?, 1)""",
                (producto_canonico, fecha, kg,
                 f"Plan auto · motivo: {motivo} · usuario: {user}"),
            )
            new_id = c.lastrowid
            programadas_ids.append({"id": new_id, "producto": producto_canonico,
                                     "fecha": fecha, "kg": kg})
            # Audit
            try:
                c.execute(
                    """INSERT INTO audit_log
                           (fecha, usuario, accion, tabla, registro_id, detalle)
                       VALUES (datetime('now', '-5 hours'), ?, 'PLAN_SUGERIDO_PROGRAMAR',
                               'produccion_programada', ?, ?)""",
                    (user, str(new_id),
                     f"producto={producto_canonico} fecha={fecha} kg={kg}"),
                )
            except Exception:
                pass
        except Exception as ex:
            errores.append({"accion": "programar", "indice": i, "error": str(ex)})

    # 2) CANCELAR · soft-cancel de Calendar legacy
    for i, pid in enumerate(cancelar_ids):
        try:
            pid_int = int(pid)
            row = c.execute(
                """SELECT producto, fecha_programada, origen, estado, fin_real_at
                   FROM produccion_programada WHERE id = ?""",
                (pid_int,),
            ).fetchone()
            if not row:
                errores.append({"accion": "cancelar", "indice": i,
                                "error": f"id no encontrado: {pid_int}"})
                continue
            if row[4]:  # fin_real_at
                errores.append({"accion": "cancelar", "indice": i,
                                "error": f"id {pid_int} ya tiene fin_real_at · no cancelable"})
                continue
            c.execute(
                """UPDATE produccion_programada
                   SET estado = 'cancelado',
                       observaciones = COALESCE(observaciones,'') ||
                           ' · CANCELADO por plan-sugerido · ' || datetime('now', '-5 hours')
                   WHERE id = ?""",
                (pid_int,),
            )
            canceladas_ids.append({"id": pid_int, "producto": row[0],
                                     "fecha_programada": row[1], "origen": row[2]})
            try:
                c.execute(
                    """INSERT INTO audit_log
                           (fecha, usuario, accion, tabla, registro_id, detalle)
                       VALUES (datetime('now', '-5 hours'), ?, 'PLAN_SUGERIDO_CANCELAR',
                               'produccion_programada', ?, ?)""",
                    (user, str(pid_int),
                     f"producto={row[0]} fecha={row[1]} origen={row[2]}"),
                )
            except Exception:
                pass
        except Exception as ex:
            errores.append({"accion": "cancelar", "indice": i, "error": str(ex)})

    # 3) BACKFILLS · producciones pasadas completadas
    for i, bf in enumerate(backfills):
        try:
            prod = (bf.get("producto") or "").strip()
            kg = float(bf.get("kg") or 0)
            fecha = (bf.get("fecha") or "").strip()
            if not prod or kg <= 0 or not fecha or not _valida_fecha_iso(fecha):
                errores.append({"accion": "backfill", "indice": i,
                                "error": "producto/kg/fecha YYYY-MM-DD requeridos"})
                continue
            # Verificar producto existe en formula_headers
            hdr = c.execute(
                """SELECT producto_nombre, lote_size_kg FROM formula_headers
                   WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
                (prod,),
            ).fetchone()
            if not hdr:
                errores.append({"accion": "backfill", "indice": i,
                                "error": f"producto sin fórmula: {prod}"})
                continue
            producto_canonico = hdr[0]
            lote_size = float(hdr[1] or kg)
            # Idempotencia: si ya existe un registro con mismo producto+fecha+kg ±5%
            # con origen='eos_retroactivo' · no duplicar
            dup = c.execute(
                """SELECT id FROM produccion_programada
                   WHERE producto = ?
                     AND date(fin_real_at) = ?
                     AND ABS(COALESCE(kg_real, cantidad_kg, 0) - ?) < ?
                     AND origen = 'eos_retroactivo'""",
                (producto_canonico, fecha, kg, max(kg * 0.05, 0.5)),
            ).fetchone()
            if dup:
                errores.append({"accion": "backfill", "indice": i,
                                "error": f"duplicado · id existente {dup[0]}"})
                continue
            # INSERT retroactivo
            c.execute(
                """INSERT INTO produccion_programada
                       (producto, fecha_programada, cantidad_kg, kg_real,
                        estado, origen, fin_real_at, lotes, observaciones)
                   VALUES (?, ?, ?, ?, 'completado', 'eos_retroactivo',
                           ? || ' 00:00:00', 1, ?)""",
                (producto_canonico, fecha, lote_size, kg, fecha,
                 f"Back-fill por plan-sugerido · usuario: {user}"),
            )
            new_id = c.lastrowid
            backfills_ids.append({"id": new_id, "producto": producto_canonico,
                                    "fecha": fecha, "kg_real": kg})
            try:
                c.execute(
                    """INSERT INTO audit_log
                           (fecha, usuario, accion, tabla, registro_id, detalle)
                       VALUES (datetime('now', '-5 hours'), ?, 'PLAN_SUGERIDO_BACKFILL',
                               'produccion_programada', ?, ?)""",
                    (user, str(new_id),
                     f"producto={producto_canonico} fecha={fecha} kg={kg}"),
                )
            except Exception:
                pass
        except Exception as ex:
            errores.append({"accion": "backfill", "indice": i, "error": str(ex)})

    conn.commit()

    return jsonify({
        "programadas": len(programadas_ids),
        "programadas_ids": programadas_ids,
        "canceladas": len(canceladas_ids),
        "canceladas_ids": canceladas_ids,
        "backfills_creados": len(backfills_ids),
        "backfills_ids": backfills_ids,
        "errores": errores,
        "total_errores": len(errores),
    }), 200


_PLAN_SUGERIDO_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Plan sugerido · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1400px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
h2{margin:0 0 12px;color:#1e293b;font-size:18px}
h3{margin:14px 0 8px;color:#475569;font-size:14px}
.muted{color:#64748b;font-size:13px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;margin:4px}
button:hover{background:#0d635c}
button.danger{background:#dc2626}
button.danger:hover{background:#b91c1c}
button.warn{background:#ca8a04}
button.warn:hover{background:#a16207}
button:disabled{background:#94a3b8;cursor:not-allowed}
input[type="number"],input[type="date"],input[type="text"]{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px}
textarea{padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;font-family:ui-monospace,SFMono-Regular,monospace;width:100%;min-height:140px;resize:vertical}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:7px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700}
.tag-urgente{background:#fee2e2;color:#991b1b}
.tag-adelanto{background:#fef3c7;color:#854d0e}
.tag-buffer{background:#dbeafe;color:#1e40af}
.tag-grande{background:#fecaca;color:#7f1d1d}
.tag-complejo{background:#e9d5ff;color:#581c87}
.tag-sin-formula{background:#f1f5f9;color:#64748b}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;color:#1e40af}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;margin-bottom:8px;text-align:center;min-width:130px;vertical-align:top}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:22px;font-weight:800}
.section{border-left:4px solid #0f766e;padding:12px 16px;background:#f0fdfa;border-radius:6px;margin-bottom:14px}
.section.danger{border-color:#dc2626;background:#fef2f2}
.section.warn{border-color:#ca8a04;background:#fefce8}
.section.muted{border-color:#94a3b8;background:#f8fafc}
.bigbtn{font-size:15px;padding:14px 28px;width:auto}
.resultado{font-size:12px;background:#f0fdf4;border:1px solid #86efac;border-radius:6px;padding:10px;margin-top:10px}
.resultado.error{background:#fef2f2;border-color:#fca5a5}
input[type="checkbox"]{transform:scale(1.2);margin-right:6px}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver al panel</a>
<div class="card">
  <h1>⚙ Plan sugerido · EOS automático</h1>
  <div class="muted">Genera plan completo aplicando reglas operativas + festivos colombianos + fórmulas del Excel (mig 121). Read-only hasta que apretes "Aplicar".</div>
  <div style="margin-top:14px">
    Horizonte:
    <select id="hz">
      <option value="2">2 semanas</option>
      <option value="4" selected>4 semanas</option>
      <option value="6">6 semanas</option>
      <option value="8">8 semanas</option>
    </select>
    <button onclick="cargar()">▶ Generar plan</button>
  </div>
  <div id="reglas" class="muted" style="margin-top:10px;font-size:11px"></div>
</div>
<div id="kpis"></div>
<div id="contenido"></div>

<div class="card" style="background:#fff7ed;border:2px solid #f97316">
  <h2 style="color:#9a3412">📥 Back-fill producciones reales pasadas</h2>
  <div class="muted">Pegá las producciones completadas que NO están en el sistema con <code>fin_real_at</code>. Formato por línea: <code>NOMBRE_PRODUCTO | kg | YYYY-MM-DD</code></div>
  <textarea id="backfill_txt" placeholder="SUERO HIDRATANTE AH 1.5% | 90 | 2026-04-30
LIMPIADOR ILUMINADOR ACIDO KOJICO | 40 | 2026-04-15
LIMPIADOR FACIAL BHA 2% | 150 | 2026-04-28"></textarea>
  <div style="margin-top:10px" class="muted">El sistema mapeará el nombre al canónico del Excel · si no existe, lo reporta como error.</div>
</div>

<div class="card" style="background:#f0fdf4;border:2px solid #16a34a">
  <h2 style="color:#166534">🚀 Aplicar acciones seleccionadas</h2>
  <div class="muted">Esta acción es <strong>idempotente</strong>: cada acción se intenta independientemente · errores no detienen el batch. Audit_log registra todo.</div>
  <div style="margin-top:14px">
    <button class="bigbtn" onclick="aplicarTodo()">✅ Aplicar TODO (programar + cancelar + back-fill)</button>
    <button class="bigbtn warn" onclick="aplicarSeleccion()">⚙ Aplicar solo seleccionados</button>
  </div>
  <div id="resultado_ejecucion"></div>
</div>

</div>
<script>
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function getCSRF(){
  return document.cookie.split(';').find(c=>c.trim().startsWith('csrf_token='))?.split('=')[1] || '';
}

const DIAS_ES = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];

async function cargar(){
  document.getElementById('contenido').innerHTML = '<div class="card">Analizando…</div>';
  document.getElementById('kpis').innerHTML = '';
  document.getElementById('reglas').innerHTML = '';
  var hz = document.getElementById('hz').value;
  try {
    var r = await fetch('/api/plan/plan-sugerido?horizonte_semanas=' + hz);
    var d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error||r.status)); return; }
    window._plan = d;
    render(d);
  } catch(e){ alert('Error: ' + e.message); }
}

function render(d){
  // KPIs
  var k = '';
  k += '<span class="kpi"><div class="kpi-lbl">📅 Producciones</div><div class="kpi-val">' + d.total_producciones + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">🗑 Cancelables Calendar</div><div class="kpi-val">' + (d.cancelables_calendar||[]).length + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">⚠ Sin fórmula</div><div class="kpi-val">' + (d.sin_formula||[]).length + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">📆 Días útiles</div><div class="kpi-val">' + (d.plan_por_dia||[]).length + '</div></span>';
  document.getElementById('kpis').innerHTML = '<div class="card">' + k + '</div>';

  var rg = d.reglas_aplicadas || {};
  document.getElementById('reglas').innerHTML =
    '📌 Reglas: lote grande >' + rg.lote_grande_kg + 'kg = 1/día · ' +
    'complejos (' + (rg.productos_complejos_substr||[]).join(', ') + ') = Lun/Mié · ' +
    'max ' + rg.max_producciones_por_dia + ' por día';

  var html = '';

  // 1) Plan por día
  html += '<div class="card"><h2>📅 Plan sugerido · ' + (d.plan_por_dia||[]).length + ' días</h2>';
  if ((d.plan_por_dia||[]).length === 0){
    html += '<div class="muted">No hay producciones sugeridas en este horizonte</div>';
  } else {
    html += '<table><thead><tr><th><input type="checkbox" id="chk_all_prog" onchange="toggleAllProg(this.checked)"></th><th>Fecha</th><th>Día</th><th>Producto</th><th>kg (Excel)</th><th>Motivo</th><th>Cobertura actual</th><th>Pipeline 7d</th></tr></thead><tbody>';
    (d.plan_por_dia||[]).forEach(g => {
      g.productos.forEach((p, idx) => {
        var item = (d.plan_items||[]).find(it => it.fecha === g.fecha && it.producto === p.producto) || {};
        var fechaObj = new Date(g.fecha + 'T12:00:00');
        var dia = DIAS_ES[fechaObj.getDay() === 0 ? 6 : fechaObj.getDay()-1];
        var tags = '';
        if (p.grande) tags += '<span class="tag tag-grande">GRANDE</span> ';
        if (p.complejo) tags += '<span class="tag tag-complejo">COMPLEJO</span> ';
        tags += '<span class="tag tag-' + (item.motivo||'buffer') + '">' + (item.motivo||'').toUpperCase() + '</span>';
        html += '<tr data-prog="1" data-idx="' + (d.plan_items||[]).indexOf(item) + '">';
        html += '<td><input type="checkbox" class="chk-prog" checked data-producto="' + escapeHtml(p.producto) + '" data-fecha="' + g.fecha + '" data-kg="' + p.kg + '" data-motivo="' + escapeHtml(item.motivo||'') + '"></td>';
        html += '<td class="mono">' + g.fecha + '</td>';
        html += '<td>' + dia + (idx===0 && g.productos.length > 1 ? ' <span class="muted">(' + g.productos.length + ' prods)</span>' : '') + '</td>';
        html += '<td><strong>' + escapeHtml(p.producto) + '</strong> ' + tags + '</td>';
        html += '<td style="text-align:right"><strong>' + p.kg + ' kg</strong></td>';
        html += '<td>' + escapeHtml(item.motivo||'') + '</td>';
        html += '<td style="text-align:right">' + (item.cob_dias_actual!=null ? item.cob_dias_actual + 'd' : '—') + '</td>';
        html += '<td style="text-align:right">' + (item.pipeline_7d_kg||0) + ' kg</td>';
        html += '</tr>';
      });
    });
    html += '</tbody></table></div>';
  }

  // 2) Cancelables
  if ((d.cancelables_calendar||[]).length){
    html += '<div class="card" style="background:#fef2f2;border:1px solid #fca5a5"><h2 style="color:#991b1b">🗑 Cancelables Calendar legacy · ' + d.cancelables_calendar.length + '</h2>';
    html += '<div class="muted" style="margin-bottom:10px">Lotes ya cubiertos por producciones recientes o reemplazados en el plan EOS.</div>';
    html += '<table><thead><tr><th><input type="checkbox" id="chk_all_cancel" onchange="toggleAllCancel(this.checked)"></th><th>ID</th><th>Producto</th><th>Fecha</th><th>kg</th><th>Razón</th></tr></thead><tbody>';
    d.cancelables_calendar.forEach(cn => {
      html += '<tr>';
      html += '<td><input type="checkbox" class="chk-cancel" checked data-id="' + cn.id + '"></td>';
      html += '<td class="mono">' + cn.id + '</td>';
      html += '<td>' + escapeHtml(cn.producto||'') + '</td>';
      html += '<td>' + (cn.fecha_programada||'').substring(0,10) + '</td>';
      html += '<td style="text-align:right">' + (cn.cantidad_kg||0) + ' kg</td>';
      html += '<td><code>' + escapeHtml(cn.razon||'') + '</code></td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
  }

  // 3) Sin fórmula
  if ((d.sin_formula||[]).length){
    html += '<div class="card" style="background:#fef9c3;border:1px solid #facc15"><h2 style="color:#854d0e">⚠ Productos SIN fórmula en Excel · ' + d.sin_formula.length + '</h2>';
    html += '<div class="muted" style="margin-bottom:10px">Estos productos aparecen con stock/ventas pero NO están en el mig 121. NO se programan automáticamente · primero hay que cargar su fórmula.</div>';
    html += '<table><thead><tr><th>Producto</th><th>Stock kg</th><th>Cobertura</th><th>Razón</th></tr></thead><tbody>';
    d.sin_formula.forEach(sf => {
      html += '<tr><td><strong>' + escapeHtml(sf.producto) + '</strong></td><td style="text-align:right">' + (sf.stock_kg||0) + '</td><td style="text-align:right">' + (sf.cob_dias||0) + 'd</td><td><code>' + escapeHtml(sf.razon||'') + '</code></td></tr>';
    });
    html += '</tbody></table></div>';
  }

  document.getElementById('contenido').innerHTML = html;
}

function toggleAllProg(checked){
  document.querySelectorAll('.chk-prog').forEach(el => el.checked = checked);
}
function toggleAllCancel(checked){
  document.querySelectorAll('.chk-cancel').forEach(el => el.checked = checked);
}

function parseBackfills(){
  var txt = document.getElementById('backfill_txt').value || '';
  var lines = txt.split('\n').map(s => s.trim()).filter(s => s && !s.startsWith('#'));
  var out = [];
  lines.forEach(line => {
    var parts = line.split('|').map(s => s.trim());
    if (parts.length >= 3){
      var kg = parseFloat(parts[1].replace(',','.'));
      if (!isNaN(kg) && kg > 0){
        out.push({producto: parts[0], kg: kg, fecha: parts[2]});
      }
    }
  });
  return out;
}

function recolectarSeleccion(soloSeleccionados){
  var programar = [];
  document.querySelectorAll('.chk-prog').forEach(el => {
    if (!soloSeleccionados || el.checked){
      programar.push({
        producto: el.dataset.producto,
        fecha: el.dataset.fecha,
        kg: parseFloat(el.dataset.kg),
        motivo: el.dataset.motivo,
      });
    }
  });
  var cancelar_ids = [];
  document.querySelectorAll('.chk-cancel').forEach(el => {
    if (!soloSeleccionados || el.checked){
      cancelar_ids.push(parseInt(el.dataset.id));
    }
  });
  var backfills = parseBackfills();
  return {programar, cancelar_ids, backfills};
}

async function ejecutar(payload){
  var box = document.getElementById('resultado_ejecucion');
  box.innerHTML = '<div class="resultado">⏳ Ejecutando…</div>';

  var msg = 'Vas a ejecutar:\n';
  msg += '  • ' + payload.programar.length + ' producciones a programar\n';
  msg += '  • ' + payload.cancelar_ids.length + ' lotes Calendar a cancelar\n';
  msg += '  • ' + payload.backfills.length + ' back-fills de producción real\n\n¿Confirmás?';
  if (!confirm(msg)) {
    box.innerHTML = '';
    return;
  }

  try {
    var r = await fetch('/api/plan/plan-sugerido/ejecutar', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-CSRF-Token': getCSRF()},
      body: JSON.stringify(payload),
    });
    var d = await r.json();
    if (!r.ok){
      box.innerHTML = '<div class="resultado error"><strong>Error ' + r.status + '</strong>: ' + escapeHtml(d.error||'desconocido') + '</div>';
      return;
    }
    var html = '<div class="resultado">';
    html += '<h3 style="margin:0 0 8px;color:#166534">✅ Aplicación completa</h3>';
    html += '<div>📅 <strong>' + d.programadas + '</strong> producciones programadas</div>';
    html += '<div>🗑 <strong>' + d.canceladas + '</strong> Calendar canceladas</div>';
    html += '<div>📥 <strong>' + d.backfills_creados + '</strong> back-fills registrados</div>';
    if (d.total_errores > 0){
      html += '<div style="margin-top:10px;color:#991b1b"><strong>⚠ ' + d.total_errores + ' errores:</strong><ul>';
      d.errores.forEach(e => {
        html += '<li>' + escapeHtml(e.accion) + ' #' + e.indice + ': ' + escapeHtml(e.error) + '</li>';
      });
      html += '</ul></div>';
    }
    html += '<div style="margin-top:10px"><a href="/admin/comparar-calendar-necesidades">→ Ver análisis actualizado</a></div>';
    html += '</div>';
    box.innerHTML = html;
  } catch(e){
    box.innerHTML = '<div class="resultado error">Error: ' + escapeHtml(e.message) + '</div>';
  }
}

function aplicarTodo(){
  if (!window._plan){ alert('Primero generá el plan'); return; }
  ejecutar(recolectarSeleccion(false));
}
function aplicarSeleccion(){
  if (!window._plan){ alert('Primero generá el plan'); return; }
  ejecutar(recolectarSeleccion(true));
}

cargar();
</script>
</body></html>"""


@bp.route("/api/plan/check-codigos-mp", methods=["GET"])
def check_codigos_mp():
    """Verifica qué códigos de MP del Excel existen en maestro_mps.

    Sebastián 13-may-2026: antes de importar fórmulas nuevas del Excel
    Alejandro, verificar que todos los códigos batch (MPxxxxx) tengan
    contraparte en maestro_mps. Los faltantes hay que crearlos primero
    (con su nombre_inci y nombre_comercial) para que el trigger mig 98
    permita insertar a formula_items.

    GET sin body · usa constantes _CODES_EXCEL_LIST y _EXCEL_INFO embebidas
    en el server (extraídas del Excel Alejandro mayo-2026). Read-only
    para saltarse el bloqueo MFA admin de mutaciones POST.

    Response:
        existentes: [{codigo, nombre_comercial_bd, nombre_inci_bd, activo}]
        faltantes: [{codigo, info_excel}]  · info_excel incluye inci+comercial
        inactivos: [{codigo, ...}]  · existen pero activo=0
        total_excel · total_existentes_activos · total_faltantes · total_inactivos
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    codigos = list(_CODES_EXCEL_LIST)
    info_excel = _EXCEL_INFO

    def _normalizar(s):
        """Lowercase + strip + sin acentos para comparar nombres."""
        import unicodedata
        if not s:
            return ""
        s = unicodedata.normalize('NFD', str(s).strip().lower())
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        # Reemplazar separadores comunes
        for ch in ('.', ',', '-', '/', '(', ')', ' ', '\t', '\n'):
            s = s.replace(ch, '')
        return s

    conn = get_db()
    c = conn.cursor()
    placeholders = ",".join(["?"] * len(codigos))
    rows = c.execute(
        f"""SELECT codigo_mp,
                   COALESCE(nombre_comercial, ''),
                   COALESCE(nombre_inci, ''),
                   COALESCE(activo, 1)
            FROM maestro_mps
            WHERE codigo_mp IN ({placeholders})""",
        codigos,
    ).fetchall()

    encontrados = {r[0]: {"codigo": r[0], "nombre_comercial_bd": r[1],
                          "nombre_inci_bd": r[2], "activo": int(r[3])}
                   for r in rows}

    # Comparar nombres BD vs Excel · Sebastián 13-may-2026:
    # "el código se relaciona con la misma materia prima?"
    # Para cada existente, verificar que BD.nombre_inci ~ Excel.inci O
    # BD.nombre_comercial ~ Excel.comercial. Si NINGUNO matchea, flag
    # como posible inconsistencia (riesgo: importar con MP equivocado).
    mismatches = []
    existentes_ok = []
    existentes_sin_info_bd = []  # BD vacío · no se puede comparar
    for info in encontrados.values():
        if info["activo"] != 1:
            continue
        cod = info["codigo"]
        ex_info = info_excel.get(cod, {})
        ex_inci = ex_info.get("inci", "")
        ex_com = ex_info.get("comercial", "")
        bd_inci = info["nombre_inci_bd"]
        bd_com = info["nombre_comercial_bd"]

        # Si BD no tiene ni inci ni comercial · no podemos comparar
        if not bd_inci and not bd_com:
            existentes_sin_info_bd.append({
                **info,
                "info_excel": ex_info,
            })
            continue

        # Si Excel no tiene info · solo confiamos en código
        if not ex_inci and not ex_com:
            existentes_ok.append(info)
            continue

        # Match si CUALQUIER campo coincide normalizado o si BD contiene
        # palabras clave del Excel (tolerante a typos menores).
        n_ex_inci = _normalizar(ex_inci)
        n_ex_com = _normalizar(ex_com)
        n_bd_inci = _normalizar(bd_inci)
        n_bd_com = _normalizar(bd_com)

        match = False
        # INCI vs INCI (cualquiera contiene al otro · puede haber prefijos)
        if n_ex_inci and n_bd_inci:
            if n_ex_inci == n_bd_inci or n_ex_inci[:15] in n_bd_inci or n_bd_inci[:15] in n_ex_inci:
                match = True
        # Comercial vs Comercial
        if not match and n_ex_com and n_bd_com:
            if n_ex_com == n_bd_com or n_ex_com[:10] in n_bd_com or n_bd_com[:10] in n_ex_com:
                match = True
        # Cruzado · Excel inci puede estar en BD comercial (y viceversa)
        if not match and n_ex_inci and n_bd_com:
            if n_ex_inci[:10] in n_bd_com or n_bd_com[:10] in n_ex_inci:
                match = True
        if not match and n_ex_com and n_bd_inci:
            if n_ex_com[:10] in n_bd_inci or n_bd_inci[:10] in n_ex_com:
                match = True

        if match:
            existentes_ok.append(info)
        else:
            mismatches.append({**info, "info_excel": ex_info})

    inactivos = [info for info in encontrados.values() if info["activo"] != 1]
    faltantes = [{
        "codigo": cod,
        "info_excel": info_excel.get(cod, {}),
    } for cod in codigos if cod not in encontrados]

    return jsonify({
        "total_excel": len(codigos),
        "total_existentes_ok": len(existentes_ok),
        "total_mismatches": len(mismatches),
        "total_existentes_sin_info_bd": len(existentes_sin_info_bd),
        "total_inactivos": len(inactivos),
        "total_faltantes": len(faltantes),
        "existentes": existentes_ok,
        "mismatches": mismatches,
        "existentes_sin_info_bd": existentes_sin_info_bd,
        "inactivos": inactivos,
        "faltantes": faltantes,
    })


def _valida_fecha_iso(s):
    """True si s es formato YYYY-MM-DD válido."""
    try:
        from datetime import date as _d
        _d.fromisoformat(s[:10])
        return True
    except Exception:
        return False


# Constantes de capacidad de planta · Sebastián 13-may-2026
# "solo trabajamos lunes a viernes · max 2 producciones por día"
DIAS_HABILES = {0, 1, 2, 3, 4}        # lun=0 ... vie=4
DIAS_PREFERIDOS = {0, 2, 4}            # lun, mié, vie (para canónico)
MAX_PRODUCCIONES_POR_DIA = 2

# Timezone Colombia · módulo central api/tz_colombia.py · Sebastián 13-may-2026
try:
    from tz_colombia import (
        TZ_COLOMBIA, hoy_colombia as _hoy_colombia,
        now_colombia as _now_colombia,
        SQLITE_DATE_NOW as SQLITE_DATE_COL,
        SQLITE_DATETIME_NOW as SQLITE_NOW_COL,
    )
except ImportError:
    from api.tz_colombia import (
        TZ_COLOMBIA, hoy_colombia as _hoy_colombia,
        now_colombia as _now_colombia,
        SQLITE_DATE_NOW as SQLITE_DATE_COL,
        SQLITE_DATETIME_NOW as SQLITE_NOW_COL,
    )


# Festivos colombianos · Sebastián 13-may-2026
# "revisa bien dias festivos en colombia asi evitamos errores"
# Calculados algorítmicamente para cualquier año:
# - Fijos sin mover: 1-ene, 1-may, 20-jul, 7-ago, 8-dic, 25-dic
# - Semana Santa: Jueves y Viernes Santo (Pascua − 3 y − 2)
# - Ley Emiliani (movidos al lunes siguiente si caen otro día):
#     Reyes (6-ene), San José (19-mar), Ascensión (Pascua+39),
#     Corpus Christi (Pascua+60), Sagrado Corazón (Pascua+68),
#     San Pedro y San Pablo (29-jun), Asunción (15-ago),
#     Día de la Raza (12-oct), Todos los Santos (1-nov),
#     Independencia Cartagena (11-nov)
_FESTIVOS_CACHE = {}


def _calcular_pascua(year):
    """Algoritmo de Butcher · domingo de Pascua para cualquier año.
    Validado: 2026=5-abr, 2027=28-mar, 2028=16-abr.
    """
    from datetime import date as _date
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return _date(year, month, day)


def _festivos_colombia_year(year):
    """Devuelve set de date con festivos colombianos del año.
    Cacheado en _FESTIVOS_CACHE.
    """
    if year in _FESTIVOS_CACHE:
        return _FESTIVOS_CACHE[year]
    from datetime import date as _date, timedelta as _td

    def _mover_a_lunes(fecha):
        wd = fecha.weekday()
        if wd == 0:
            return fecha
        return fecha + _td(days=(7 - wd))

    pascua = _calcular_pascua(year)
    fest = set()

    # Fijos
    fest.add(_date(year, 1, 1))    # Año Nuevo
    fest.add(_date(year, 5, 1))    # Día del Trabajo
    fest.add(_date(year, 7, 20))   # Independencia
    fest.add(_date(year, 8, 7))    # Batalla de Boyacá
    fest.add(_date(year, 12, 8))   # Inmaculada Concepción
    fest.add(_date(year, 12, 25))  # Navidad

    # Semana Santa (no se mueven)
    fest.add(pascua - _td(days=3))  # Jueves Santo
    fest.add(pascua - _td(days=2))  # Viernes Santo

    # Movibles (Ley Emiliani)
    fest.add(_mover_a_lunes(_date(year, 1, 6)))    # Reyes
    fest.add(_mover_a_lunes(_date(year, 3, 19)))   # San José
    fest.add(_mover_a_lunes(pascua + _td(days=39)))  # Ascensión
    fest.add(_mover_a_lunes(pascua + _td(days=60)))  # Corpus Christi
    fest.add(_mover_a_lunes(pascua + _td(days=68)))  # Sagrado Corazón
    fest.add(_mover_a_lunes(_date(year, 6, 29)))   # S Pedro y Pablo
    fest.add(_mover_a_lunes(_date(year, 8, 15)))   # Asunción
    fest.add(_mover_a_lunes(_date(year, 10, 12)))  # Día de la Raza
    fest.add(_mover_a_lunes(_date(year, 11, 1)))   # Todos los Santos
    fest.add(_mover_a_lunes(_date(year, 11, 11)))  # Independencia Cartagena

    _FESTIVOS_CACHE[year] = fest
    return fest


def es_festivo_colombia(fecha):
    """True si la fecha (date) es festivo en Colombia."""
    return fecha in _festivos_colombia_year(fecha.year)


# Umbral · lotes >50kg se consideran "grandes" y van solos en su día.
# Sebastián 13-may-2026: "si hay un lote grande de 90 kilos debe quedar
# ese dia solo, podemos hacer dos el mismo dia si son cosas pequeñas".
LOTE_GRANDE_KG = 50.0

# Productos "complejos" que requieren envasado el mismo día → preferir
# Lun/Mié para tener Mar/Jue/Vie para envasado + descarga. El operario
# elaboración no puede solapar con otro lote.
# Match por substring case-insensitive en producto_nombre canónico.
PRODUCTOS_COMPLEJOS_SUBSTR = ("VITAMINA C", "TRIACTIVE")


def _es_producto_complejo(producto_nombre):
    """True si el producto requiere envasado el mismo día (Vit C / Triactive)."""
    if not producto_nombre:
        return False
    pu = producto_nombre.upper()
    return any(s in pu for s in PRODUCTOS_COMPLEJOS_SUBSTR)


def _proxima_fecha_habil(c, fecha_obj, prefer_mwf=False, max_lookahead=400,
                         lote_kg=None, producto_nombre=None):
    """Devuelve la próxima fecha date que cumpla:
    - Día hábil (lun-vie, no fines de semana, NO festivo colombiano)
    - Cuenta de producciones activas ese día < MAX_PRODUCCIONES_POR_DIA
    - Si prefer_mwf=True · prefiere lun/mié/vie pero acepta mar/jue si los
      preferidos están saturados
    - Si lote_kg > LOTE_GRANDE_KG · ese día NO puede tener otra producción
      (max 1 producción ese día, no importa el tamaño)
    - Si ya hay UN lote grande ese día · no permite agregar más
    - Si producto_nombre es Vit C o Triactive · fuerza lun/mié (no vie)

    Si no se puede encontrar dentro de max_lookahead días → retorna None.
    """
    from datetime import timedelta as _td

    es_grande = lote_kg is not None and lote_kg > LOTE_GRANDE_KG
    es_complejo = _es_producto_complejo(producto_nombre)
    # Complejos solo Lun/Mié (weekday 0,2) · más restrictivo que prefer_mwf
    DIAS_COMPLEJOS = {0, 2}

    cur = fecha_obj
    for _ in range(max_lookahead):
        if cur.weekday() in DIAS_HABILES and not es_festivo_colombia(cur):
            # Filtro día de la semana
            if es_complejo:
                if cur.weekday() not in DIAS_COMPLEJOS:
                    cur = cur + _td(days=1)
                    continue
            elif prefer_mwf and cur.weekday() not in DIAS_PREFERIDOS:
                cur = cur + _td(days=1)
                continue

            # Filtro capacidad · contar + considerar si hay grandes ya
            rows = c.execute(
                """SELECT pp.id, COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0)
                   FROM produccion_programada pp
                   LEFT JOIN formula_headers fh
                     ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
                   WHERE date(pp.fecha_programada) = ?
                     AND pp.estado IN ('pendiente','programado','en_curso')""",
                (cur.isoformat(),),
            ).fetchall()
            count = len(rows)
            ya_hay_grande = any((r[1] or 0) > LOTE_GRANDE_KG for r in rows)

            if es_grande:
                # Lote grande · solo permitido si día está vacío
                if count == 0:
                    return cur
            else:
                # Lote normal · permitido si <MAX y NO hay grande ya
                if count < MAX_PRODUCCIONES_POR_DIA and not ya_hay_grande:
                    return cur
        cur = cur + _td(days=1)
    return None


@bp.route("/api/plan/proximas", methods=["GET"])
def plan_proximas():
    """Lista lotes de produccion_programada con filtros.

    Sebastián 13-may-2026: usado por dos vistas:
    - Tab Plan en curso · bitácora completa con filtros estado/fecha
    - (deprecated) sección Próximas en Necesidades · ya removida pero
      el endpoint se conserva

    Query params:
        estados: lista coma-separada · default pendiente,programado,en_curso
                 valores válidos: pendiente, programado, en_curso, completado,
                 cancelado, propuesto
        desde: YYYY-MM-DD · fecha_programada >= (default: hoy - 7d)
        hasta: YYYY-MM-DD · fecha_programada <= (default: sin límite)
        producto: filtro substring case-insensitive en producto

    Devuelve ordenado por fecha_programada ASC + id ASC.
    """
    err = _require_login()
    if err:
        return err

    # Parse filtros
    estados_param = (request.args.get("estados") or "").strip()
    if estados_param:
        estados = [e.strip() for e in estados_param.split(",") if e.strip()]
    else:
        estados = ['pendiente', 'programado', 'en_curso']

    valid = {'pendiente','programado','en_curso','completado','cancelado','propuesto'}
    estados = [e for e in estados if e in valid]
    if not estados:
        return jsonify({"error": "estados inválidos"}), 400

    desde = (request.args.get("desde") or "").strip()
    hasta = (request.args.get("hasta") or "").strip()
    if desde and not _valida_fecha_iso(desde):
        return jsonify({"error": "desde formato YYYY-MM-DD"}), 400
    if hasta and not _valida_fecha_iso(hasta):
        return jsonify({"error": "hasta formato YYYY-MM-DD"}), 400

    producto_filtro = (request.args.get("producto") or "").strip()
    # Sebastián 13-may-2026: "olvidemos Calendar · en Plan montemos la
    # realidad de lo que estamos programando". Plan en curso muestra
    # SOLO origenes EOS por default. Si admin necesita ver legacy
    # (calendar, manual), pasa incluir_legacy=1.
    incluir_legacy = request.args.get("incluir_legacy", "0") == "1"

    conn = get_db()
    c = conn.cursor()
    placeholders = ",".join(["?"] * len(estados))
    where = [f"pp.estado IN ({placeholders})"]
    params = list(estados)

    if not incluir_legacy:
        # Solo los origenes que EOS controla
        where.append("pp.origen IN ('eos_plan','eos_canonico','eos_retroactivo')")

    if desde:
        where.append("date(pp.fecha_programada) >= date(?)")
        params.append(desde)
    else:
        # Default: últimos 7 días + futuro
        where.append("date(pp.fecha_programada) >= date('now', '-5 hours', '-7 day')")

    if hasta:
        where.append("date(pp.fecha_programada) <= date(?)")
        params.append(hasta)

    if producto_filtro:
        where.append("LOWER(pp.producto) LIKE LOWER(?)")
        params.append(f"%{producto_filtro}%")

    sql = f"""SELECT pp.id, pp.producto, pp.fecha_programada, pp.cantidad_kg,
                     pp.estado, pp.origen, pp.observaciones,
                     pp.area_id, ap.codigo as area_codigo, ap.nombre as area_nombre,
                     pp.creado_en, pp.kg_real, pp.fin_real_at, pp.inicio_real_at
              FROM produccion_programada pp
              LEFT JOIN areas_planta ap ON ap.id = pp.area_id
              WHERE {' AND '.join(where)}
              ORDER BY pp.fecha_programada ASC, pp.id ASC"""
    rows = c.execute(sql, params).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "producto": r[1] or "",
            "fecha_programada": r[2] or "",
            "cantidad_kg": float(r[3] or 0),
            "estado": r[4] or "",
            "origen": r[5] or "",
            "observaciones": r[6] or "",
            "area_id": r[7],
            "area_codigo": r[8] or "",
            "area_nombre": r[9] or "",
            "creado_en": r[10] or "",
            "kg_real": float(r[11] or 0) if r[11] else None,
            "fin_real_at": r[12],
            "inicio_real_at": r[13],
        })
    return jsonify({"items": items, "total": len(items),
                     "filtros": {"estados": estados, "desde": desde or None,
                                  "hasta": hasta or None, "producto": producto_filtro or None}})


@bp.route("/api/plan/proximas/<int:pid>", methods=["DELETE"])
def cancelar_proxima(pid):
    """Cancela un lote agendado (soft delete · estado='cancelado')."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT estado, producto, fecha_programada FROM produccion_programada WHERE id = ?",
        (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "lote no encontrado"}), 404
    estado_actual, producto, fecha = row
    if estado_actual not in ('pendiente', 'programado'):
        return jsonify({
            "error": f"solo se puede cancelar pendiente/programado · estado actual: {estado_actual}",
        }), 409

    cur.execute("UPDATE produccion_programada SET estado='cancelado' WHERE id = ?", (pid,))
    conn.commit()
    audit_log(cur, usuario=user, accion="CANCELAR_PRODUCCION_PROGRAMADA",
              tabla="produccion_programada", registro_id=pid,
              antes={"estado": estado_actual, "producto": producto, "fecha": fecha},
              despues={"estado": "cancelado"})
    return jsonify({"ok": True, "id": pid, "estado": "cancelado"})


@bp.route("/api/plan/proximas/<int:pid>/reprogramar", methods=["POST"])
def reprogramar_proxima(pid):
    """Cambia la fecha de un lote agendado · útil cuando falta MP ese
    día o hay otro imprevisto.

    Sebastián 13-may-2026: "nos falta mover o cambiar fecha por si no
    hay materia prima por ejemplo".

    Body:
        nueva_fecha: str YYYY-MM-DD (requerido)
        razon: str (opcional · "falta_mp", "operario_ausente", etc.)
        skip_validacion_dia: bool (default False · admin override)

    Reglas aplicadas si skip_validacion_dia=False:
        - No festivo colombiano · no fin de semana
        - Si lote >50kg · día destino no debe tener otra producción
        - Si producto es Vit C / Triactive · solo Lun/Mié
        - Si día destino ya tiene MAX_PRODUCCIONES_POR_DIA · rechazar

    Inmutabilidad post-aprobación · si tiene fin_real_at o
    inicio_real_at → 409.

    Audit_log captura fecha_antes/fecha_despues/razon.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    nueva_fecha = (body.get("nueva_fecha") or "").strip()
    razon = (body.get("razon") or "").strip()
    skip_val = bool(body.get("skip_validacion_dia"))

    if not nueva_fecha or not _valida_fecha_iso(nueva_fecha):
        return jsonify({"error": "nueva_fecha YYYY-MM-DD requerida"}), 400

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT pp.estado, pp.producto, pp.fecha_programada,
                  COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0),
                  pp.inicio_real_at, pp.fin_real_at, pp.origen
           FROM produccion_programada pp
           LEFT JOIN formula_headers fh
             ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
           WHERE pp.id = ?""",
        (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "lote no encontrado"}), 404

    estado_actual, producto, fecha_antes, lote_kg, inicio_real, fin_real, origen = row
    lote_kg = float(lote_kg or 0)

    # Inmutabilidad post-arranque · no reprogramar lotes en ejecución
    if fin_real:
        return jsonify({
            "error": f"lote ya completado · no reprogramable (fin_real_at={fin_real})",
        }), 409
    if inicio_real:
        return jsonify({
            "error": f"lote en curso · no reprogramable (inicio_real_at={inicio_real})",
        }), 409
    if estado_actual not in ('pendiente', 'programado'):
        return jsonify({
            "error": f"solo se reprograma pendiente/programado · estado actual: {estado_actual}",
        }), 409

    # Same date · no-op pero no error
    if (fecha_antes or "")[:10] == nueva_fecha:
        return jsonify({"ok": True, "id": pid, "noop": True,
                        "fecha": nueva_fecha}), 200

    # Validar fecha destino (a menos que admin la fuerce)
    if not skip_val:
        from datetime import date as _date
        try:
            f_obj = _date.fromisoformat(nueva_fecha)
        except ValueError:
            return jsonify({"error": "nueva_fecha formato inválido"}), 400

        if f_obj.weekday() not in DIAS_HABILES:
            return jsonify({
                "error": f"{nueva_fecha} es fin de semana · usa skip_validacion_dia=true para forzar",
            }), 422
        if es_festivo_colombia(f_obj):
            return jsonify({
                "error": f"{nueva_fecha} es festivo colombiano · usa skip_validacion_dia=true para forzar",
            }), 422

        # Productos complejos · solo Lun/Mié
        if _es_producto_complejo(producto) and f_obj.weekday() not in {0, 2}:
            return jsonify({
                "error": f"{producto} es complejo · solo Lun/Mié (envasado mismo día) · usa skip_validacion_dia=true para forzar",
            }), 422

        # Capacidad del día destino · excluir el propio lote
        rows_dia = cur.execute(
            """SELECT pp.id, COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0)
               FROM produccion_programada pp
               LEFT JOIN formula_headers fh
                 ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
               WHERE date(pp.fecha_programada) = ?
                 AND pp.estado IN ('pendiente','programado','en_curso')
                 AND pp.id != ?""",
            (nueva_fecha, pid),
        ).fetchall()
        count_dia = len(rows_dia)
        kgs_dia = [float(r[1] or 0) for r in rows_dia]
        ya_grande = any(k > LOTE_GRANDE_KG for k in kgs_dia)
        es_grande = lote_kg > LOTE_GRANDE_KG

        if es_grande and count_dia > 0:
            return jsonify({
                "error": f"{nueva_fecha} ya tiene {count_dia} producción(es) · este lote grande necesita el día solo · usa skip_validacion_dia=true para forzar",
            }), 422
        if not es_grande and ya_grande:
            return jsonify({
                "error": f"{nueva_fecha} ya tiene un lote grande · no se pueden agregar más · usa skip_validacion_dia=true para forzar",
            }), 422
        if not es_grande and count_dia >= MAX_PRODUCCIONES_POR_DIA:
            return jsonify({
                "error": f"{nueva_fecha} ya tiene {count_dia} producciones (max {MAX_PRODUCCIONES_POR_DIA}) · usa skip_validacion_dia=true para forzar",
            }), 422

    # UPDATE + audit
    cur.execute(
        """UPDATE produccion_programada
           SET fecha_programada = ?,
               observaciones = COALESCE(observaciones,'') ||
                   ' · REPROGRAMADO de ' || COALESCE(?,'?') || ' a ' || ? ||
                   CASE WHEN ? != '' THEN ' (razón: ' || ? || ')' ELSE '' END ||
                   ' · ' || datetime('now', '-5 hours')
           WHERE id = ?""",
        (nueva_fecha, fecha_antes, nueva_fecha, razon, razon, pid),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="REPROGRAMAR_PRODUCCION_PROGRAMADA",
              tabla="produccion_programada", registro_id=pid,
              antes={"fecha_programada": fecha_antes,
                     "producto": producto, "origen": origen},
              despues={"fecha_programada": nueva_fecha, "razon": razon,
                       "skip_validacion_dia": skip_val})
    conn.commit()

    return jsonify({"ok": True, "id": pid, "producto": producto,
                    "fecha_antes": fecha_antes, "fecha_nueva": nueva_fecha,
                    "razon": razon or None})


@bp.route("/api/plan/proximas/<int:pid>/pausar", methods=["POST"])
def pausar_proxima(pid):
    """Pausa un lote agendado · estado='esperando_recurso' hasta que
    llegue la materia prima u otro insumo.

    Sebastián 13-may-2026: "algunas es por materia prima entonces
    debemos dejarla pendiente hasta que llegue la materia prima".

    Body:
        motivo_pausa: str requerido · "falta_mp", "operario_ausente",
                      "equipo_mantenimiento", "espera_QC", etc.

    409 si ya iniciado (inicio_real_at), completado o cancelado.
    Audit_log: PAUSAR_PRODUCCION_PROGRAMADA.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo_pausa") or "").strip()
    if not motivo:
        return jsonify({"error": "motivo_pausa requerido"}), 400

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT estado, producto, fecha_programada,
                  inicio_real_at, fin_real_at, motivo_pausa
           FROM produccion_programada WHERE id = ?""",
        (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "lote no encontrado"}), 404

    estado_actual, producto, fecha, inicio_real, fin_real, motivo_prev = row

    if fin_real:
        return jsonify({"error": "lote completado · no pausable"}), 409
    if inicio_real:
        return jsonify({"error": "lote en curso · no pausable"}), 409
    if estado_actual == 'cancelado':
        return jsonify({"error": "lote cancelado · no pausable"}), 409
    if estado_actual == 'esperando_recurso' and motivo == motivo_prev:
        return jsonify({"ok": True, "id": pid, "noop": True}), 200

    cur.execute(
        f"""UPDATE produccion_programada
            SET estado = 'esperando_recurso',
                motivo_pausa = ?,
                pausado_at = {SQLITE_NOW_COL},
                pausado_por = ?,
                observaciones = COALESCE(observaciones,'') ||
                    ' · PAUSADO (' || ? || ') por ' || ? || ' · ' || {SQLITE_NOW_COL}
            WHERE id = ?""",
        (motivo, user, motivo, user, pid),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="PAUSAR_PRODUCCION_PROGRAMADA",
              tabla="produccion_programada", registro_id=pid,
              antes={"estado": estado_actual, "producto": producto,
                     "fecha": fecha, "motivo_pausa": motivo_prev},
              despues={"estado": "esperando_recurso", "motivo_pausa": motivo})
    conn.commit()
    return jsonify({"ok": True, "id": pid, "estado": "esperando_recurso",
                    "motivo_pausa": motivo})


@bp.route("/api/plan/proximas/<int:pid>/reactivar", methods=["POST"])
def reactivar_proxima(pid):
    """Reactiva un lote 'esperando_recurso' → vuelve a 'programado'.

    Body:
        nueva_fecha: str YYYY-MM-DD (opcional · si no, conserva la previa)
        skip_validacion_dia: bool (default False)
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    nueva_fecha = (body.get("nueva_fecha") or "").strip()
    skip_val = bool(body.get("skip_validacion_dia"))

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT pp.estado, pp.producto, pp.fecha_programada,
                  COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0),
                  pp.motivo_pausa
           FROM produccion_programada pp
           LEFT JOIN formula_headers fh
             ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
           WHERE pp.id = ?""",
        (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "lote no encontrado"}), 404

    estado_actual, producto, fecha_actual, lote_kg, motivo_prev = row
    lote_kg = float(lote_kg or 0)

    if estado_actual != 'esperando_recurso':
        return jsonify({
            "error": f"solo se reactiva 'esperando_recurso' · estado actual: {estado_actual}",
        }), 409

    fecha_destino = nueva_fecha or (fecha_actual or "")[:10]
    if not fecha_destino or not _valida_fecha_iso(fecha_destino):
        return jsonify({"error": "fecha destino inválida"}), 400

    if not skip_val:
        from datetime import date as _date
        f_obj = _date.fromisoformat(fecha_destino)
        if f_obj.weekday() not in DIAS_HABILES:
            return jsonify({"error": f"{fecha_destino} es fin de semana"}), 422
        if es_festivo_colombia(f_obj):
            return jsonify({"error": f"{fecha_destino} es festivo colombiano"}), 422
        if _es_producto_complejo(producto) and f_obj.weekday() not in {0, 2}:
            return jsonify({"error": f"{producto} es complejo · solo Lun/Mié"}), 422
        rows_dia = cur.execute(
            """SELECT pp.id, COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0)
               FROM produccion_programada pp
               LEFT JOIN formula_headers fh
                 ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
               WHERE date(pp.fecha_programada) = ?
                 AND pp.estado IN ('pendiente','programado','en_curso')
                 AND pp.id != ?""",
            (fecha_destino, pid),
        ).fetchall()
        kgs_dia = [float(r[1] or 0) for r in rows_dia]
        ya_grande = any(k > LOTE_GRANDE_KG for k in kgs_dia)
        es_grande = lote_kg > LOTE_GRANDE_KG
        if es_grande and len(rows_dia) > 0:
            return jsonify({"error": f"{fecha_destino} ocupado · grande necesita día solo"}), 422
        if not es_grande and (ya_grande or len(rows_dia) >= MAX_PRODUCCIONES_POR_DIA):
            return jsonify({"error": f"{fecha_destino} saturado"}), 422

    cur.execute(
        f"""UPDATE produccion_programada
            SET estado = 'programado',
                fecha_programada = ?,
                motivo_pausa = NULL,
                observaciones = COALESCE(observaciones,'') ||
                    ' · REACTIVADO de pausa (motivo previo: ' ||
                    COALESCE(?, '?') || ') por ' || ? ||
                    ' · ' || {SQLITE_NOW_COL}
            WHERE id = ?""",
        (fecha_destino, motivo_prev, user, pid),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="REACTIVAR_PRODUCCION_PROGRAMADA",
              tabla="produccion_programada", registro_id=pid,
              antes={"estado": "esperando_recurso", "producto": producto,
                     "motivo_pausa": motivo_prev, "fecha_anterior": fecha_actual},
              despues={"estado": "programado", "fecha_programada": fecha_destino})
    conn.commit()
    return jsonify({"ok": True, "id": pid, "estado": "programado",
                    "fecha_programada": fecha_destino})


@bp.route("/api/plan/programar-canonico", methods=["POST"])
def programar_canonico():
    """Programa N lotes recurrentes con horizonte (típicamente 1 año).

    Sebastián 13-may-2026: "quieres hacerlo canónico, cada 60 días por
    un año · horizonte sólido". Crea múltiples filas en
    produccion_programada con origen='eos_canonico' respetando:
    - Solo lunes a viernes (skip fin de semana)
    - Preferir lun/mié/vie (3 días/semana, ritmo Sebastián)
    - Max 2 producciones por día (capacidad planta)

    Body:
        producto_nombre: str
        cantidad_kg: float > 0
        frecuencia_dias: int 7..180 (típicamente 30/60/90)
        horizonte_dias: int 30..730 (default 365)
        fecha_inicio: str YYYY-MM-DD (default hoy+3d)
        notas: str opcional

    Response:
        201 {ok, lotes_creados: [{id, fecha, kg}, ...], total: N}
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    try:
        kg = float(body.get("cantidad_kg") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_kg inválida"}), 400
    try:
        freq = int(body.get("frecuencia_dias") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "frecuencia_dias inválida"}), 400
    try:
        horizonte = int(body.get("horizonte_dias") or 365)
    except (ValueError, TypeError):
        return jsonify({"error": "horizonte_dias inválido"}), 400
    fecha_inicio = (body.get("fecha_inicio") or "").strip()
    notas = (body.get("notas") or "").strip()

    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    if kg <= 0:
        return jsonify({"error": "cantidad_kg debe ser > 0"}), 400
    if not (7 <= freq <= 180):
        return jsonify({"error": "frecuencia_dias debe estar entre 7 y 180"}), 400
    if not (30 <= horizonte <= 730):
        return jsonify({"error": "horizonte_dias debe estar entre 30 y 730"}), 400

    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()
    if fecha_inicio:
        if not _valida_fecha_iso(fecha_inicio):
            return jsonify({"error": "fecha_inicio formato YYYY-MM-DD"}), 400
        f_ini = _date.fromisoformat(fecha_inicio[:10])
    else:
        f_ini = hoy + _td(days=3)  # default: 3 días desde hoy

    f_fin = hoy + _td(days=horizonte)

    conn = get_db()
    cur = conn.cursor()

    if not cur.execute(
        "SELECT 1 FROM formula_headers WHERE producto_nombre = ?", (producto,),
    ).fetchone():
        return jsonify({"error": f"producto '{producto}' no existe"}), 404

    lotes_creados = []
    fecha_objetivo = f_ini

    while fecha_objetivo <= f_fin:
        # Encontrar próxima fecha hábil con capacidad disponible
        fecha_real = _proxima_fecha_habil(cur, fecha_objetivo, prefer_mwf=True)
        if fecha_real is None or fecha_real > f_fin:
            break

        cur.execute(
            """INSERT INTO produccion_programada
                 (producto, fecha_programada, cantidad_kg, lotes, estado,
                  origen, observaciones, creado_en)
               VALUES (?, ?, ?, 1, 'pendiente', 'eos_canonico', ?, datetime('now', '-5 hours'))""",
            (producto, fecha_real.isoformat(), kg,
             f"Canónico cada {freq}d" + (f" · {notas}" if notas else "")),
        )
        pid = cur.lastrowid
        lotes_creados.append({
            "id": pid,
            "fecha": fecha_real.isoformat(),
            "kg": kg,
        })

        # Avanzar el objetivo a la próxima fecha según frecuencia
        # (NO desde fecha_real para que el ritmo no se descalibre)
        fecha_objetivo = fecha_real + _td(days=freq)

    audit_log(cur, usuario=user, accion="PROGRAMAR_CANONICO",
              tabla="produccion_programada", registro_id=lotes_creados[0]["id"] if lotes_creados else None,
              despues={"producto": producto, "kg": kg, "frecuencia_dias": freq,
                       "horizonte_dias": horizonte, "total_lotes": len(lotes_creados),
                       "fecha_inicio": f_ini.isoformat(),
                       "fecha_fin": (lotes_creados[-1]["fecha"] if lotes_creados else None)})
    conn.commit()
    return jsonify({
        "ok": True,
        "total": len(lotes_creados),
        "lotes_creados": lotes_creados,
        "producto": producto,
        "frecuencia_dias": freq,
        "horizonte_dias": horizonte,
    }), 201


@bp.route("/api/plan/registrar-produccion-completada", methods=["POST"])
def registrar_produccion_completada():
    """Registra retroactivamente un lote ya producido.

    Sebastián 13-may-2026: "decir ya producido y que diga si se hizo tal
    día y tanto alcanzará para tantos días". Permite back-fill de
    producciones reales que ya pasaron · el horizonte de Necesidades usa
    esa data para calcular "próxima sugerida".

    NO toca movimientos (inventario ya refleja Shopify Available). Solo
    registra el evento histórico en produccion_programada con
    estado='completado' + fin_real_at + kg_real.

    Body:
        producto_nombre: str (FK formula_headers)
        cantidad_kg_real: float > 0
        fecha_producida: str YYYY-MM-DD
        lote: str opcional (auto si no se pasa)
        notas: str opcional

    Response:
        201 {ok, id, producto, fecha, kg_real, lote}
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    fecha = (body.get("fecha_producida") or "").strip()
    try:
        kg = float(body.get("cantidad_kg_real") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_kg_real inválida"}), 400
    lote = (body.get("lote") or "").strip()
    notas = (body.get("notas") or "").strip()

    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    if not fecha or not _valida_fecha_iso(fecha):
        return jsonify({"error": "fecha_producida formato YYYY-MM-DD requerido"}), 400
    if kg <= 0:
        return jsonify({"error": "cantidad_kg_real debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()

    if not cur.execute(
        "SELECT 1 FROM formula_headers WHERE producto_nombre = ?", (producto,),
    ).fetchone():
        return jsonify({"error": f"producto '{producto}' no existe"}), 404

    # Auto-generar lote si no se proporciona: PRODSHORT-YYYYMMDD-id
    if not lote:
        palabras = (producto or 'PROD').split()[:3]
        prod_short = ''.join(p[:3].upper() for p in palabras)[:12]
        lote = f"{prod_short}-{fecha.replace('-','')}"

    cur.execute(
        """INSERT INTO produccion_programada
             (producto, fecha_programada, cantidad_kg, lotes, estado,
              origen, observaciones, inicio_real_at, fin_real_at,
              kg_real, inventario_descontado_at, creado_en)
           VALUES (?, ?, ?, 1, 'completado', 'eos_retroactivo', ?,
                   ?, ?, ?, ?, datetime('now', '-5 hours'))""",
        (producto, fecha, kg,
         f"LOTE {lote}" + (f" · {notas}" if notas else ""),
         fecha + " 08:00:00",  # inicio_real_at · same day at 8am (placeholder)
         fecha + " 17:00:00",  # fin_real_at · same day at 5pm (placeholder)
         kg,
         fecha + " 08:00:00"),  # inventario_descontado_at · no double-discount
    )
    pid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_PRODUCCION_COMPLETADA",
              tabla="produccion_programada", registro_id=pid,
              despues={"producto": producto, "fecha": fecha,
                       "kg_real": kg, "lote": lote,
                       "origen": "eos_retroactivo", "notas": notas})
    conn.commit()
    return jsonify({
        "ok": True, "id": pid,
        "producto": producto, "fecha": fecha,
        "kg_real": kg, "lote": lote, "estado": "completado",
    }), 201
