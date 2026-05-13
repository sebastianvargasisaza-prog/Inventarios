"""Blueprint plan · Plan v3 unificado de necesidades por cliente · 13-may-2026.

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

    hoy = _date.today()
    ventana_desde = (hoy - _td(days=ventana)).isoformat()
    pipeline_desde = (hoy - _td(days=7)).isoformat()

    # 1. Productos activos con código asignado
    productos = c.execute(
        """SELECT producto_nombre, codigo_pt, lote_size_kg,
                  COALESCE(tiene_10ml,0), COALESCE(uds_10ml_por_lote,0),
                  COALESCE(tipo_10ml,''),
                  COALESCE(imagen_url,'')
           FROM formula_headers
           WHERE COALESCE(activo,1) = 1
             AND codigo_pt IS NOT NULL
             AND TRIM(codigo_pt) != ''
           ORDER BY producto_nombre""",
    ).fetchall()

    if not productos:
        return []

    # 2. Mapeo producto → sku_principal (para Shopify)
    # Estructura sku_producto_map: sku → producto_nombre
    sku_to_prod = {}
    for r in c.execute(
        """SELECT sku, producto_nombre FROM sku_producto_map
           WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
             AND TRIM(producto_nombre) != ''""",
    ).fetchall():
        sku_to_prod[r[0].upper()] = r[1]

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
             AND date(fin_real_at) <= date('now')
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

        # ml promedio · approx 30 (la mayoría son 30ml)
        ml_promedio = 30.0
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
            "dias_cobertura": dias_cobertura,
            "urgencia": urgencia,
            "n_lotes_recomendados": n_lotes_recomendados,
            "kg_a_producir": kg_a_producir,
            "regalos_extra_uds": regalos_extra_uds,
        })

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
             AND date(fecha_programada) >= date('now', '-7 day')
           GROUP BY producto""",
    ).fetchall():
        fechas = sorted(set([f.strip() for f in (r[3] or "").split(",") if f.strip()]))
        lotes_pendientes[r[0]] = {
            "n": r[1],
            "kg_total": round(float(r[2] or 0), 2),
            "proximas_fechas": fechas[:3],
        }
    # Inyectar en cada producto
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
           VALUES (?, ?, ?, 1, 'pendiente', 'eos_plan', ?, ?, datetime('now'))""",
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


def _valida_fecha_iso(s):
    """True si s es formato YYYY-MM-DD válido."""
    try:
        from datetime import date as _d
        _d.fromisoformat(s[:10])
        return True
    except Exception:
        return False
