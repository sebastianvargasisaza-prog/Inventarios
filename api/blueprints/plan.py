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
             AND date(fecha_programada) >= date('now', '-7 day')
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
    hoy = _date.today()
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
    hoy = _date.today()
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
             AND date(fecha_programada) >= date('now')
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

        # Stock efectivo · góndola + pipeline 7d (lo recién producido)
        stock_kg_efectivo = (nec["stock_kg_gondola"] or 0) + (nec["pipeline_kg"] or 0)

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
            "pipeline_kg": round(nec["pipeline_kg"] or 0, 2),
            "stock_kg_efectivo": round(stock_kg_efectivo, 2),
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
             AND date(fecha_programada) >= date('now')
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
      var pipeline = (p.pipeline_kg||0) > 0 ? ' <span style="color:#0891b2;font-weight:700">+' + p.pipeline_kg + '</span>' : '';
      tbl += '<tr>';
      tbl += '<td class="mono">' + escapeHtml(p.codigo_pt||'') + '</td>';
      tbl += '<td><strong>' + escapeHtml(p.producto_nombre) + '</strong><br><span style="color:#64748b;font-size:10px">' + p.stock_uds + ' uds</span></td>';
      tbl += '<td style="text-align:right"><strong>' + (p.stock_kg_gondola||0) + '</strong>' + pipeline + '</td>';
      tbl += '<td style="text-align:right">' + (p.velocidad_kg_dia||0).toFixed(2) + '</td>';
      tbl += '<td style="text-align:center">' + (p.dias_cobertura != null ? p.dias_cobertura + 'd' : '—') + '</td>';
      tbl += '<td style="text-align:center;color:#dc2626;font-weight:600">' + (p.fecha_agotamiento || '—') + '</td>';
      tbl += '<td style="text-align:center;color:#166534;font-weight:700">' + (p.fecha_producir_sugerida || '—') + '</td>';
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


def _proxima_fecha_habil(c, fecha_obj, prefer_mwf=False, max_lookahead=400):
    """Devuelve la próxima fecha date que cumpla:
    - Día hábil (lun-vie, no fines de semana)
    - Cuenta de producciones activas ese día < MAX_PRODUCCIONES_POR_DIA
    - Si prefer_mwf=True · prefiere lun/mié/vie pero acepta mar/jue si los
      preferidos están saturados

    Si no se puede encontrar dentro de max_lookahead días → retorna None.
    """
    from datetime import timedelta as _td
    cur = fecha_obj
    for _ in range(max_lookahead):
        if cur.weekday() in DIAS_HABILES:
            if (not prefer_mwf) or (cur.weekday() in DIAS_PREFERIDOS):
                count = c.execute(
                    """SELECT COUNT(*) FROM produccion_programada
                       WHERE date(fecha_programada) = ?
                         AND estado IN ('pendiente','programado','en_curso')""",
                    (cur.isoformat(),),
                ).fetchone()[0]
                if count < MAX_PRODUCCIONES_POR_DIA:
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
        where.append("date(pp.fecha_programada) >= date('now', '-7 day')")

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
    hoy = _date.today()
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
               VALUES (?, ?, ?, 1, 'pendiente', 'eos_canonico', ?, datetime('now'))""",
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
                   ?, ?, ?, ?, datetime('now'))""",
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
