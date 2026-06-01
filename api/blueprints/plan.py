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

# Buffer de re-orden · "producir N días ANTES de agotar el stock".
# Fuente de verdad única (Sebastián 23-may-2026: "las sugerencias deben ser 25
# días antes de que se acabe"). Antes había 20 hardcodeado en varios cálculos
# (timing_status, generadores de plan, frecuencia óptima) y 25 en otros
# (proxima_sugerida, cob_alerta) → fechas inconsistentes. Unificado a 25 ·
# coincide con cob_alerta default. Audit 30-may-2026.
BUFFER_REORDEN_DIAS = 25


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

    conn_l = get_db()
    rows = conn_l.execute(sql, params).fetchall()
    # FEATURE B2B 24-may-2026 · enriquecer cada pedido con su lote
    # consolidado (mig 171) · útil para que admin vea "qué lote cubre
    # mi pedido + cuándo se produce + cuánto bulk total".
    items = []
    pedido_ids = [r[0] for r in rows]
    lotes_por_pedido = {}
    if pedido_ids:
        try:
            ph = ','.join('?' * len(pedido_ids))
            for lr in conn_l.execute(
                f"""SELECT pbl.pedido_b2b_id, pbl.lote_produccion_id,
                          pbl.kg_aporte, pbl.unidades_aporte, pbl.modo,
                          pp.fecha_programada, pp.estado,
                          COALESCE(pp.cantidad_kg, 0),
                          COALESCE(pp.kg_real, 0),
                          pp.inicio_real_at, pp.fin_real_at
                   FROM pedidos_b2b_lote pbl
                   LEFT JOIN produccion_programada pp ON pp.id = pbl.lote_produccion_id
                   WHERE pbl.pedido_b2b_id IN ({ph})""",
                pedido_ids,
            ).fetchall():
                lotes_por_pedido[lr[0]] = {
                    'lote_id': lr[1],
                    'kg_aporte': float(lr[2] or 0),
                    'unidades_aporte': int(lr[3] or 0),
                    'modo': lr[4],
                    'fecha_lote': (lr[5] or '')[:10],
                    'estado_lote': lr[6] or '',
                    'kg_total_lote': float(lr[7] or 0),
                    'kg_real_lote': float(lr[8] or 0),
                    'iniciada': bool(lr[9]),
                    'terminada': bool(lr[10]),
                }
        except Exception:
            pass  # tabla no existe en BD vieja · fallback al payload básico
    for r in rows:
        items.append({
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
            "lote_consolidado": lotes_por_pedido.get(r[0]),
        })
    return jsonify({"items": items, "total": len(items)})


def _seleccionar_variante_optima(conn, producto_canonico, kg_objetivo=1.0):
    """FEATURE FÓRMULAS ALTERNATIVAS 24-may-2026 · dado un producto canónico
    (e.g. 'LIP SERUM'), busca las variantes registradas y devuelve la que
    actualmente tiene menos déficit MP para producir `kg_objetivo`.

    Algoritmo:
    1. Buscar variantes activas (formula_headers donde producto_canonico=?).
    2. Si hay 0 o 1 variantes → devolver esa (o None).
    3. Para cada variante, calcular sum(faltante_g) usando stock_mp_disponible
       y formula_items × kg_objetivo / lote_size_kg.
    4. Si hay prioridad manual >0, usar la de mayor prioridad.
    5. Si no, ganar la de menor faltante_total_g (o ninguno con faltantes).

    Returns: dict {producto_nombre, variante_label, faltante_total_g,
                    sin_faltantes: bool, n_variantes_evaluadas, decisión}
                 o None si producto_canonico no existe.
    """
    if not producto_canonico:
        return None
    try:
        variantes = conn.execute(
            """SELECT producto_nombre, COALESCE(variante_label,''),
                      COALESCE(prioridad, 0), COALESCE(lote_size_kg, 0)
               FROM formula_headers
               WHERE UPPER(TRIM(producto_canonico)) = UPPER(TRIM(?))
               ORDER BY prioridad DESC, id ASC""",
            (producto_canonico,),
        ).fetchall()
    except Exception:
        # mig 174 no aplicada · fallback al lookup exacto
        variantes = conn.execute(
            """SELECT producto_nombre, '', 0, COALESCE(lote_size_kg, 0)
               FROM formula_headers
               WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
            (producto_canonico,),
        ).fetchall()
    if not variantes:
        return None
    if len(variantes) == 1:
        v = variantes[0]
        return {
            'producto_nombre': v[0],
            'variante_label': v[1] or '',
            'faltante_total_g': 0,
            'sin_faltantes': True,
            'n_variantes_evaluadas': 1,
            'decision': 'unica_variante',
        }
    # Si hay variante con prioridad manual >0 → usar la más alta.
    max_prio = max((int(v[2] or 0)) for v in variantes)
    if max_prio > 0:
        v = next(v for v in variantes if int(v[2] or 0) == max_prio)
        return {
            'producto_nombre': v[0],
            'variante_label': v[1] or '',
            'faltante_total_g': 0,
            'sin_faltantes': True,
            'n_variantes_evaluadas': len(variantes),
            'decision': f'prioridad_manual_{max_prio}',
        }
    # PERF-FIX 27-may-2026 PM · audit round 4 · N+1 stock_mp_disponible.
    # Antes: por cada variante × item llamaba stock_mp_disponible(conn, mat_id)
    # que escanea movimientos · 5 variantes × 20 items = 100 SUM full table.
    # Ahora: una sola query agregada para TODOS los material_ids relevantes ·
    # dict lookup O(1) en el loop.
    #
    # 1) Levantar la lista de material_ids candidatos UPA vez.
    _todos_mat_ids = set()
    items_por_variante = {}
    for prod_nom, var_label, _prio, lote_kg in variantes:
        _items = conn.execute(
            """SELECT material_id, COALESCE(porcentaje, 0),
                      COALESCE(cantidad_g_por_lote, 0)
               FROM formula_items
               WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
            (prod_nom,),
        ).fetchall()
        items_por_variante[prod_nom] = _items
        for _row in _items:
            if _row[0]:
                _todos_mat_ids.add(_row[0])

    # 2) Una sola query agregada para stock disponible por material_id.
    stock_por_mat = {}
    if _todos_mat_ids:
        try:
            _ph = ','.join(['?'] * len(_todos_mat_ids))
            _mat_list = list(_todos_mat_ids)
            for _r in conn.execute(
                f"""SELECT material_id,
                          COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad
                                            WHEN tipo='Salida'  THEN -cantidad
                                            WHEN tipo='Ajuste'  THEN cantidad
                                            ELSE 0 END), 0)
                     FROM movimientos
                     WHERE material_id IN ({_ph})
                       AND (estado_lote IS NULL OR UPPER(estado_lote) NOT IN
                            ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO','VENCIDO','AGOTADO','BLOQUEADO'))
                     GROUP BY material_id""",
                _mat_list
            ).fetchall():
                stock_por_mat[_r[0]] = float(_r[1] or 0)
        except Exception:
            # Fallback a query individual si la batch falla (PG/SQLite divergence)
            for _mid in _todos_mat_ids:
                try:
                    stock_por_mat[_mid] = float(stock_mp_disponible(conn, _mid) or 0)
                except Exception:
                    stock_por_mat[_mid] = 0.0

    # Calcular faltante por variante (sin más SELECTs en el loop)
    evaluadas = []
    for prod_nom, var_label, _prio, lote_kg in variantes:
        items = items_por_variante.get(prod_nom, [])
        faltante_total = 0.0
        for mat_id, pct, cant_g_por_lote in items:
            if cant_g_por_lote and lote_kg:
                req_g = float(cant_g_por_lote) * (kg_objetivo / float(lote_kg)) if float(lote_kg) > 0 else float(cant_g_por_lote)
            else:
                req_g = (float(pct or 0) / 100.0) * float(kg_objetivo or 0) * 1000.0
            disp_g = stock_por_mat.get(mat_id, 0.0)
            if disp_g < req_g:
                faltante_total += (req_g - disp_g)
        evaluadas.append({
            'producto_nombre': prod_nom,
            'variante_label': var_label or '',
            'faltante_total_g': round(faltante_total, 1),
            'n_items': len(items),
        })
    # Ganadora = la de menor faltante
    evaluadas.sort(key=lambda e: e['faltante_total_g'])
    g = evaluadas[0]
    return {
        'producto_nombre': g['producto_nombre'],
        'variante_label': g['variante_label'],
        'faltante_total_g': g['faltante_total_g'],
        'sin_faltantes': g['faltante_total_g'] < 0.01,
        'n_variantes_evaluadas': len(evaluadas),
        'decision': 'min_faltante_mp' if g['faltante_total_g'] > 0 else 'tie_o_sin_faltante',
        'evaluadas': evaluadas,
    }


@bp.route("/api/admin/formulas/variantes/<path:producto_canonico>", methods=["GET"])
def admin_formulas_variantes(producto_canonico):
    """Lista variantes activas del producto canónico + selección óptima
    para kg_objetivo (?kg=10 default). Permite a Sebastián ver el porqué
    de la selección actual."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    try:
        kg = float(request.args.get('kg', '10'))
    except (TypeError, ValueError):
        kg = 10.0
    conn = get_db()
    seleccion = _seleccionar_variante_optima(conn, producto_canonico, kg_objetivo=kg)
    return jsonify({
        'producto_canonico': producto_canonico,
        'kg_objetivo': kg,
        'seleccion': seleccion,
    })


@bp.route("/api/admin/formulas/agrupar-canonico", methods=["POST"])
def admin_formulas_agrupar_canonico():
    """Agrupa N producto_nombre bajo un producto_canonico común. Útil para
    declarar variantes: "LIP SERUM PIB CHINO + LIP SERUM PIB LOCAL son
    ambos canónico=LIP SERUM, variante=PIB CHINO/LOCAL respectivamente".

    Body: {producto_canonico: "LIP SERUM", variantes: [
        {producto_nombre: "LIP SERUM PIB CHINO", variante_label: "PIB CHINO", prioridad: 0},
        {producto_nombre: "LIP SERUM PIB LOCAL", variante_label: "PIB LOCAL", prioridad: 0},
    ]}
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    body = request.get_json(silent=True) or {}
    canonico = (body.get('producto_canonico') or '').strip()
    variantes = body.get('variantes') or []
    if not canonico:
        return jsonify({'error': 'producto_canonico requerido'}), 400
    if not isinstance(variantes, list) or not variantes:
        return jsonify({'error': 'variantes lista requerida'}), 400
    conn = get_db()
    cur = conn.cursor()
    actualizadas = []
    errores = []
    for v in variantes:
        prod = (v.get('producto_nombre') or '').strip()
        label = (v.get('variante_label') or '').strip()
        try:
            prio = int(v.get('prioridad', 0))
        except (TypeError, ValueError):
            prio = 0
        if not prod:
            errores.append({'producto': prod, 'error': 'producto_nombre requerido'})
            continue
        ex = cur.execute(
            "SELECT 1 FROM formula_headers WHERE producto_nombre = ?",
            (prod,),
        ).fetchone()
        if not ex:
            errores.append({'producto': prod, 'error': 'no existe en formula_headers'})
            continue
        try:
            cur.execute(
                """UPDATE formula_headers
                     SET producto_canonico = ?, variante_label = ?, prioridad = ?
                   WHERE producto_nombre = ?""",
                (canonico, label, prio, prod),
            )
            actualizadas.append({'producto_nombre': prod, 'variante_label': label, 'prioridad': prio})
        except Exception as e:
            errores.append({'producto': prod, 'error': str(e)[:100]})
    audit_log(cur, usuario=user, accion='FORMULA_AGRUPAR_CANONICO',
              tabla='formula_headers', registro_id=canonico,
              despues={'canonico': canonico, 'n_actualizadas': len(actualizadas)})
    conn.commit()
    return jsonify({'ok': True, 'producto_canonico': canonico,
                    'actualizadas': actualizadas, 'errores': errores,
                    'n_actualizadas': len(actualizadas)})


@bp.route("/api/admin/diag-familia-producto", methods=["GET"])
def admin_diag_familia_producto():
    """Read-only · radiografía de una familia de producto (ej. 'LIP SERUM').

    Sebastián 31-may-2026: para decidir cómo unificar 'LIP SERUM PIB CHINO' vs
    'LIP SERUM VOLUMINIZADOR PEPTIDOS' (mismo producto, distinta MP). Muestra:
    fórmulas (con canónico/variante), SKUs mapeados y a qué nombre, y las
    presentaciones (tonos/envases). NO muta nada.
    """
    err = _require_login()
    if err:
        return err
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "q (texto a buscar) requerido"}), 400
    conn = get_db()
    c = conn.cursor()
    like = "%" + q.upper() + "%"

    # 1) Fórmulas (formula_headers) · con canónico/variante (fallback si faltan)
    formulas = []
    for _cols in (
        "producto_nombre, COALESCE(producto_canonico,''), COALESCE(variante_label,''), "
        "COALESCE(prioridad,0), COALESCE(activo,1), COALESCE(lote_size_kg,0), COALESCE(codigo_pt,'')",
        "producto_nombre, '', '', 0, COALESCE(activo,1), COALESCE(lote_size_kg,0), COALESCE(codigo_pt,'')",
    ):
        try:
            rows = c.execute(
                "SELECT " + _cols + " FROM formula_headers "
                "WHERE UPPER(producto_nombre) LIKE ? OR UPPER(COALESCE(producto_canonico,'')) LIKE ? "
                "ORDER BY producto_nombre", (like, like)).fetchall()
            break
        except Exception:
            rows = []
    for r in rows:
        formulas.append({
            "producto_nombre": r[0], "producto_canonico": r[1], "variante_label": r[2],
            "prioridad": r[3], "activo": bool(r[4]), "lote_size_kg": float(r[5] or 0),
            "codigo_pt": r[6],
        })

    # 2) SKUs en sku_producto_map relacionados (por SKU o por producto)
    skus = []
    for _cols in (
        "sku, producto_nombre, COALESCE(es_regalo,0), COALESCE(tono_label,''), COALESCE(activo,1)",
        "sku, producto_nombre, COALESCE(es_regalo,0), '', COALESCE(activo,1)",
        "sku, producto_nombre, 0, '', COALESCE(activo,1)",
    ):
        try:
            srows = c.execute(
                "SELECT " + _cols + " FROM sku_producto_map "
                "WHERE UPPER(sku) LIKE ? OR UPPER(COALESCE(producto_nombre,'')) LIKE ? "
                "ORDER BY producto_nombre, sku", (like, like)).fetchall()
            break
        except Exception:
            srows = []
    for r in srows:
        skus.append({"sku": r[0], "producto_nombre": r[1], "es_regalo": bool(r[2]),
                     "tono_label": r[3], "activo": bool(r[4])})

    # 3) Presentaciones (tonos/envases) de los productos de la familia
    pres = []
    for _cols in (
        "producto_nombre, presentacion_codigo, COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
        "COALESCE(envase_codigo,''), COALESCE(cantidad_fija_uds,0)",
        "producto_nombre, presentacion_codigo, COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
        "COALESCE(envase_codigo,''), 0",
    ):
        try:
            prows = c.execute(
                "SELECT " + _cols + " FROM producto_presentaciones "
                "WHERE UPPER(producto_nombre) LIKE ? AND COALESCE(activo,1)=1 "
                "ORDER BY producto_nombre, volumen_ml DESC", (like,)).fetchall()
            break
        except Exception:
            prows = []
    for r in prows:
        pres.append({"producto_nombre": r[0], "presentacion_codigo": r[1], "etiqueta": r[2],
                     "volumen_ml": float(r[3] or 0), "envase_codigo": r[4],
                     "cantidad_fija_uds": float(r[5] or 0)})

    # 4) STOCK por SKU · diagnóstico "dice que no hay pero en Shopify sí"
    # Sebastián 1-jun-2026: el motor de necesidades resuelve stock con la regla
    # "CC manda sobre SHOPIFY" (_resolved_stock_por_sku) y descarta filas con
    # unidades_disponible<=0. Si Shopify trae stock pero un conteo CC lo pisa, o
    # no hay filas en stock_pt para el SKU (el sync no lo trajo), acá se ve.
    stock_por_sku = []
    try:
        from blueprints.programacion import _resolved_stock_por_sku as _rss
        resolved = _rss(conn, empresa='ANIMUS')
    except Exception:
        resolved = {}
    sku_set = set()
    for s in skus:
        if s.get('sku'):
            sku_set.add(str(s['sku']).strip().upper())
    try:
        for r in c.execute(
            "SELECT UPPER(TRIM(sku_shopify)) FROM producto_presentaciones "
            "WHERE UPPER(producto_nombre) LIKE ? AND sku_shopify IS NOT NULL "
            "AND TRIM(sku_shopify)!=''", (like,)).fetchall():
            if r[0]:
                sku_set.add(r[0])
    except Exception:
        pass
    for sku in sorted(sku_set):
        cc_uds = 0
        shop_uds = 0
        empresas = set()
        try:
            for rr in c.execute(
                """SELECT CASE WHEN COALESCE(lote_produccion,'') LIKE 'SHOPIFY-%'
                               THEN 'SHOPIFY' ELSE 'CC' END AS bucket,
                          COALESCE(SUM(unidades_disponible), 0),
                          MAX(COALESCE(empresa, ''))
                   FROM stock_pt
                   WHERE UPPER(TRIM(sku)) = ? AND estado = 'Disponible'
                   GROUP BY CASE WHEN COALESCE(lote_produccion,'') LIKE 'SHOPIFY-%'
                                 THEN 'SHOPIFY' ELSE 'CC' END""", (sku,)).fetchall():
                if rr[0] == 'SHOPIFY':
                    shop_uds = int(rr[1] or 0)
                else:
                    cc_uds = int(rr[1] or 0)
                if rr[2]:
                    empresas.add(rr[2])
        except Exception:
            pass
        res = resolved.get(sku, {})
        if cc_uds > 0 and shop_uds > 0:
            diag = ('CC manda (%d uds) · Shopify (%d uds) IGNORADO por regla de autoridad. '
                    'Si Shopify es el real, el conteo CC quedó desactualizado.' % (cc_uds, shop_uds))
        elif cc_uds > 0:
            diag = 'CC (%d uds) · sin snapshot Shopify' % cc_uds
        elif shop_uds > 0:
            diag = 'Shopify (%d uds) · sin conteo CC' % shop_uds
        else:
            diag = ('SIN STOCK en stock_pt (ni CC ni Shopify Disponible). El sync no trajo '
                    'este SKU o no hay disponible · revisar sync-stock-shopify y que el SKU '
                    'coincida exacto con el de Shopify.')
        stock_por_sku.append({
            'sku': sku,
            'resolved_uds': int(res.get('uds', 0) or 0),
            'fuente': res.get('fuente', ''),
            'cc_uds_disponible': cc_uds,
            'shopify_uds_disponible': shop_uds,
            'empresas': sorted(empresas),
            'mapeado': any((s.get('sku') or '').strip().upper() == sku for s in skus),
            'diagnostico': diag,
        })

    return jsonify({
        "ok": True, "query": q,
        "formulas": formulas, "n_formulas": len(formulas),
        "skus": skus, "n_skus": len(skus),
        "presentaciones": pres, "n_presentaciones": len(pres),
        "stock_por_sku": stock_por_sku, "n_stock_skus": len(stock_por_sku),
    })


@bp.route("/api/admin/consolidar-producto", methods=["POST"])
def admin_consolidar_producto():
    """Consolida dos fórmulas del MISMO producto comercial en una sola.

    Sebastián 31-may-2026: 'LIP SERUM (PIB CHINO)' fue temporal (se acabó el PIB
    de siempre, usaron uno chino); ya volvieron a 'LIP SERUM VOLUMINIZADOR
    PEPTIDOS'. Mueve presentaciones (tonos) + lotes PENDIENTES + (opcional) receta
    del source al target, y desactiva el source. Los lotes ya producidos/iniciados
    quedan como historia. dry_run=true (default) solo REPORTA, no muta.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    from config import ADMIN_USERS as _AU
    if user not in _AU:
        return jsonify({'error': 'solo admin puede consolidar'}), 403
    d = request.get_json(silent=True) or {}
    source = (d.get('source') or '').strip()
    target = (d.get('target') or '').strip()
    aplicar = bool(d.get('aplicar'))
    copiar_receta = bool(d.get('copiar_receta'))
    if not source or not target or source == target:
        return jsonify({'error': 'source y target (distintos) requeridos'}), 400
    conn = get_db()
    c = conn.cursor()
    for nm in (source, target):
        if not c.execute("SELECT 1 FROM formula_headers WHERE producto_nombre=?", (nm,)).fetchone():
            return jsonify({'error': f"'{nm}' no existe en formula_headers"}), 404

    def _cnt(sql, p):
        try:
            return int(c.execute(sql, p).fetchone()[0] or 0)
        except Exception:
            return 0

    pres_source = [r[0] for r in c.execute(
        "SELECT presentacion_codigo FROM producto_presentaciones WHERE producto_nombre=?",
        (source,)).fetchall()]
    pres_target = set(r[0] for r in c.execute(
        "SELECT presentacion_codigo FROM producto_presentaciones WHERE producto_nombre=?",
        (target,)).fetchall())
    pres_conflict = [p for p in pres_source if p in pres_target]
    pres_mover = [p for p in pres_source if p not in pres_target]
    lotes_mover = _cnt(
        "SELECT COUNT(*) FROM produccion_programada WHERE producto=? "
        "AND COALESCE(estado,'') NOT IN ('cancelado','completado') AND inicio_real_at IS NULL",
        (source,))
    lotes_hist = _cnt(
        "SELECT COUNT(*) FROM produccion_programada WHERE producto=? "
        "AND (COALESCE(estado,'')='completado' OR inicio_real_at IS NOT NULL)", (source,))
    receta_source = _cnt("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (source,))
    receta_target = _cnt("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (target,))
    rep = {
        'ok': True, 'source': source, 'target': target,
        'presentaciones_a_mover': pres_mover,
        'presentaciones_en_conflicto': pres_conflict,
        'lotes_pendientes_a_mover': lotes_mover,
        'lotes_historicos_se_quedan': lotes_hist,
        'receta_source_items': receta_source,
        'receta_target_items': receta_target,
    }
    if not aplicar:
        rep['dry_run'] = True
        if receta_target == 0:
            rep['advertencia'] = ('El target NO tiene receta (formula_items). Tildá '
                                  '"copiar receta" para copiar la del temporal, o cargá la receta antes.')
        return jsonify(rep)

    # ── APLICAR ──
    if receta_target == 0 and not copiar_receta:
        rep['error'] = 'target sin receta · tildá copiar receta o cargá la receta primero'
        return jsonify(rep), 400
    if receta_target == 0 and copiar_receta and receta_source > 0:
        c.execute(
            "INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
            "SELECT ?, material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?",
            (target, source))
    for pc in pres_mover:
        c.execute(
            "UPDATE producto_presentaciones SET producto_nombre=? "
            "WHERE producto_nombre=? AND presentacion_codigo=?", (target, source, pc))
    c.execute(
        "UPDATE produccion_programada SET producto=? WHERE producto=? "
        "AND COALESCE(estado,'') NOT IN ('cancelado','completado') AND inicio_real_at IS NULL",
        (target, source))
    c.execute("UPDATE formula_headers SET activo=0 WHERE producto_nombre=?", (source,))
    audit_log(c, usuario=user, accion='CONSOLIDAR_PRODUCTO',
              tabla='formula_headers', registro_id=source,
              despues={'source': source, 'target': target,
                       'lotes_movidos': lotes_mover, 'pres_movidas': len(pres_mover),
                       'receta_copiada': bool(receta_target == 0 and copiar_receta)})
    conn.commit()
    rep['aplicado'] = True
    rep['mensaje'] = (f"Consolidado: '{source}' → '{target}'. {len(pres_mover)} presentaciones + "
                      f"{lotes_mover} lotes movidos. '{source}' desactivada.")
    return jsonify(rep)


@bp.route("/admin/diag-familia", methods=["GET"])
def admin_diag_familia_page():
    """Página read-only · radiografía de una familia de producto (Sebastián 31-may)."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/diag-familia")
    from flask import Response
    return Response(_DIAG_FAMILIA_HTML, mimetype="text/html")


_DIAG_FAMILIA_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Diagnóstico familia de producto · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1200px;margin:0 auto}
.card{background:#fff;border-radius:12px;padding:18px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:21px} h3{color:#0f766e;margin:0 0 8px}
input{padding:9px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;min-width:240px}
button{background:#0f766e;color:#fff;border:none;padding:9px 18px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
th{text-align:left;padding:7px 8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:6px 8px;border-bottom:1px solid #f1f5f9}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:#1e40af}
.muted{color:#64748b;font-size:12px}
.tag{padding:1px 7px;border-radius:5px;font-weight:700;font-size:11px}
</style></head><body>
<div class="wrap">
<a href="/modulos">&larr; Volver</a>
<div class="card">
  <h1>🔬 Diagnóstico familia de producto</h1>
  <div class="muted">Read-only · fórmulas + canónico + mapeo de SKUs + presentaciones. Para decidir cómo unificar nombres.</div>
  <div style="margin-top:12px"><input id="q" value="LIP SERUM" placeholder="ej. LIP SERUM, GLOSS, SUERO..."> <button onclick="ir()">Buscar</button></div>
</div>
<div class="card" style="border:1px solid #fca5a5">
  <h3 style="color:#b91c1c">🔗 Consolidar (unificar fórmulas del mismo producto)</h3>
  <div class="muted">Mueve presentaciones (tonos) + lotes PENDIENTES + (opcional) receta del temporal al definitivo y <b>desactiva</b> el temporal. Los lotes ya producidos quedan como historia. <b>Vista previa antes de aplicar.</b></div>
  <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px">
    <span>Desactivar (temporal):</span><input id="cs-source" placeholder="LIP SERUM (PIB CHINO)" style="min-width:260px">
    <span>→ Mantener (definitivo):</span><input id="cs-target" placeholder="LIP SERUM VOLUMINIZADOR PEPTIDOS" style="min-width:300px">
    <label style="font-size:12px"><input type="checkbox" id="cs-receta"> copiar receta si el definitivo no tiene</label>
    <button onclick="consPreview()">👁 Vista previa</button>
    <button onclick="consAplicar()" style="background:#b91c1c">Aplicar</button>
  </div>
  <div id="cons-out" style="margin-top:10px"></div>
</div>
<div id="out"></div>
</div>
<script>
function esc(s){return String(s==null?'':s).replace(/[&<>\"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c];});}
async function ir(){
  var q=document.getElementById('q').value.trim();
  var out=document.getElementById('out');
  if(!q){ out.innerHTML='<div class="card">Escribí algo</div>'; return; }
  out.innerHTML='<div class="card">Buscando…</div>';
  try{
    var r=await fetch('/api/admin/diag-familia-producto?q='+encodeURIComponent(q),{cache:'no-store'});
    var d=await r.json();
    if(!r.ok||!d.ok){ out.innerHTML='<div class="card" style="color:#dc2626">Error: '+esc((d&&d.error)||r.status)+'</div>'; return; }
    var h='';
    // Fórmulas
    h+='<div class="card"><h3>📋 Fórmulas ('+d.n_formulas+')</h3>';
    h+='<table><tr><th>Producto (formula_headers)</th><th>Canónico</th><th>Variante</th><th>Activo</th><th>Lote kg</th><th>codigo_pt</th></tr>';
    d.formulas.forEach(function(f){ h+='<tr><td class="mono">'+esc(f.producto_nombre)+'</td><td>'+esc(f.producto_canonico||'—')+'</td><td>'+esc(f.variante_label||'—')+'</td><td>'+(f.activo?'sí':'<span style="color:#b91c1c">no</span>')+'</td><td>'+f.lote_size_kg+'</td><td>'+esc(f.codigo_pt||'')+'</td></tr>'; });
    if(!d.formulas.length) h+='<tr><td colspan="6" class="muted">sin fórmulas</td></tr>';
    h+='</table></div>';
    // SKUs
    h+='<div class="card"><h3>🔗 SKUs mapeados ('+d.n_skus+')</h3>';
    h+='<table><tr><th>SKU</th><th>Mapea a producto</th><th>Tono</th><th>Regalo</th><th>Activo</th></tr>';
    d.skus.forEach(function(s){ h+='<tr><td class="mono">'+esc(s.sku)+'</td><td>'+esc(s.producto_nombre)+'</td><td>'+esc(s.tono_label||'—')+'</td><td>'+(s.es_regalo?'🎁':'')+'</td><td>'+(s.activo?'sí':'no')+'</td></tr>'; });
    if(!d.skus.length) h+='<tr><td colspan="5" class="muted">sin SKUs · las ventas no se asocian</td></tr>';
    h+='</table></div>';
    // Presentaciones
    h+='<div class="card"><h3>📐 Presentaciones / tonos ('+d.n_presentaciones+')</h3>';
    h+='<table><tr><th>Producto</th><th>Presentación</th><th>Etiqueta</th><th>ml</th><th>Envase</th><th>Fija</th></tr>';
    d.presentaciones.forEach(function(p){ h+='<tr><td>'+esc(p.producto_nombre)+'</td><td class="mono">'+esc(p.presentacion_codigo)+'</td><td>'+esc(p.etiqueta)+'</td><td>'+p.volumen_ml+'</td><td class="mono">'+esc(p.envase_codigo||'—')+'</td><td>'+(p.cantidad_fija_uds||'')+'</td></tr>'; });
    if(!d.presentaciones.length) h+='<tr><td colspan="6" class="muted">sin presentaciones</td></tr>';
    h+='</table></div>';
    // Stock por SKU · "dice que no hay pero en Shopify sí"
    var sps=d.stock_por_sku||[];
    h+='<div class="card"><h3>📦 Stock por SKU ('+sps.length+') · qué ve el motor de necesidades</h3>';
    h+='<div class="muted">Regla: si hay conteo CC para el SKU, ESE manda y se IGNORA el snapshot Shopify. Filas con 0 disponibles se descartan. Si "dice que no hay y en Shopify sí", mirá la columna diagnóstico.</div>';
    h+='<table><tr><th>SKU</th><th>Mapeado</th><th>Resuelto (motor)</th><th>Fuente</th><th>CC disp.</th><th>Shopify disp.</th><th>Empresa</th><th>Diagnóstico</th></tr>';
    sps.forEach(function(s){
      var resColor = s.resolved_uds>0 ? '#15803d' : '#b91c1c';
      var diagColor = (s.shopify_uds_disponible>0 && s.resolved_uds<s.shopify_uds_disponible) ? '#b45309'
                    : (s.resolved_uds<=0 ? '#b91c1c' : '#475569');
      h+='<tr><td class="mono">'+esc(s.sku)+'</td>'
        +'<td>'+(s.mapeado?'sí':'<span style="color:#b91c1c">NO</span>')+'</td>'
        +'<td style="font-weight:700;color:'+resColor+'">'+s.resolved_uds+'</td>'
        +'<td>'+esc(s.fuente||'—')+'</td>'
        +'<td>'+s.cc_uds_disponible+'</td>'
        +'<td>'+s.shopify_uds_disponible+'</td>'
        +'<td class="muted">'+esc((s.empresas||[]).join(', ')||'—')+'</td>'
        +'<td style="color:'+diagColor+'">'+esc(s.diagnostico)+'</td></tr>';
    });
    if(!sps.length) h+='<tr><td colspan="8" class="muted">sin SKUs con stock para revisar</td></tr>';
    h+='</table></div>';
    out.innerHTML=h;
  }catch(e){ out.innerHTML='<div class="card" style="color:#dc2626">Error red: '+esc(e.message)+'</div>'; }
}
async function _csrf(){ try{ var r=await fetch('/api/csrf-token',{credentials:'same-origin'}); if(r.ok){ var d=await r.json(); return d.csrf_token||''; } }catch(_){} return ''; }
function _renderRep(d){
  var h='<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;font-size:12px">';
  if(d.mensaje) h+='<div style="color:#15803d;font-weight:700;margin-bottom:6px">✓ '+esc(d.mensaje)+'</div>';
  if(d.error) h+='<div style="color:#b91c1c;font-weight:700;margin-bottom:6px">✕ '+esc(d.error)+'</div>';
  h+='Presentaciones a mover: <b>'+((d.presentaciones_a_mover||[]).length)+'</b>'+(((d.presentaciones_en_conflicto||[]).length)?' · ⚠ en conflicto: '+d.presentaciones_en_conflicto.join(', '):'')+'<br>';
  h+='Lotes pendientes a mover: <b>'+(d.lotes_pendientes_a_mover||0)+'</b> · históricos que se quedan: '+(d.lotes_historicos_se_quedan||0)+'<br>';
  h+='Receta · temporal: '+(d.receta_source_items||0)+' items · <b>definitivo: '+(d.receta_target_items||0)+' items</b><br>';
  if(d.advertencia) h+='<div style="color:#b45309;margin-top:4px">⚠ '+esc(d.advertencia)+'</div>';
  h+='</div>';
  return h;
}
async function _consCall(aplicar){
  var s=document.getElementById('cs-source').value.trim(), t=document.getElementById('cs-target').value.trim();
  var rec=document.getElementById('cs-receta').checked, o=document.getElementById('cons-out');
  if(!s||!t){ o.innerHTML='<span style="color:#dc2626">Completá ambos nombres</span>'; return; }
  if(aplicar && !confirm('¿Aplicar la consolidación?\\n\\nDesactiva "'+s+'" y mueve presentaciones + lotes pendientes a "'+t+'".\\nNo se deshace fácil.')) return;
  o.innerHTML='Procesando…';
  try{
    var r=await fetch('/api/admin/consolidar-producto',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':await _csrf()},credentials:'same-origin',body:JSON.stringify({source:s,target:t,aplicar:aplicar,copiar_receta:rec})});
    var d=await r.json();
    o.innerHTML=_renderRep(d);
    if(d.aplicado){ setTimeout(ir,700); }
  }catch(e){ o.innerHTML='<span style="color:#dc2626">Error red: '+esc(e.message)+'</span>'; }
}
function consPreview(){ _consCall(false); }
function consAplicar(){ _consCall(true); }
ir();
</script>
</body></html>"""


@bp.route("/api/admin/b2b/cliente/<cliente_id>/envases", methods=["GET"])
def admin_b2b_envases_cliente(cliente_id):
    """FEATURE B2B 24-may-2026 · whitelist envases por cliente.
    Devuelve envases actualmente permitidos para el cliente. Lista vacía
    significa "todos los activos" (default permisivo)."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT cbe.envase_codigo, cbe.envase_descripcion,
                      cbe.activo, COALESCE(cbe.notas,''),
                      mee.descripcion AS mee_desc
               FROM clientes_b2b_envases cbe
               LEFT JOIN maestro_mee mee
                 ON UPPER(TRIM(mee.codigo)) = UPPER(TRIM(cbe.envase_codigo))
               WHERE cbe.cliente_id = ?
               ORDER BY cbe.envase_codigo""",
            (cliente_id,),
        ).fetchall()
    except Exception:
        rows = []
    return jsonify({
        'cliente_id': cliente_id,
        'modo': 'whitelist' if rows else 'permisivo',
        'items': [{
            'envase_codigo': r[0],
            'envase_descripcion': r[1] or r[4] or '',
            'activo': bool(r[2]),
            'notas': r[3] or '',
        } for r in rows],
        'total': len(rows),
    })


@bp.route("/api/admin/b2b/cliente/<cliente_id>/envases", methods=["POST"])
def admin_b2b_envases_cliente_set(cliente_id):
    """Asigna envases permitidos para un cliente · operación REPLACE bulk:
    el set recibido reemplaza al anterior. Body: {items: [{envase_codigo,
    envase_descripcion?, notas?}], reemplazar: true|false}"""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    body = request.get_json(silent=True) or {}
    items = body.get('items') or []
    reemplazar = bool(body.get('reemplazar', True))
    if not isinstance(items, list):
        return jsonify({'error': 'items debe ser lista'}), 400
    conn = get_db()
    cur = conn.cursor()
    # Validar todos los envases existen y son MEE activos antes de empezar
    codigos_norm = []
    for it in items:
        cod = (it.get('envase_codigo') or '').strip().upper()
        if not cod:
            continue
        existe = cur.execute(
            "SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo)) = ? AND COALESCE(estado,'Activo')='Activo'",
            (cod,),
        ).fetchone()
        if not existe:
            return jsonify({'error': f"envase '{cod}' no existe o inactivo en maestro_mee"}), 404
        codigos_norm.append({
            'envase_codigo': cod,
            'envase_descripcion': (it.get('envase_descripcion') or '').strip(),
            'notas': (it.get('notas') or '').strip(),
        })
    creados, actualizados, desactivados = 0, 0, 0
    if reemplazar:
        # Desactivar los que NO estén en la nueva lista
        codigos_nuevos = {x['envase_codigo'] for x in codigos_norm}
        existing = cur.execute(
            "SELECT envase_codigo FROM clientes_b2b_envases WHERE cliente_id = ? AND activo = 1",
            (cliente_id,),
        ).fetchall()
        for (ec,) in existing:
            if (ec or '').upper().strip() not in codigos_nuevos:
                cur.execute(
                    "UPDATE clientes_b2b_envases SET activo = 0 WHERE cliente_id = ? AND envase_codigo = ?",
                    (cliente_id, ec),
                )
                desactivados += 1
    for it in codigos_norm:
        existing = cur.execute(
            "SELECT id FROM clientes_b2b_envases WHERE cliente_id = ? AND envase_codigo = ?",
            (cliente_id, it['envase_codigo']),
        ).fetchone()
        if existing:
            cur.execute(
                """UPDATE clientes_b2b_envases
                     SET activo = 1, envase_descripcion = ?, notas = ?
                   WHERE id = ?""",
                (it['envase_descripcion'], it['notas'], existing[0]),
            )
            actualizados += 1
        else:
            cur.execute(
                """INSERT INTO clientes_b2b_envases
                     (cliente_id, envase_codigo, envase_descripcion, notas, activo)
                   VALUES (?, ?, ?, ?, 1)""",
                (cliente_id, it['envase_codigo'], it['envase_descripcion'], it['notas']),
            )
            creados += 1
    audit_log(cur, usuario=user, accion='B2B_ENVASES_WHITELIST',
              tabla='clientes_b2b_envases', registro_id=cliente_id,
              despues={'creados': creados, 'actualizados': actualizados,
                       'desactivados': desactivados,
                       'total_final': len(codigos_norm)})
    conn.commit()
    return jsonify({'ok': True, 'cliente_id': cliente_id,
                    'creados': creados, 'actualizados': actualizados,
                    'desactivados': desactivados,
                    'total_activos': len(codigos_norm)})


@bp.route("/api/b2b/envases-disponibles", methods=["GET"])
def b2b_envases_disponibles():
    """FEATURE B2B multi-envase 24-may-2026 · catálogo de envases que un
    cliente B2B puede solicitar. Filtros opcionales por producto (futuro,
    cuando se mappee envase↔producto). Por ahora lista maestro_mee activos
    de categoría 'Envase' o 'envase'.

    Accesible por sesión Portal o backoffice (cualquier cliente B2B necesita
    poder ver el catálogo al armar un pedido).
    """
    # Permitir tanto sesión portal como backoffice
    portal_cid = session.get('portal_cliente_id')
    backoffice_user = session.get('compras_user')
    if not portal_cid and not backoffice_user:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    # Si es sesión portal · filtrar por whitelist del cliente (si existe).
    # Backoffice ve todo (admin).
    filtrar_por_cliente = portal_cid if portal_cid and not backoffice_user else None
    if filtrar_por_cliente:
        try:
            tiene_wl = conn.execute(
                """SELECT COUNT(*) FROM clientes_b2b_envases
                   WHERE cliente_id = ? AND activo = 1""",
                (filtrar_por_cliente,),
            ).fetchone()
            if tiene_wl and int(tiene_wl[0] or 0) > 0:
                rows = conn.execute(
                    """SELECT m.codigo, m.descripcion, m.categoria,
                              COALESCE(m.unidad,''), COALESCE(m.stock_actual,0)
                       FROM maestro_mee m
                       INNER JOIN clientes_b2b_envases cbe
                         ON UPPER(TRIM(cbe.envase_codigo)) = UPPER(TRIM(m.codigo))
                       WHERE COALESCE(m.estado,'Activo') = 'Activo'
                         AND cbe.cliente_id = ? AND cbe.activo = 1
                       ORDER BY m.descripcion ASC""",
                    (filtrar_por_cliente,),
                ).fetchall()
                return jsonify({
                    'items': [{
                        'codigo': r[0], 'descripcion': r[1] or '',
                        'categoria': r[2] or '', 'unidad': r[3] or '',
                        'stock_actual': float(r[4] or 0),
                    } for r in rows],
                    'total': len(rows),
                    'filtrado_por_cliente': filtrar_por_cliente,
                })
        except Exception:
            pass  # mig 173 no aplicada · fallback al listado total
    try:
        rows = conn.execute(
            """SELECT codigo, descripcion, categoria,
                      COALESCE(unidad,''), COALESCE(stock_actual,0)
               FROM maestro_mee
               WHERE COALESCE(estado,'Activo') = 'Activo'
                 AND LOWER(COALESCE(categoria,'')) LIKE '%envase%'
               ORDER BY descripcion ASC"""
        ).fetchall()
    except Exception:
        rows = []
    return jsonify({
        'items': [{
            'codigo': r[0],
            'descripcion': r[1] or '',
            'categoria': r[2] or '',
            'unidad': r[3] or '',
            'stock_actual': float(r[4] or 0),
        } for r in rows],
        'total': len(rows),
    })


@bp.route("/api/admin/b2b/lote/<int:lote_id>/desglose", methods=["GET"])
def admin_b2b_lote_desglose(lote_id):
    """FEATURE B2B 24-may-2026 · dado un lote de produccion_programada,
    devuelve el desglose DTC vs B2B: kg total del lote, qué porción es
    B2B sumada de qué pedidos, qué porción es DTC (= total - B2B).

    Útil para que en planta sepan: "este lote LBHA de 5kg = 2kg DTC +
    3kg Fernando (pedido #42, envase 250ml)".
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    lote = conn.execute(
        """SELECT id, producto, fecha_programada, COALESCE(cantidad_kg,0),
                  COALESCE(kg_real,0), estado, origen
           FROM produccion_programada WHERE id = ?""",
        (lote_id,),
    ).fetchone()
    if not lote:
        return jsonify({'error': 'lote no existe'}), 404
    kg_total = float(lote[3] or 0)
    aportes_b2b = []
    kg_b2b_total = 0.0
    try:
        for r in conn.execute(
            """SELECT pbl.pedido_b2b_id, pbl.kg_aporte, pbl.unidades_aporte,
                      pbl.ml_unidad, pbl.envase_codigo, pbl.modo,
                      pbl.cliente_nombre,
                      pb.estado, pb.fecha_estimada, pb.notas,
                      mee.descripcion
               FROM pedidos_b2b_lote pbl
               LEFT JOIN pedidos_b2b pb ON pb.id = pbl.pedido_b2b_id
               LEFT JOIN maestro_mee mee ON UPPER(TRIM(mee.codigo)) = UPPER(TRIM(COALESCE(pbl.envase_codigo,'')))
               WHERE pbl.lote_produccion_id = ?
               ORDER BY pbl.kg_aporte DESC""",
            (lote_id,),
        ).fetchall():
            kg = float(r[1] or 0)
            kg_b2b_total += kg
            aportes_b2b.append({
                'pedido_id': r[0],
                'kg_aporte': kg,
                'unidades_aporte': int(r[2] or 0),
                'ml_unidad': float(r[3] or 0),
                'envase_codigo': r[4] or '',
                'envase_descripcion': r[10] or '',
                'modo': r[5],
                'cliente_nombre': r[6] or '',
                'estado_pedido': r[7] or '',
                'fecha_estimada': (r[8] or '')[:10],
                'notas': r[9] or '',
            })
    except Exception:
        pass  # mig 171/172 no aplicada todavía
    kg_dtc = max(kg_total - kg_b2b_total, 0)
    pct_b2b = round(100.0 * kg_b2b_total / kg_total, 1) if kg_total > 0 else 0
    return jsonify({
        'lote_id': lote_id,
        'producto': lote[1],
        'fecha_programada': (lote[2] or '')[:10],
        'estado': lote[5] or '',
        'origen': lote[6] or '',
        'kg_total': kg_total,
        'kg_real': float(lote[4] or 0),
        'kg_b2b': round(kg_b2b_total, 2),
        'kg_dtc': round(kg_dtc, 2),
        'pct_b2b': pct_b2b,
        'aportes_b2b': aportes_b2b,
        'n_pedidos_b2b': len(aportes_b2b),
    })


def _check_mp_para_pedido_b2b(c, producto, kg_b2b):
    """Verifica si hay MP suficiente para producir kg_b2b del producto.

    Sebastián 19-may-2026: queremos avisar al crear pedido B2B si faltan MP,
    sin bloquear la creación. El usuario decide si crea igual + genera SOL,
    o ajusta cantidad antes.

    Reusa el patrón de /api/plan/factibilidad pero focalizado a UN pedido:
    explota la fórmula del producto por los kg pedidos y compara con stock
    actual = SUM(movimientos) sin descontar otras producciones programadas
    (heurística simple · si querés precisión, mirá /api/plan/factibilidad).

    Returns dict:
        {ok: bool, mps_faltantes: [{material_id, material_nombre,
                                     necesario_g, disponible_g, faltante_g}],
         sin_formula: bool, lote_size_kg, n_lotes}
    """
    if kg_b2b <= 0:
        return {"ok": True, "mps_faltantes": [], "sin_formula": False,
                "lote_size_kg": 0, "n_lotes": 0}

    # Fórmula + lote_size del producto
    items = c.execute(
        """SELECT fi.material_id,
                  COALESCE(fi.material_nombre,'') AS mat_nom,
                  COALESCE(fi.cantidad_g_por_lote,0) AS cant_g,
                  COALESCE(fi.porcentaje,0) AS pct,
                  COALESCE(fh.lote_size_kg,0) AS lote_kg
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo,1)=1
             AND UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(?))
             AND fi.material_id IS NOT NULL AND TRIM(fi.material_id)!=''""",
        (producto,),
    ).fetchall()
    if not items:
        return {"ok": True, "mps_faltantes": [], "sin_formula": True,
                "lote_size_kg": 0, "n_lotes": 0}

    lote_kg = float(items[0][4] or 0)
    n_lotes = kg_b2b / lote_kg if lote_kg > 0 else 1.0

    # Necesidad por MP
    requeridos = []  # [(material_id, nombre, gramos)]
    for mid_raw, mnom, cant_g, pct, _lk in items:
        mid = str(mid_raw).strip()
        if mid == 'MPAGUALI01':  # agua = consumible infinito
            continue
        nec_g = float(cant_g or 0)
        if nec_g <= 0 and pct and lote_kg > 0:
            nec_g = (float(pct) / 100.0) * lote_kg * 1000.0
        if nec_g <= 0:
            continue
        requeridos.append((mid, str(mnom)[:60], round(nec_g * n_lotes, 2)))

    if not requeridos:
        return {"ok": True, "mps_faltantes": [], "sin_formula": False,
                "lote_size_kg": lote_kg, "n_lotes": round(n_lotes, 3)}

    # Stock actual = SUM(movimientos) por material_id requerido
    ids = [r[0] for r in requeridos]
    placeholders = ','.join(['?'] * len(ids))
    stock_g = {}
    for r in c.execute(
        f"""SELECT material_id,
                   COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad
                                     WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad
                                     ELSE 0 END),0)
            FROM movimientos
            WHERE material_id IN ({placeholders})
            GROUP BY material_id""",
        ids,
    ).fetchall():
        stock_g[str(r[0]).strip()] = max(float(r[1] or 0), 0.0)

    # Comparar
    faltantes = []
    for mid, mnom, need in requeridos:
        disp = stock_g.get(mid, 0.0)
        if need - disp > 0.01:
            faltantes.append({
                "material_id": mid,
                "material_nombre": mnom,
                "necesario_g": round(need, 1),
                "disponible_g": round(disp, 1),
                "faltante_g": round(need - disp, 1),
            })
    return {
        "ok": len(faltantes) == 0,
        "mps_faltantes": faltantes,
        "sin_formula": False,
        "lote_size_kg": lote_kg,
        "n_lotes": round(n_lotes, 3),
    }


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
    # FEATURE B2B multi-envase 24-may-2026 · cliente puede solicitar
    # envase específico (e.g. Fernando 500ml branded). Default = vacío
    # → usa presentación default del producto.
    envase_codigo = (body.get("envase_codigo") or "").strip().upper()
    envase_notas = (body.get("envase_notas") or "").strip()

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

    # Validar envase si fue solicitado (debe existir en maestro_mee).
    if envase_codigo:
        env_row = cur.execute(
            "SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo)) = ?",
            (envase_codigo,),
        ).fetchone()
        if not env_row:
            return jsonify({"error": f"envase '{envase_codigo}' no existe en maestro_mee"}), 404
        # FEATURE B2B 24-may-2026 · whitelist envase↔cliente (mig 173).
        # Si el cliente tiene ≥1 fila en clientes_b2b_envases → solo esos
        # son válidos. Sin filas → todos activos permitidos (backward-compat).
        try:
            tiene_wl = cur.execute(
                """SELECT COUNT(*) FROM clientes_b2b_envases
                   WHERE cliente_id = ? AND activo = 1""",
                (cliente_id,),
            ).fetchone()
            if tiene_wl and int(tiene_wl[0] or 0) > 0:
                permitido = cur.execute(
                    """SELECT 1 FROM clientes_b2b_envases
                       WHERE cliente_id = ? AND UPPER(TRIM(envase_codigo)) = ?
                         AND activo = 1""",
                    (cliente_id, envase_codigo),
                ).fetchone()
                if not permitido:
                    return jsonify({"error": f"envase '{envase_codigo}' no permitido para cliente {cliente_id}",
                                    "codigo": "ENVASE_NO_PERMITIDO"}), 403
        except Exception:
            pass  # mig 173 no aplicada · default permisivo

    try:
        cur.execute(
            """INSERT INTO pedidos_b2b
                 (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                  ml_unidad, fecha_estimada, notas, creado_por,
                  envase_codigo, envase_notas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, cliente_nombre, producto, cantidad, ml,
             fecha_estimada or None, notas, user, envase_codigo, envase_notas),
        )
    except Exception:
        # Mig 172 puede no estar aplicada · fallback al INSERT viejo.
        cur.execute(
            """INSERT INTO pedidos_b2b
                 (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                  ml_unidad, fecha_estimada, notas, creado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, cliente_nombre, producto, cantidad, ml,
             fecha_estimada or None, notas, user),
        )
    pid = cur.lastrowid
    audit_log(cur, usuario=user, accion="CREAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              despues={"cliente_id": cliente_id, "producto": producto,
                       "cantidad_uds": cantidad, "fecha": fecha_estimada,
                       "envase_codigo": envase_codigo})
    conn.commit()

    # Sebastián 15-may-2026: integrar el pedido B2B al plan AL INSTANTE.
    # Híbrido: si hay un lote canónico del mismo producto cerca de la
    # fecha que necesita el cliente (±10d), le suma los kg; si no, crea
    # un lote dedicado. Ver _integrar_pedido_b2b_al_plan.
    kg_b2b = round(cantidad * ml / 1000.0, 2)
    integracion = None
    try:
        integracion = _integrar_pedido_b2b_al_plan(
            cur, pid, producto, kg_b2b, fecha_estimada, cliente_nombre, user,
            unidades=cantidad, ml_unidad=ml, envase_codigo=envase_codigo)
        conn.commit()
    except Exception as _e:
        # La integración es best-effort · si falla, el pedido igual queda
        # registrado y se puede agendar a mano. rollback() descarta los
        # writes parciales de la integración (el pedido ya está committeado).
        try:
            conn.rollback()
        except Exception:
            pass
        integracion = {"error": str(_e)[:200]}

    # Sebastián 19-may-2026: check de MP non-blocking · avisa si faltan MPs
    # para producir el pedido. No bloquea la creación · el usuario decide si
    # ajusta cantidad o genera SOL a Compras. Si el check falla, sigue OK.
    mp_check = None
    try:
        mp_check = _check_mp_para_pedido_b2b(cur, producto, kg_b2b)
    except Exception as _e:
        mp_check = {"ok": True, "error": str(_e)[:200], "mps_faltantes": []}

    return jsonify({"ok": True, "id": pid, "kg_b2b": kg_b2b,
                    "integracion_plan": integracion,
                    "mp_check": mp_check}), 201


def _registrar_evento_prod(cur, produccion_id, tipo, detalles='', usuario=''):
    """Inserta evento estructurado en produccion_eventos.

    Reemplaza la práctica de concatenar a observaciones (que acumulaba
    KB de basura). Para mostrar timeline limpio en UI.

    Args:
        cur: cursor BD
        produccion_id: int
        tipo: str (e.g. 'CANCELADO_REGEN', 'B2B_SUMADO', 'KG_EDITADO',
              'PAUSADO', 'REPROGRAMADO', 'BLOQUEADO', etc.)
        detalles: str humano corto (e.g. '+50kg B2B Fernando')
        usuario: quien lo hizo
    """
    if not produccion_id or not tipo:
        return
    try:
        cur.execute(
            """INSERT INTO produccion_eventos
                 (produccion_id, tipo, detalles, usuario)
               VALUES (?, ?, ?, ?)""",
            (int(produccion_id), tipo[:50], (detalles or '')[:500],
             (usuario or '')[:80]),
        )
    except Exception:
        pass  # mig 178 no aplicada · skip silencioso


@bp.route("/api/produccion/<int:pid>/eventos", methods=["GET"])
def produccion_eventos_listar(pid):
    """Timeline estructurado de una producción · todos los eventos
    del histórico (cancelaciones, ajustes, B2B sumado, etc.) ordenados
    cronológicamente. Reemplaza el wall-of-text de observaciones.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); cur = conn.cursor()
    try:
        rows = cur.execute(
            """SELECT id, tipo, COALESCE(detalles,''),
                      COALESCE(usuario,''), fecha_at
               FROM produccion_eventos
               WHERE produccion_id = ?
               ORDER BY fecha_at DESC, id DESC
               LIMIT 200""",
            (pid,),
        ).fetchall()
    except Exception:
        rows = []
    items = [{
        'id': r[0], 'tipo': r[1], 'detalles': r[2],
        'usuario': r[3], 'fecha_at': r[4],
    } for r in rows]
    return jsonify({'produccion_id': pid, 'eventos': items, 'total': len(items)})


def _regenerar_distribucion_lote(cur, lote_id):
    """Regenera la etiqueta distribucion_resumen del lote con desglose
    DTC + cada aporte B2B. Llamar después de cada INSERT/DELETE en
    pedidos_b2b_lote para mantener la observación al día.

    Formato salida:
      'DTC: 150 kg + Fernando Mesa: 350 kg + Kelly Guerra: 150 kg
       · TOTAL 650 kg · 3 partes'
    """
    if not lote_id:
        return
    try:
        # Total del lote
        row = cur.execute(
            "SELECT COALESCE(cantidad_kg, 0) FROM produccion_programada WHERE id = ?",
            (lote_id,),
        ).fetchone()
        if not row:
            return
        kg_total = float(row[0] or 0)
        # Aportes B2B agrupados por cliente
        aportes = cur.execute(
            """SELECT COALESCE(cliente_nombre, '') AS cli,
                      SUM(kg_aporte) AS kg,
                      COUNT(*) AS n_pedidos
               FROM pedidos_b2b_lote
               WHERE lote_produccion_id = ?
               GROUP BY COALESCE(cliente_nombre, '')
               ORDER BY SUM(kg_aporte) DESC""",
            (lote_id,),
        ).fetchall()
        partes = []
        kg_b2b_total = 0.0
        for cli, kg, n in aportes:
            kg_f = float(kg or 0)
            if kg_f <= 0:
                continue
            label = (cli or 'B2B sin nombre')
            n_pedidos = int(n or 0)
            sufijo = f' ({n_pedidos} pedidos)' if n_pedidos > 1 else ''
            partes.append(f'{label}: {kg_f:.1f} kg{sufijo}')
            kg_b2b_total += kg_f
        kg_dtc = max(kg_total - kg_b2b_total, 0)
        # Si no hay aportes B2B, el lote es 100% DTC
        if not partes:
            resumen = f'DTC: {kg_total:.1f} kg · 1 parte'
        else:
            if kg_dtc > 0.01:
                resumen = f'DTC: {kg_dtc:.1f} kg + ' + ' + '.join(partes)
            else:
                resumen = ' + '.join(partes)
            resumen += f' · TOTAL {kg_total:.1f} kg · {len(partes) + (1 if kg_dtc > 0.01 else 0)} partes'
        cur.execute(
            "UPDATE produccion_programada SET distribucion_resumen = ? WHERE id = ?",
            (resumen[:500], lote_id),
        )
    except Exception:
        pass  # mig 176 no aplicada · skip


def _integrar_pedido_b2b_al_plan(cur, pedido_id, producto, kg_b2b,
                                   fecha_estimada, cliente_nombre, user,
                                   unidades=0, ml_unidad=0, envase_codigo=''):
    """Ubica un pedido B2B en el calendario de producción.

    Sebastián 15-may-2026 · modo HÍBRIDO:
    - Si hay un lote canónico del mismo producto a ±10 días de la fecha
      objetivo de producción → suma los kg a ese lote (y lo marca como
      eos_plan para que el regenerador NO lo borre).
    - Si no hay ninguno cerca → crea un lote dedicado origen='eos_b2b'
      (también sobrevive al regenerador).

    Fecha objetivo = fecha_estimada del cliente − 10 días (margen para
    producir + QC + despacho). Sin fecha → hoy + 7d.

    Sebastián 24-may-2026 · trazabilidad B2B → DTC: además del UPDATE
    en produccion_programada, registra el aporte en `pedidos_b2b_lote`
    para que la UI pueda mostrar desglose DTC vs B2B sin parsear el
    string de observaciones. Args nuevos `unidades`, `ml_unidad`,
    `envase_codigo` opcionales (default 0/'' → backward compat).
    """
    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()
    if fecha_estimada and _valida_fecha_iso(fecha_estimada):
        f_target = _date.fromisoformat(fecha_estimada[:10]) - _td(days=10)
    else:
        f_target = hoy + _td(days=7)
    if f_target < hoy:
        f_target = hoy + _td(days=3)

    # Buscar lote canónico del mismo producto cerca de f_target (±10d)
    cercano = cur.execute(
        """SELECT id, fecha_programada, COALESCE(cantidad_kg,0)
           FROM produccion_programada
           WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
             AND estado IN ('pendiente','programado','esperando_recurso')
             AND inicio_real_at IS NULL AND fin_real_at IS NULL
             AND ABS(julianday(fecha_programada) - julianday(?)) <= 10
           ORDER BY ABS(julianday(fecha_programada) - julianday(?)) ASC
           LIMIT 1""",
        (producto, f_target.isoformat(), f_target.isoformat()),
    ).fetchone()

    if cercano:
        lid, lfecha = cercano[0], cercano[1]
        # BUG-22 fix · 19-may-2026 audit Planta PERFECTA: el cálculo previo
        # leía cantidad_kg en Python (`lkg`), sumaba kg_b2b y escribía con
        # UPDATE SET cantidad_kg=?. Dos pedidos B2B concurrentes del mismo
        # producto leían el mismo lkg y el último write ganaba (lost update,
        # uno de los aportes desaparecía). Ahora el UPDATE es atómico vía
        # `SET cantidad_kg = COALESCE(cantidad_kg,0) + ?` · cualquier orden
        # de commits suma correctamente.
        cur.execute(
            """UPDATE produccion_programada
               SET cantidad_kg = COALESCE(cantidad_kg, 0) + ?,
                   origen = 'eos_plan',
                   observaciones = COALESCE(observaciones,'') ||
                     ' · +' || ? || 'kg B2B ' || ? || ' (pedido #' || ? || ')'
               WHERE id = ?""",
            (kg_b2b, kg_b2b, cliente_nombre, pedido_id, lid),
        )
        # Releer el total real post-UPDATE para reportarlo (los concurrentes
        # pueden haber sumado también en este intervalo · valor canónico
        # viene de la BD, no de la copia local).
        row_post = cur.execute(
            "SELECT cantidad_kg FROM produccion_programada WHERE id=?",
            (lid,),
        ).fetchone()
        nuevo_kg = float(row_post[0] or 0) if row_post else 0
        # Trazabilidad estructurada (mig 171) · INSERT OR REPLACE para
        # idempotencia si el mismo pedido se re-integra (re-aprobación).
        try:
            cur.execute(
                """INSERT OR REPLACE INTO pedidos_b2b_lote
                     (pedido_b2b_id, lote_produccion_id, kg_aporte,
                      unidades_aporte, ml_unidad, envase_codigo, modo,
                      cliente_nombre)
                   VALUES (?, ?, ?, ?, ?, ?, 'sumado_a_lote_canonico', ?)""",
                (pedido_id, lid, kg_b2b, unidades, ml_unidad,
                 envase_codigo, cliente_nombre),
            )
        except Exception:
            pass  # tabla puede no existir aún en tests viejos
        audit_log(cur, usuario=user, accion="B2B_SUMADO_A_LOTE",
                  tabla="produccion_programada", registro_id=lid,
                  despues={"pedido_b2b": pedido_id, "kg_sumados": kg_b2b,
                           "kg_total": nuevo_kg})
        # FEATURE 24-may noche · regenerar etiqueta de distribución legible
        _regenerar_distribucion_lote(cur, lid)
        # Refactor observaciones · evento estructurado
        _registrar_evento_prod(cur, lid, 'B2B_SUMADO',
            f'+{kg_b2b}kg · {cliente_nombre or "B2B"} · pedido #{pedido_id}',
            user)
        return {"modo": "sumado_a_lote_canonico", "lote_id": lid,
                "fecha": (lfecha or "")[:10], "kg_total": nuevo_kg,
                "kg_b2b": kg_b2b}

    # Sin lote cercano → lote dedicado
    f_real = _proxima_fecha_habil(cur, f_target, prefer_mwf=False,
                                   lote_kg=kg_b2b, producto_nombre=producto)
    if f_real is None:
        f_real = f_target
    cur.execute(
        """INSERT INTO produccion_programada
             (producto, fecha_programada, cantidad_kg, estado, origen,
              lotes, observaciones)
           VALUES (?, ?, ?, 'programado', 'eos_b2b', 1, ?)""",
        (producto, f_real.isoformat(), kg_b2b,
         f"Pedido B2B {cliente_nombre} · #{pedido_id} · "
         f"entrega estimada {fecha_estimada or 's/f'}"),
    )
    nuevo_lote = cur.lastrowid
    # Trazabilidad estructurada · 100% del lote es B2B en este caso
    try:
        cur.execute(
            """INSERT OR REPLACE INTO pedidos_b2b_lote
                 (pedido_b2b_id, lote_produccion_id, kg_aporte,
                  unidades_aporte, ml_unidad, envase_codigo, modo,
                  cliente_nombre)
               VALUES (?, ?, ?, ?, ?, ?, 'lote_dedicado', ?)""",
            (pedido_id, nuevo_lote, kg_b2b, unidades, ml_unidad,
             envase_codigo, cliente_nombre),
        )
    except Exception:
        pass
    audit_log(cur, usuario=user, accion="B2B_LOTE_DEDICADO",
              tabla="produccion_programada", registro_id=nuevo_lote,
              despues={"pedido_b2b": pedido_id, "producto": producto,
                       "kg": kg_b2b, "fecha": f_real.isoformat()})
    _regenerar_distribucion_lote(cur, nuevo_lote)
    # Refactor observaciones · evento estructurado
    _registrar_evento_prod(cur, nuevo_lote, 'CREADO_B2B_DEDICADO',
        f'Pedido B2B {cliente_nombre or "?"} · pedido #{pedido_id} · {kg_b2b}kg',
        user)
    return {"modo": "lote_dedicado", "lote_id": nuevo_lote,
            "fecha": f_real.isoformat(), "kg_b2b": kg_b2b}


def _revertir_pedido_b2b_del_plan(cur, pedido_id, user):
    """Revierte la integración de un pedido B2B al plan cuando se cancela.

    Espejo de _integrar_pedido_b2b_al_plan:
    - Lote dedicado (origen='eos_b2b'): se cancela (estado='cancelado').
    - Lote canónico con kg sumados: se restan los kg que aportó el pedido,
      parseados de la observación '+Xkg B2B ... (pedido #N)'.
    Lotes ya iniciados o terminados NO se tocan · la producción ya ocurrió.
    """
    import re as _re
    resultado = {"lotes_revertidos": []}
    marca_sumado = f"(pedido #{pedido_id})"
    marca_dedicado = f"· #{pedido_id} ·"

    # 1. Lote dedicado eos_b2b → cancelar
    for (lid,) in cur.execute(
        """SELECT id FROM produccion_programada
           WHERE origen = 'eos_b2b'
             AND observaciones LIKE ?
             AND inicio_real_at IS NULL AND fin_real_at IS NULL
             AND estado NOT IN ('cancelado','completado')""",
        (f"%{marca_dedicado}%",),
    ).fetchall():
        cur.execute(
            """UPDATE produccion_programada
               SET estado = 'cancelado',
                   observaciones = COALESCE(observaciones,'') ||
                       ' · CANCELADO (pedido B2B #' || ? || ' cancelado)'
               WHERE id = ?""",
            (pedido_id, lid),
        )
        resultado["lotes_revertidos"].append(
            {"lote_id": lid, "modo": "lote_dedicado_cancelado"})

    # 2. Lote canónico con kg B2B sumados → restar esos kg.
    # BUG-22 fix · usar UPDATE atómico SET cantidad_kg = ... - ? (no leer
    # cantidad_kg local). BUG-23 fix · si tras restar no quedan más pedidos
    # #N en observaciones, devolver origen a 'eos_canonico' para que el
    # regenerador lo gestione normalmente · sin esto, el lote queda
    # 'eos_plan' (Fijo) para siempre y regenerar genera duplicados.
    for lid, lkg, lobs in cur.execute(
        """SELECT id, COALESCE(cantidad_kg,0), COALESCE(observaciones,'')
           FROM produccion_programada
           WHERE observaciones LIKE ?
             AND inicio_real_at IS NULL AND fin_real_at IS NULL
             AND estado NOT IN ('cancelado','completado')""",
        (f"%{marca_sumado}%",),
    ).fetchall():
        m = _re.search(r'\+\s*([\d.]+)kg B2B[^(]*\(pedido #' + str(pedido_id) + r'\)', lobs)
        if not m:
            continue
        kg_quita = float(m.group(1))
        cur.execute(
            """UPDATE produccion_programada
               SET cantidad_kg = CASE
                                   WHEN COALESCE(cantidad_kg, 0) > ?
                                   THEN COALESCE(cantidad_kg, 0) - ?
                                   ELSE 0
                                 END,
                   observaciones = COALESCE(observaciones,'') ||
                       ' · −' || ? || 'kg (pedido B2B #' || ? || ' cancelado)'
               WHERE id = ?""",
            (kg_quita, kg_quita, kg_quita, pedido_id, lid),
        )
        # Releer obs post-UPDATE para saber si quedan otros pedidos B2B
        post = cur.execute(
            "SELECT COALESCE(cantidad_kg,0), COALESCE(observaciones,'') "
            "FROM produccion_programada WHERE id=?", (lid,),
        ).fetchone()
        nuevo_kg = float(post[0] or 0)
        obs_post = post[1] if post else ''
        # ¿quedan otros pedidos #N pendientes? buscar el patrón
        # `(pedido #N)` que NO haya sido cancelado.
        otros_pedidos = _re.findall(
            r'\+\s*[\d.]+kg B2B[^(]*\(pedido #(\d+)\)', obs_post or ''
        )
        cancelados = _re.findall(
            r'pedido B2B #(\d+) cancelado\)', obs_post or ''
        )
        # IDs vivos = los sumados que NO aparecen como cancelados
        vivos = set(otros_pedidos) - set(cancelados)
        if not vivos:
            # Sin pedidos B2B activos sumados → restaurar a Sugerido
            cur.execute(
                "UPDATE produccion_programada SET origen='eos_canonico' "
                "WHERE id=? AND origen='eos_plan'",
                (lid,),
            )
        resultado["lotes_revertidos"].append(
            {"lote_id": lid, "modo": "kg_restados",
             "kg_restados": kg_quita, "kg_nuevo": nuevo_kg,
             "origen_restaurado": (not vivos)})
    # Trazabilidad estructurada (mig 171) · limpiar links del pedido
    # cancelado. Si después se re-crea, el INSERT OR REPLACE lo restituye.
    lotes_a_regenerar = []
    try:
        # Antes de borrar, capturar qué lotes quedan afectados
        for (lid,) in cur.execute(
            "SELECT DISTINCT lote_produccion_id FROM pedidos_b2b_lote WHERE pedido_b2b_id = ?",
            (pedido_id,),
        ).fetchall():
            lotes_a_regenerar.append(lid)
        cur.execute("DELETE FROM pedidos_b2b_lote WHERE pedido_b2b_id = ?",
                    (pedido_id,))
    except Exception:
        pass
    # Regenerar etiqueta de los lotes que perdieron aportes
    for lid in lotes_a_regenerar:
        _regenerar_distribucion_lote(cur, lid)
    return resultado


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
    # Si se cancela vía PATCH, revertir la integración al plan igual que el DELETE.
    reversion = None
    if body.get("estado") == "cancelado" and row[3] not in ('despachado', 'cancelado'):
        reversion = _revertir_pedido_b2b_del_plan(cur, pid, user)
    audit_log(cur, usuario=user, accion="ACTUALIZAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              antes={"cliente_id": row[0], "estado": row[3]},
              despues=body)
    conn.commit()
    return jsonify({"ok": True, "id": pid, "reversion_plan": reversion})


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
    # Revertir la integración al plan · sin esto el lote queda agendado
    # para un pedido que ya no existe → sobreproducción.
    reversion = _revertir_pedido_b2b_del_plan(cur, pid, user)
    audit_log(cur, usuario=user, accion="CANCELAR_PEDIDO_B2B",
              tabla="pedidos_b2b", registro_id=pid,
              antes={"estado": row[0]},
              despues={"estado": "cancelado", "reversion_plan": reversion})
    conn.commit()
    return jsonify({"ok": True, "id": pid, "estado": "cancelado",
                    "reversion_plan": reversion})


# ─── Consolidador de necesidades ───────────────────────────────────────────

@bp.route("/api/admin/lote-size-sospechoso", methods=["GET"])
def admin_lote_size_sospechoso():
    """FIX #2-b · 23-may-2026 Sebastián · AZ HIBRID CLEAR tenía lote_size_kg=0.1
    causando 23 lotes diarios sugeridos. Lista productos con lote_size_kg < 1
    para que admin los arregle.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """SELECT producto_nombre, COALESCE(lote_size_kg,0), COALESCE(unidad_base_g,0),
                  COALESCE(activo,1), codigo_pt
           FROM formula_headers
           WHERE COALESCE(lote_size_kg,0) < 1
             AND COALESCE(activo,1) = 1
           ORDER BY producto_nombre""",
    ).fetchall()
    items = [{
        'producto_nombre': r[0],
        'lote_size_kg_actual': float(r[1] or 0),
        'unidad_base_g_actual': float(r[2] or 0),
        'codigo_pt': r[4] or '',
        'sugerido_kg': round((r[2] or 0) / 1000.0, 2) if r[2] else None,
    } for r in rows]
    return jsonify({'ok': True, 'n': len(items), 'items': items})


@bp.route("/api/admin/lote-size-fix", methods=["POST"])
def admin_lote_size_fix():
    """Actualiza formula_headers.lote_size_kg + unidad_base_g desde body.
    Body: {producto_nombre: '...', lote_size_kg: 33}
    Solo admin · audit log.
    """
    from config import ADMIN_USERS as _AU
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    if user not in _AU:
        return jsonify({'error': 'solo admin'}), 403
    d = request.get_json(silent=True) or {}
    producto = (d.get('producto_nombre') or '').strip()
    try:
        lote_kg = float(d.get('lote_size_kg') or 0)
    except Exception:
        return jsonify({'error': 'lote_size_kg debe ser número'}), 400
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if lote_kg < 0.5 or lote_kg > 1000:
        return jsonify({'error': 'lote_size_kg fuera de rango (0.5 - 1000)'}), 400
    conn = get_db()
    cur = conn.cursor()
    row_old = cur.execute(
        """SELECT lote_size_kg, unidad_base_g FROM formula_headers
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    ).fetchone()
    if not row_old:
        return jsonify({'error': f"producto '{producto}' no existe"}), 404
    nuevo_g = lote_kg * 1000.0
    cur.execute(
        """UPDATE formula_headers
           SET lote_size_kg = ?, unidad_base_g = ?
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (lote_kg, nuevo_g, producto),
    )
    try:
        audit_log(cur, usuario=user, accion='FIX_LOTE_SIZE_KG',
                  tabla='formula_headers', registro_id=producto,
                  antes={'lote_size_kg': float(row_old[0] or 0),
                          'unidad_base_g': float(row_old[1] or 0)},
                  despues={'lote_size_kg': lote_kg, 'unidad_base_g': nuevo_g})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'producto_nombre': producto,
                    'lote_size_kg_nuevo': lote_kg,
                    'unidad_base_g_nuevo': nuevo_g})


@bp.route("/api/plan/desglose-tonos", methods=["GET"])
def plan_desglose_tonos():
    """Sebastián 24-may PM · LIP SERUM VOLUMINIZADOR tiene 5 tonos
    (PEACH, MERLOT, MOCCA, MALVA, N). Misma fórmula base · al producir
    12kg de bulk se divide entre los tonos según mix de ventas reciente.

    Query params:
      producto: nombre del producto (requerido)
      cantidad_kg: kg totales del lote (default 0 · solo retorna %)
      ventana_dias: ventana para calcular mix (default 60)

    Returns:
      {ok, producto, n_tonos, total_uds_ventana, items: [
        {sku, ml_unidad, uds_ventana, porcentaje, kg_sugerido}, ...
      ]}
    """
    err = _require_login()
    if err:
        return err
    import json as _json
    from datetime import datetime as _dt2, timedelta as _td2
    producto = (request.args.get('producto') or '').strip()
    try:
        cantidad_kg = float(request.args.get('cantidad_kg') or 0)
    except Exception:
        cantidad_kg = 0
    try:
        ventana = max(7, min(int(request.args.get('ventana_dias') or 60), 365))
    except Exception:
        ventana = 60
    if not producto:
        return jsonify({'error': 'producto requerido'}), 400
    conn = get_db()
    cur = conn.cursor()
    # SKUs mapeados al producto
    skus_rows = cur.execute(
        """SELECT sku FROM sku_producto_map
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
             AND COALESCE(activo,1) = 1""",
        (producto,),
    ).fetchall()
    skus = [r[0].upper().strip() for r in skus_rows]
    if not skus:
        return jsonify({'ok': True, 'producto': producto, 'n_tonos': 0,
                        'items': [], 'mensaje': 'sin SKUs mapeados'})
    # ml por SKU (volumen_ml en producto_presentaciones)
    ml_por_sku = {}
    try:
        qs = ','.join(['?'] * len(skus))
        for r in cur.execute(
            f"""SELECT UPPER(TRIM(sku_shopify)), volumen_ml
                 FROM producto_presentaciones
                WHERE UPPER(TRIM(sku_shopify)) IN ({qs})
                  AND COALESCE(activo,1) = 1""",
            tuple(skus),
        ).fetchall():
            if r[1]:
                ml_por_sku[r[0]] = float(r[1])
    except Exception:
        pass
    # Ventas por SKU en ventana
    desde = (_dt2.utcnow() - _td2(days=ventana)).strftime('%Y-%m-%dT00:00:00')
    ventas = {sk: 0 for sk in skus}
    try:
        for r in cur.execute(
            """SELECT sku_items FROM animus_shopify_orders
                WHERE creado_en >= ?
                  AND sku_items IS NOT NULL AND sku_items != ''
                  AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                  AND LOWER(COALESCE(estado_pago,'')) NOT IN ('refunded','voided','partially_refunded')""",
            (desde,),
        ).fetchall():
            try:
                items = _json.loads(r[0]) if r[0] else []
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for it in items:
                sk = (it.get('sku') or '').upper().strip()
                if sk not in ventas:
                    continue
                qty = float(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
                ventas[sk] += qty
    except Exception as e:
        return jsonify({'error': f'query ventas: {e}'}), 500
    total_uds = sum(ventas.values())
    items = []
    if total_uds <= 0:
        # Sin ventas en ventana · distribuir equitativamente
        for sk in skus:
            items.append({
                'sku': sk,
                'ml_unidad': ml_por_sku.get(sk),
                'uds_ventana': 0,
                'porcentaje': round(100.0 / len(skus), 2),
                'kg_sugerido': round(cantidad_kg / len(skus), 2) if cantidad_kg > 0 else 0,
            })
    else:
        for sk in skus:
            uds = ventas[sk]
            pct = (uds / total_uds) * 100
            items.append({
                'sku': sk,
                'ml_unidad': ml_por_sku.get(sk),
                'uds_ventana': int(uds),
                'porcentaje': round(pct, 2),
                'kg_sugerido': round((pct / 100.0) * cantidad_kg, 2) if cantidad_kg > 0 else 0,
            })
    # Ordenar por porcentaje desc (mejor venta primero)
    items.sort(key=lambda x: -x['porcentaje'])
    return jsonify({
        'ok': True, 'producto': producto, 'n_tonos': len(skus),
        'ventana_dias': ventana, 'cantidad_kg': cantidad_kg,
        'total_uds_ventana': int(total_uds), 'items': items,
    })


@bp.route("/api/plan/diagnostico-shopify", methods=["GET"])
def diagnostico_shopify_skus():
    """Read-only · verifica la ingesta Shopify y la atribución por SKU/sub-SKU.

    Responde 3 preguntas de Sebastián (30-may-2026):
      1. ¿Está llegando de verdad Shopify? → salud de ingesta (conteos, frescura).
      2. ¿Se ve lo que se vende por cada SKU y sub-SKU? → ventas 30/60/90d por SKU.
      3. ¿Se pierde demanda? → reconciliación: uds mapeadas vs huérfanas vs SKU vacío.

    NO muta nada. Una sola pasada sobre animus_shopify_orders (90d), filtrando
    cancelled/refunded igual que el cálculo real de necesidades (_calcular_animus_dtc).
    """
    err = _require_login()
    if err:
        return err
    import json as _json
    from datetime import timedelta as _td
    try:
        from tz_colombia import hoy_colombia as _hoy_col
    except ImportError:
        from api.tz_colombia import hoy_colombia as _hoy_col
    conn = get_db()
    cur = conn.cursor()
    hoy = _hoy_col()

    # ── 1. Salud de ingesta ────────────────────────────────────────────────
    meta = cur.execute(
        "SELECT COUNT(*), MIN(creado_en), MAX(creado_en), MAX(synced_at) "
        "FROM animus_shopify_orders"
    ).fetchone()

    def _cnt(dias):
        desde = (hoy - _td(days=dias)).isoformat() + 'T00:00:00'
        return cur.execute(
            "SELECT COUNT(*) FROM animus_shopify_orders WHERE creado_en >= ?",
            (desde,)).fetchone()[0]

    sync = {
        'ordenes_total': meta[0] or 0,
        'fecha_min': meta[1], 'fecha_max': meta[2],
        'ultimo_synced_at': meta[3],
        'ordenes_30d': _cnt(30), 'ordenes_60d': _cnt(60), 'ordenes_90d': _cnt(90),
    }
    try:
        from shopify_client import _get_shopify_config
        tok, shop = _get_shopify_config(conn)
        sync['shopify_configurado'] = bool(tok and shop)
        sync['shopify_shop'] = shop or None
    except Exception:
        sync['shopify_configurado'] = None

    # ── 2. Mapa SKU→producto (+es_regalo +tono) y ml por SKU ────────────────
    # Degrada por columnas que pueden faltar en instancias viejas (mig 170/177).
    rows_map = []
    for _sel in (
        "SELECT UPPER(TRIM(sku)), producto_nombre, COALESCE(es_regalo,0), COALESCE(tono_label,'')",
        "SELECT UPPER(TRIM(sku)), producto_nombre, COALESCE(es_regalo,0), ''",
        "SELECT UPPER(TRIM(sku)), producto_nombre, 0, ''",
    ):
        try:
            rows_map = cur.execute(
                _sel + " FROM sku_producto_map WHERE COALESCE(activo,1)=1 "
                "AND producto_nombre IS NOT NULL AND TRIM(producto_nombre)!=''"
            ).fetchall()
            break
        except Exception:
            continue
    sku_to_prod, skus_regalo, tono_por_sku = {}, set(), {}
    for r in rows_map:
        sku_to_prod[r[0]] = r[1]
        if r[2]:
            skus_regalo.add(r[0])
        if r[3]:
            tono_por_sku[r[0]] = r[3]
    ml_por_sku = {}
    try:
        for r in cur.execute(
            "SELECT UPPER(TRIM(sku_shopify)), volumen_ml FROM producto_presentaciones "
            "WHERE COALESCE(activo,1)=1 AND sku_shopify IS NOT NULL "
            "AND TRIM(sku_shopify)!='' AND COALESCE(volumen_ml,0)>0"
        ).fetchall():
            ml_por_sku[r[0]] = float(r[1])
    except Exception:
        pass

    # ── 3. Una pasada sobre órdenes 90d (filtrando cancel/refund) ───────────
    cut90 = (hoy - _td(days=90)).isoformat() + 'T00:00:00'
    cut60 = (hoy - _td(days=60)).isoformat() + 'T00:00:00'
    cut30 = (hoy - _td(days=30)).isoformat() + 'T00:00:00'
    rows = cur.execute(
        "SELECT sku_items, creado_en, nombre FROM animus_shopify_orders "
        "WHERE creado_en >= ? AND sku_items IS NOT NULL AND sku_items!='' "
        "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided') "
        "AND LOWER(COALESCE(estado_pago,'')) NOT IN ('refunded','voided','partially_refunded')",
        (cut90,)).fetchall()

    por_sku = {}           # sku -> {30,60,90}
    uds_vacio = {'30': 0, '60': 0, '90': 0}
    uds_total = {'30': 0, '60': 0, '90': 0}
    ordenes_vacio = []     # muestra de órdenes con line item sin SKU
    for r in rows:
        try:
            items = _json.loads(r[0]) if r[0] else []
        except Exception:
            continue
        if not isinstance(items, list):
            continue
        creado = r[1] or ''
        e60 = creado >= cut60
        e30 = creado >= cut30   # e90 garantizado por el WHERE
        tiene_vacio = False
        for it in items:
            sku = str(it.get('sku', '') or '').strip().upper()
            qty = int(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
            if qty <= 0:
                continue
            uds_total['90'] += qty
            if e60:
                uds_total['60'] += qty
            if e30:
                uds_total['30'] += qty
            if not sku:
                tiene_vacio = True
                uds_vacio['90'] += qty
                if e60:
                    uds_vacio['60'] += qty
                if e30:
                    uds_vacio['30'] += qty
                continue
            d = por_sku.setdefault(sku, {'30': 0, '60': 0, '90': 0})
            d['90'] += qty
            if e60:
                d['60'] += qty
            if e30:
                d['30'] += qty
        if tiene_vacio and len(ordenes_vacio) < 20:
            ordenes_vacio.append(r[2] or '(sin nombre)')

    # ── 4. Clasificar cada SKU + reconciliación ─────────────────────────────
    detalle = []
    uds_map = {'30': 0, '60': 0, '90': 0}
    uds_huerf = {'30': 0, '60': 0, '90': 0}
    uds_regalo = {'30': 0, '60': 0, '90': 0}
    n_map = n_huerf = n_regalo = 0
    for sku, d in por_sku.items():
        if sku in skus_regalo:
            estado, prod = 'REGALO', sku_to_prod.get(sku)
            n_regalo += 1
            for k in ('30', '60', '90'):
                uds_regalo[k] += d[k]
        elif sku in sku_to_prod:
            estado, prod = 'MAPEADO', sku_to_prod[sku]
            n_map += 1
            for k in ('30', '60', '90'):
                uds_map[k] += d[k]
        else:
            estado, prod = 'HUERFANO', None
            n_huerf += 1
            for k in ('30', '60', '90'):
                uds_huerf[k] += d[k]
        detalle.append({
            'sku': sku, 'producto': prod, 'estado': estado,
            'es_regalo': sku in skus_regalo,
            'tono': tono_por_sku.get(sku) or None,
            'ml': ml_por_sku.get(sku),
            'ml_faltante': (estado == 'MAPEADO' and sku not in ml_por_sku),
            'uds_30d': d['30'], 'uds_60d': d['60'], 'uds_90d': d['90'],
        })
    detalle.sort(key=lambda x: -x['uds_90d'])

    tot90 = uds_total['90'] or 1
    reconciliacion = {
        'uds_total_90d': uds_total['90'],
        'uds_mapeadas_90d': uds_map['90'],
        'uds_huerfanas_90d': uds_huerf['90'],
        'uds_regalo_90d': uds_regalo['90'],
        'uds_sku_vacio_90d': uds_vacio['90'],
        # % de la demanda que SÍ entra al plan (mapeada, no-regalo):
        'pct_cobertura_real': round(100.0 * uds_map['90'] / tot90, 1),
        'pct_perdido_huerfano': round(100.0 * uds_huerf['90'] / tot90, 1),
        'pct_perdido_sku_vacio': round(100.0 * uds_vacio['90'] / tot90, 1),
        'n_skus_distintos': len(por_sku),
        'n_skus_mapeados': n_map,
        'n_skus_huerfanos': n_huerf,
        'n_skus_regalo': n_regalo,
    }
    return jsonify({
        'ok': True,
        'sync': sync,
        'reconciliacion': reconciliacion,
        'por_sku': detalle,
        'sku_vacio': {
            'uds_30d': uds_vacio['30'], 'uds_60d': uds_vacio['60'],
            'uds_90d': uds_vacio['90'], 'ordenes_muestra': ordenes_vacio,
        },
        'nota': ('uds_mapeadas = demanda que SÍ entra al plan · huerfanas = SKU '
                 'vendido pero sin fila en sku_producto_map · sku_vacio = line '
                 'items sin SKU en Shopify (se pierden) · regalo = es_regalo=1 '
                 '(excluido a propósito). Filtra cancelled/refunded. DTC-only.'),
    })


@bp.route("/api/admin/formula-desactivar", methods=["POST"])
def admin_formula_desactivar():
    """Sebastián 24-may · 'EMULSION ANTIOX, SUERO C+B3, SUERO AZ+B3 ya
    no vendemos' · marca activo=0 en formula_headers para sacar de
    Necesidades + Calendar (sin borrar para preservar histórico).
    Body: {producto_nombre} · admin only · audit_log.
    """
    from config import ADMIN_USERS as _AU
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    if user not in _AU:
        return jsonify({'error': 'solo admin'}), 403
    d = request.get_json(silent=True) or {}
    producto = (d.get('producto_nombre') or '').strip()
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT producto_nombre, COALESCE(activo,1) FROM formula_headers
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    ).fetchone()
    if not row:
        return jsonify({'error': f"producto '{producto}' no existe"}), 404
    if int(row[1] or 0) == 0:
        return jsonify({'ok': True, 'producto_nombre': row[0],
                        'ya_inactivo': True})
    cur.execute(
        """UPDATE formula_headers SET activo = 0
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    )
    try:
        audit_log(cur, usuario=user, accion='FORMULA_DESACTIVAR',
                  tabla='formula_headers', registro_id=row[0])
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'producto_nombre': row[0], 'desactivado': True})


@bp.route("/api/admin/formula-activar", methods=["POST"])
def admin_formula_activar():
    """Reactivar producto · activo=1 · admin only · audit."""
    from config import ADMIN_USERS as _AU
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    if user not in _AU:
        return jsonify({'error': 'solo admin'}), 403
    d = request.get_json(silent=True) or {}
    producto = (d.get('producto_nombre') or '').strip()
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """UPDATE formula_headers SET activo = 1
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    )
    try:
        audit_log(cur, usuario=user, accion='FORMULA_ACTIVAR',
                  tabla='formula_headers', registro_id=producto)
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'producto_nombre': producto})


@bp.route("/api/admin/skus-huerfanos-top", methods=["GET"])
def admin_skus_huerfanos_top():
    """Sebastián 23-may-2026 PM · 'Suero Exfoliante BHA dice 300/mes
    no es verdad' · diag reveló LBHA + CRB3BHA huérfanos vendiendo
    casi 2000 uds/60d sin map. Endpoint que lista top huérfanos para
    mapeo masivo desde UI Herramientas.

    Devuelve top N huérfanos vendedores en 60d (no en sku_producto_map)
    + lista de productos activos en formula_headers para dropdown UI.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    import json as _json
    from datetime import datetime as _dt2, timedelta as _td2
    try:
        limit = max(1, min(int(request.args.get('limit', 30)), 100))
    except Exception:
        limit = 30
    conn = get_db()
    cur = conn.cursor()
    # SKUs ya mapeados
    mapeados = set()
    try:
        for r in cur.execute(
            "SELECT UPPER(TRIM(sku)) FROM sku_producto_map "
            "WHERE COALESCE(activo,1)=1"
        ).fetchall():
            mapeados.add(r[0])
    except Exception:
        pass
    # Ventas 60d agregadas por SKU (con filtro cancelled/refunded)
    desde = (_dt2.utcnow() - _td2(days=60)).strftime('%Y-%m-%dT00:00:00')
    ventas = {}
    try:
        for r in cur.execute(
            """SELECT sku_items FROM animus_shopify_orders
               WHERE creado_en >= ? AND sku_items IS NOT NULL
                 AND sku_items != ''
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                 AND LOWER(COALESCE(estado_pago,'')) NOT IN ('refunded','voided','partially_refunded')""",
            (desde,),
        ).fetchall():
            try:
                items = _json.loads(r[0]) if r[0] else []
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for it in items:
                sk = (it.get('sku') or '').upper().strip()
                if not sk:
                    continue
                qty = float(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
                ventas[sk] = ventas.get(sk, 0) + qty
    except Exception as e:
        return jsonify({'error': f'query ventas: {e}'}), 500
    # Filtrar huérfanos y ordenar
    huerfanos = {k: v for k, v in ventas.items() if k not in mapeados}
    top = sorted(huerfanos.items(), key=lambda x: -x[1])[:limit]
    # Lista de productos disponibles (formula_headers activos)
    productos = []
    try:
        for r in cur.execute(
            "SELECT producto_nombre FROM formula_headers "
            "WHERE COALESCE(activo,1)=1 ORDER BY producto_nombre"
        ).fetchall():
            productos.append(r[0])
    except Exception:
        pass
    return jsonify({
        'ok': True,
        'huerfanos_top': [{'sku': k, 'uds_60d': v} for k, v in top],
        'productos_disponibles': productos,
        'n_huerfanos_total': len(huerfanos),
        'uds_huerfanas_total_60d': round(sum(huerfanos.values())),
    })


@bp.route("/api/admin/sku-producto-map/bulk", methods=["POST"])
def admin_sku_producto_map_bulk():
    """UPSERT múltiples SKU→producto en una llamada.
    Body: {items: [{sku, producto_nombre}, ...]}
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    d = request.get_json(silent=True) or {}
    items = d.get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'items lista requerida'}), 400
    conn = get_db()
    cur = conn.cursor()
    creados = []
    errores = []
    for it in items[:200]:
        sku = (it.get('sku') or '').strip().upper()
        prod = (it.get('producto_nombre') or '').strip()
        # FEATURE 24-may-2026 · es_regalo opcional (default 0). Si el client
        # NO envía el campo, preservamos el valor actual via COALESCE en UPDATE.
        es_regalo_raw = it.get('es_regalo', None)
        es_regalo = None if es_regalo_raw is None else (1 if es_regalo_raw else 0)
        if not sku or not prod:
            errores.append({'sku': sku, 'error': 'sku y producto requeridos'})
            continue
        # Validar producto existe
        ex = cur.execute(
            "SELECT 1 FROM formula_headers WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))",
            (prod,),
        ).fetchone()
        if not ex:
            errores.append({'sku': sku, 'error': f"producto '{prod}' no existe"})
            continue
        try:
            existing = cur.execute(
                "SELECT 1 FROM sku_producto_map WHERE UPPER(TRIM(sku)) = UPPER(TRIM(?))",
                (sku,),
            ).fetchone()
            if existing:
                # COALESCE preserva es_regalo si el client no lo envió
                cur.execute(
                    """UPDATE sku_producto_map
                        SET producto_nombre=?, activo=1,
                            es_regalo = COALESCE(?, es_regalo)
                      WHERE UPPER(TRIM(sku)) = UPPER(TRIM(?))""",
                    (prod, es_regalo, sku),
                )
            else:
                cur.execute(
                    "INSERT INTO sku_producto_map (sku, producto_nombre, activo, es_regalo) "
                    "VALUES (?, ?, 1, ?)",
                    (sku, prod, es_regalo or 0),
                )
            creados.append({'sku': sku, 'producto': prod, 'es_regalo': es_regalo})
        except Exception as e:
            errores.append({'sku': sku, 'error': str(e)[:100]})
    try:
        audit_log(cur, usuario=user, accion='SKU_MAP_BULK',
                  tabla='sku_producto_map', registro_id='',
                  despues={'n_mapeados': len(creados),
                            'n_errores': len(errores)})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'n_mapeados': len(creados),
                    'n_errores': len(errores),
                    'creados': creados, 'errores': errores})


@bp.route("/api/admin/ml-fix-todos-skus", methods=["POST"])
def admin_ml_fix_todos_skus():
    """Sebastián 24-may PM · 'Blush es de 6 gramos' · aplica volumen_ml
    (o peso_g, en este caso 6g = 6ml equivalente) a TODOS los SKUs
    activos del producto en una llamada. Útil cuando todas las variantes
    tienen el mismo formato (5 colores Blush Balm de 6g cada uno).

    Body: {producto_nombre, volumen_ml}
    Solo admin · audit_log.
    """
    from config import ADMIN_USERS as _AU
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    if user not in _AU:
        return jsonify({'error': 'solo admin'}), 403
    d = request.get_json(silent=True) or {}
    producto = (d.get('producto_nombre') or '').strip()
    try:
        ml = float(d.get('volumen_ml') or 0)
    except Exception:
        return jsonify({'error': 'volumen_ml debe ser número'}), 400
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if ml <= 0 or ml > 5000:
        return jsonify({'error': 'volumen_ml fuera de rango (1-5000)'}), 400
    conn = get_db()
    cur = conn.cursor()
    # Verificar producto existe
    row = cur.execute(
        """SELECT producto_nombre FROM formula_headers
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    ).fetchone()
    if not row:
        return jsonify({'error': f"producto '{producto}' no existe"}), 404
    prod_canonico = row[0]
    # Listar SKUs del producto
    skus_rows = cur.execute(
        """SELECT sku FROM sku_producto_map
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
             AND COALESCE(activo,1) = 1
           ORDER BY sku""",
        (prod_canonico,),
    ).fetchall()
    if not skus_rows:
        return jsonify({'error': f"sin SKUs activos para '{prod_canonico}'"}), 400
    # UPSERT producto_presentaciones por cada SKU
    aplicados = []
    for r in skus_rows:
        sku = r[0].upper().strip()
        existing = cur.execute(
            """SELECT id FROM producto_presentaciones
               WHERE UPPER(TRIM(sku_shopify)) = UPPER(TRIM(?))""",
            (sku,),
        ).fetchone()
        if existing:
            cur.execute(
                """UPDATE producto_presentaciones
                    SET volumen_ml = ?, activo = 1
                  WHERE id = ?""",
                (ml, existing[0]),
            )
            aplicados.append({'sku': sku, 'accion': 'UPDATE'})
        else:
            cur.execute(
                """INSERT INTO producto_presentaciones
                    (producto_nombre, categoria, presentacion_codigo, etiqueta,
                     volumen_ml, sku_shopify, es_default, activo)
                    VALUES (?, '', ?, ?, ?, ?, 0, 1)""",
                (prod_canonico, sku, f'{int(ml)}ml', ml, sku),
            )
            aplicados.append({'sku': sku, 'accion': 'INSERT'})
    try:
        audit_log(cur, usuario=user, accion='FIX_VOLUMEN_ML_BULK',
                  tabla='producto_presentaciones', registro_id=prod_canonico,
                  despues={'producto_nombre': prod_canonico,
                            'volumen_ml': ml,
                            'n_skus_aplicados': len(aplicados),
                            'aplicados': aplicados})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'producto_nombre': prod_canonico,
                    'volumen_ml': ml, 'n_skus': len(aplicados),
                    'aplicados': aplicados})


@bp.route("/api/admin/ml-fix", methods=["POST"])
def admin_ml_fix():
    """Sebastián 23-may-2026 PM · "triactive no tiene tamaño envase y
    no me deja modificarlo" · UPSERT producto_presentaciones para que
    el cálculo no caiga a heurística (ml_inferido=true).

    Body: {producto_nombre: '...', volumen_ml: 30, sku: 'optional'}
    - Si sku se pasa, UPSERT con ese sku_shopify.
    - Si no, toma el PRIMER sku activo del producto en sku_producto_map
      y lo asocia a la presentación con ese ml.
    - Solo admin.
    """
    from config import ADMIN_USERS as _AU
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    if user not in _AU:
        return jsonify({'error': 'solo admin'}), 403
    d = request.get_json(silent=True) or {}
    producto = (d.get('producto_nombre') or '').strip()
    try:
        ml = float(d.get('volumen_ml') or 0)
    except Exception:
        return jsonify({'error': 'volumen_ml debe ser número'}), 400
    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if ml <= 0 or ml > 5000:
        return jsonify({'error': 'volumen_ml fuera de rango (1-5000)'}), 400
    sku_in = (d.get('sku') or '').strip().upper()
    conn = get_db()
    cur = conn.cursor()
    # Buscar producto en formula_headers
    row = cur.execute(
        """SELECT producto_nombre FROM formula_headers
           WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
        (producto,),
    ).fetchone()
    if not row:
        return jsonify({'error': f"producto '{producto}' no existe en formula_headers"}), 404
    prod_canonico = row[0]
    # Si no dieron SKU, buscar el primero del producto
    if not sku_in:
        row_sku = cur.execute(
            """SELECT sku FROM sku_producto_map
               WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
                 AND COALESCE(activo,1) = 1
               ORDER BY sku LIMIT 1""",
            (prod_canonico,),
        ).fetchone()
        if not row_sku:
            return jsonify({'error': f"producto '{prod_canonico}' sin SKUs en sku_producto_map · pasá sku explícito en body"}), 400
        sku_in = row_sku[0].upper()
    # UPSERT producto_presentaciones · una fila por sku_shopify
    existing = cur.execute(
        """SELECT id FROM producto_presentaciones
           WHERE UPPER(TRIM(sku_shopify)) = UPPER(TRIM(?))""",
        (sku_in,),
    ).fetchone()
    if existing:
        cur.execute(
            """UPDATE producto_presentaciones
                SET volumen_ml = ?, activo = 1
              WHERE id = ?""",
            (ml, existing[0]),
        )
        accion = 'UPDATE'
    else:
        cur.execute(
            """INSERT INTO producto_presentaciones
                (producto_nombre, categoria, presentacion_codigo, etiqueta,
                 volumen_ml, sku_shopify, es_default, activo)
                VALUES (?, '', ?, ?, ?, ?, 1, 1)""",
            (prod_canonico, sku_in, f'{int(ml)}ml', ml, sku_in),
        )
        accion = 'INSERT'
    try:
        audit_log(cur, usuario=user, accion='FIX_VOLUMEN_ML',
                  tabla='producto_presentaciones', registro_id=sku_in,
                  despues={'producto_nombre': prod_canonico,
                            'sku_shopify': sku_in, 'volumen_ml': ml,
                            'accion': accion})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'producto_nombre': prod_canonico,
                    'sku_shopify': sku_in, 'volumen_ml_nuevo': ml,
                    'accion': accion})


@bp.route("/api/clientes-b2b", methods=["GET"])
def clientes_b2b_listar():
    """Lista clientes_b2b_maestro · Sebastián 23-may-2026 FIX #4.
    Query params:
      activo=1 (default) · solo activos
      incluir_pedidos=1 · adjunta count de pedidos por cliente
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    solo_activos = request.args.get('activo', '1') == '1'
    incluir_pedidos = request.args.get('incluir_pedidos') == '1'
    conn = get_db()
    cur = conn.cursor()
    where = "WHERE activo=1" if solo_activos else ""
    rows = cur.execute(
        f"""SELECT cliente_id, cliente_nombre, contacto, telefono, email,
                    activo, tipo, COALESCE(notas,''), creado_at_utc
            FROM clientes_b2b_maestro {where}
            ORDER BY cliente_nombre""",
    ).fetchall()
    items = []
    for r in rows:
        item = {
            'cliente_id': r[0], 'cliente_nombre': r[1], 'contacto': r[2],
            'telefono': r[3], 'email': r[4], 'activo': int(r[5] or 0),
            'tipo': r[6], 'notas': r[7], 'creado_at_utc': r[8],
        }
        if incluir_pedidos:
            row_pc = cur.execute(
                """SELECT COUNT(*),
                          SUM(CASE WHEN estado IN ('pendiente','confirmado','en_produccion') THEN 1 ELSE 0 END),
                          MAX(COALESCE(fecha_estimada, creado_at_utc))
                   FROM pedidos_b2b WHERE cliente_id = ?""",
                (r[0],),
            ).fetchone()
            item['pedidos_total'] = int((row_pc and row_pc[0]) or 0)
            item['pedidos_pendientes'] = int((row_pc and row_pc[1]) or 0)
            item['ultimo_pedido_fecha'] = (row_pc[2] if row_pc else '') or ''
        items.append(item)
    return jsonify({'ok': True, 'clientes': items})


@bp.route("/api/clientes-b2b", methods=["POST"])
def clientes_b2b_crear():
    """Crea cliente en clientes_b2b_maestro · upsert por cliente_id.

    Sebastián 25-may-2026 PM · si body.generar_credencial_portal=true,
    crea TAMBIÉN credencial en portal_clientes_credenciales con password
    random · devuelve email + password en plain (solo se muestra una vez)
    + mensaje pre-armado para mandar al cliente.

    Requiere email válido para generar credencial portal · si no viene,
    devuelve 400 con hint.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    d = request.get_json(silent=True) or {}
    cliente_id = (d.get('cliente_id') or '').strip()
    cliente_nombre = (d.get('cliente_nombre') or '').strip()
    if not cliente_id or not cliente_nombre:
        return jsonify({'error': 'cliente_id y cliente_nombre requeridos'}), 400
    tipo = (d.get('tipo') or 'B2B').upper()
    if tipo not in ('B2B', 'MAQUILA', 'INFLUENCER', 'OTRO'):
        tipo = 'B2B'
    email = (d.get('email') or '').strip()
    generar_portal = bool(d.get('generar_credencial_portal'))
    if generar_portal and (not email or '@' not in email):
        return jsonify({'error': 'Email válido requerido para generar credencial portal',
                         'codigo': 'PORTAL_EMAIL_REQUERIDO'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO clientes_b2b_maestro
            (cliente_id, cliente_nombre, contacto, telefono, email, tipo, notas, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(cliente_id) DO UPDATE SET
              cliente_nombre = excluded.cliente_nombre,
              contacto = excluded.contacto,
              telefono = excluded.telefono,
              email = excluded.email,
              tipo = excluded.tipo,
              notas = excluded.notas,
              activo = 1,
              actualizado_at_utc = datetime('now','utc')""",
        (cliente_id, cliente_nombre,
         (d.get('contacto') or '').strip(),
         (d.get('telefono') or '').strip(),
         email,
         tipo,
         (d.get('notas') or '').strip()),
    )
    try:
        audit_log(cur, usuario=user, accion='UPSERT_CLIENTE_B2B',
                  tabla='clientes_b2b_maestro', registro_id=cliente_id,
                  despues=d)
    except Exception:
        pass

    portal_info = None
    if generar_portal:
        import secrets as _secrets
        from werkzeug.security import generate_password_hash as _gph
        # Password random 12 chars · sin caracteres ambiguos
        pw_plain = _secrets.token_urlsafe(9)[:12].replace('-', 'A').replace('_', 'B')
        pw_hash = _gph(pw_plain)
        email_lower = email.lower()
        # Si ya existe credencial con ese email, hacer reset; sino insertar nueva
        try:
            existe = cur.execute(
                "SELECT id FROM portal_clientes_credenciales WHERE LOWER(email) = ?",
                (email_lower,)).fetchone()
            if existe:
                cur.execute(
                    """UPDATE portal_clientes_credenciales
                          SET password_hash = ?, activo = 1,
                              cliente_id = ?, cliente_nombre = ?
                        WHERE id = ?""",
                    (pw_hash, cliente_id, cliente_nombre, existe[0]))
                accion_audit = 'PORTAL_RESET_CRED_VIA_CLIENTE_NUEVO'
                cred_id_audit = existe[0]
            else:
                cur.execute(
                    """INSERT INTO portal_clientes_credenciales
                         (cliente_id, cliente_nombre, email, password_hash,
                          activo, creado_por)
                       VALUES (?, ?, ?, ?, 1, ?)""",
                    (cliente_id, cliente_nombre, email_lower, pw_hash, user))
                cred_id_audit = cur.lastrowid
                accion_audit = 'PORTAL_CREAR_CRED_VIA_CLIENTE_NUEVO'
            try:
                audit_log(cur, usuario=user, accion=accion_audit,
                          tabla='portal_clientes_credenciales',
                          registro_id=cred_id_audit,
                          despues={'cliente_id': cliente_id, 'email': email_lower})
            except Exception:
                pass
            # Mensaje pre-armado para WhatsApp / Email
            portal_url = 'https://app.eossuite.com/portal/login'
            primer_nombre = cliente_nombre.split()[0] if cliente_nombre else ''
            mensaje = (
                f"Hola {primer_nombre}! 👋\n\n"
                f"Te creé tu acceso al portal B2B de Espagiria. Desde acá "
                f"podés solicitar productos directamente y hacer "
                f"peticiones/quejas/reclamos cuando lo necesites.\n\n"
                f"🔗 {portal_url}\n\n"
                f"Email: {email_lower}\n"
                f"Contraseña: {pw_plain}\n\n"
                f"Te recomiendo cambiarla al primer ingreso.\n"
                f"Cualquier duda me avisás.\n\n"
                f"— Sebastián"
            )
            portal_info = {
                'email': email_lower,
                'password': pw_plain,
                'portal_url': portal_url,
                'mensaje': mensaje,
            }
        except Exception as _e:
            log.warning('crear cred portal fallo al crear cliente %s: %s',
                          cliente_id, _e)
            portal_info = {'error': f'No pude crear credencial portal: {_e}'}
    conn.commit()
    return jsonify({'ok': True, 'cliente_id': cliente_id,
                     'portal_credencial': portal_info}), 201


@bp.route("/api/clientes-b2b/<cliente_id>", methods=["DELETE"])
def clientes_b2b_desactivar(cliente_id):
    """Soft-delete · marca activo=0 · NUNCA borra para preservar pedidos."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """UPDATE clientes_b2b_maestro SET activo=0,
            actualizado_at_utc = datetime('now','utc')
           WHERE cliente_id = ?""",
        (cliente_id,),
    )
    try:
        audit_log(cur, usuario=user, accion='DESACTIVAR_CLIENTE_B2B',
                  tabla='clientes_b2b_maestro', registro_id=cliente_id)
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True})


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

    # EN VIVO · Sebastián 1-jun-2026: "que lea Shopify en vivo, no el snapshot".
    # Antes de calcular, refresca el stock de Shopify si el snapshot está viejo
    # (>10 min). Best-effort + lock-guarded: solo UNA carga sincroniza (las demás
    # usan el snapshot sin esperar) y NUNCA rompe Necesidades si Shopify falla.
    # ?live=0 lo salta (cargas rápidas / debugging).
    if request.args.get('live', '1') != '0':
        try:
            from blueprints.programacion import _auto_refresh_shopify_stock
            _auto_refresh_shopify_stock(conn)
        except Exception:
            pass

    # ─── Cliente 1: Animus DTC (Shopify auto) ─────────────────────────────
    # Re-usamos la lógica existente del endpoint animus-prioridad-agotamiento
    # pero ajustando umbrales a la lógica de Sebastián (20-25-45d).
    productos_animus = _calcular_animus_dtc(c, ventana, cob_critico, cob_alerta, cob_vigilar)

    # ─── Cliente 2+: B2B (Fernando + futuros) ─────────────────────────────
    # Sebastián 25-may-2026 PM · incluir `urgencia` (mig 182) y ordenar
    # alta primero · planta debe ver de un vistazo qué cliente apura.
    # Fallback si mig 182 no aplicada · query alternativo sin urgencia.
    try:
        pedidos_b2b = c.execute(
            """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                      cantidad_uds, ml_unidad, fecha_estimada, estado, notas,
                      COALESCE(urgencia,'media')
               FROM pedidos_b2b
               WHERE estado NOT IN ('despachado','cancelado')
               ORDER BY
                  CASE LOWER(COALESCE(urgencia,'media'))
                       WHEN 'alta' THEN 0
                       WHEN 'media' THEN 1
                       WHEN 'baja' THEN 2 ELSE 1 END,
                  cliente_nombre ASC, fecha_estimada ASC""",
        ).fetchall()
        _has_urg = True
    except Exception:
        pedidos_b2b = c.execute(
            """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                      cantidad_uds, ml_unidad, fecha_estimada, estado, notas
               FROM pedidos_b2b
               WHERE estado NOT IN ('despachado','cancelado')
               ORDER BY cliente_nombre ASC, fecha_estimada ASC""",
        ).fetchall()
        _has_urg = False

    # Agrupar por cliente · ya vienen ordenados alta primero del SQL
    _URG_RANK = {'alta': 0, 'media': 1, 'baja': 2}
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
                "max_urgencia": 'baja',
                "max_urgencia_rank": 2,
            }
        kg = round((r[4] * r[5]) / 1000.0, 2)
        urg = (r[9] if _has_urg and len(r) > 9 else 'media') or 'media'
        urg = str(urg).lower()
        if urg not in _URG_RANK:
            urg = 'media'
        b2b_por_cliente[cid]["pedidos"].append({
            "id": r[0],
            "producto_nombre": r[3],
            "cantidad_uds": r[4],
            "ml_unidad": r[5],
            "kg_equivalente": kg,
            "fecha_estimada": r[6],
            "estado": r[7],
            "notas": r[8] or "",
            "urgencia": urg,
        })
        b2b_por_cliente[cid]["kg_total"] += kg
        # max_urgencia del cliente = la más alta de sus pedidos
        rank = _URG_RANK[urg]
        if rank < b2b_por_cliente[cid]["max_urgencia_rank"]:
            b2b_por_cliente[cid]["max_urgencia"] = urg
            b2b_por_cliente[cid]["max_urgencia_rank"] = rank

    # Ordenar clientes B2B por max_urgencia (alta primero), luego alfabético
    b2b_lista = sorted(b2b_por_cliente.values(),
                        key=lambda x: (x["max_urgencia_rank"], x["cliente_nombre"]))

    clientes = [{
        "cliente_id": "ANIMUS_DTC",
        "cliente_nombre": "Animus Lab DTC",
        "tipo": "shopify_auto",
        "productos": productos_animus,
    }] + b2b_lista

    # SHOPIFY-FIX · 22-may-2026 · Bug #5 audit · SKUs huérfanos vendiendo
    # · Detecta SKUs vendiendo en Shopify SIN mapping a producto
    # · Sebastián los necesita ver para mapearlos en admin/maestro_pt
    # FIX 30-may-2026 · auditoría Plan · DOS arreglos:
    #  (a) PG-safe: antes usaba json_each() (SQLite-only) · en PostgreSQL caía al
    #      except y la detección de huérfanos quedaba INERTE en producción.
    #      Ahora parsea sku_items en Python (funciona en SQLite y PG).
    #  (b) Cuantifica las UDS vendidas sin mapear (no solo lista SKUs), para
    #      mostrar cuánta VELOCIDAD/venta se está perdiendo del cálculo.
    from datetime import datetime as _dt2, timedelta as _td2
    import json as _jh_orf
    cutoff = (_dt2.now() - _td2(days=30)).strftime('%Y-%m-%d')
    uds_por_sku_vend = {}
    try:
        for (items_json,) in c.execute(
            "SELECT sku_items FROM animus_shopify_orders "
            "WHERE COALESCE(creado_en,'') >= ? AND COALESCE(sku_items,'') != ''",
            (cutoff,),
        ).fetchall():
            try:
                items = _jh_orf.loads(items_json) if items_json else []
                if not isinstance(items, list):
                    continue
                for li in items:
                    sk = (li.get('sku') or '').strip().upper()
                    qty = int(li.get('qty') or li.get('quantity') or li.get('cantidad') or 0)
                    if sk and qty > 0:
                        uds_por_sku_vend[sk] = uds_por_sku_vend.get(sk, 0) + qty
            except Exception:
                continue
    except Exception:
        uds_por_sku_vend = {}
    skus_set = set(uds_por_sku_vend.keys())
    try:
        skus_mapeados = set(
            (r[0] or '').strip().upper()
            for r in c.execute(
                "SELECT DISTINCT sku FROM sku_producto_map WHERE COALESCE(activo,1)=1"
            ).fetchall() if r and r[0]
        )
    except Exception:
        skus_mapeados = set()
    _huerfanos_ids = sorted(skus_set - skus_mapeados,
                            key=lambda s: -uds_por_sku_vend.get(s, 0))
    skus_huerfanos = _huerfanos_ids[:50]
    skus_huerfanos_detalle = [
        {"sku": s, "uds_30d": uds_por_sku_vend.get(s, 0)} for s in skus_huerfanos
    ]
    uds_huerfanas_total = sum(uds_por_sku_vend.get(s, 0)
                              for s in (skus_set - skus_mapeados))

    # Resumen consolidado
    resumen = {
        "n_critico": sum(1 for p in productos_animus if p["urgencia"] == "CRITICO"),
        "n_urgente": sum(1 for p in productos_animus if p["urgencia"] == "URGENTE"),
        "n_vigilar": sum(1 for p in productos_animus if p["urgencia"] == "VIGILAR"),
        "n_ok": sum(1 for p in productos_animus if p["urgencia"] == "OK"),
        "n_sin_ventas": sum(1 for p in productos_animus if p["urgencia"] == "SIN_VENTAS"),
        "n_sin_mapeo": sum(1 for p in productos_animus if p["urgencia"] == "SIN_MAPEO"),
        "n_skus_huerfanos_vendiendo": len(skus_huerfanos),
        "skus_huerfanos_vendiendo": skus_huerfanos,  # solo top 50
        "skus_huerfanos_detalle": skus_huerfanos_detalle,  # [{sku, uds_30d}] top 50
        "uds_huerfanas_total_30d": uds_huerfanas_total,  # ⚠ ventas que NO entran al cálculo de velocidad
        "n_clientes_b2b": len(b2b_por_cliente),
        "n_pedidos_b2b_pendientes": sum(len(c["pedidos"]) for c in b2b_por_cliente.values()),
        "kg_total_b2b_pendientes": round(sum(c["kg_total"] for c in b2b_por_cliente.values()), 2),
    }

    # Sebastián 30-may-2026 · estado del sync de ventas · si pasa mucho sin
    # sincronizar, el plan queda CIEGO (caso 25-may: 5 días stale → velocidad
    # baja, "dura hasta noviembre"). El frontend pinta un banner de atraso.
    ultimo_sync_ventas = None
    horas_desde_sync = None
    try:
        _row = conn.execute(
            "SELECT MAX(synced_at) FROM animus_shopify_orders"
        ).fetchone()
        ultimo_sync_ventas = _row[0] if (_row and _row[0]) else None
        if ultimo_sync_ventas:
            from datetime import datetime as _dts
            try:
                from tz_colombia import now_colombia as _nowcol
                _ahora = _nowcol().replace(tzinfo=None)
            except Exception:
                _ahora = None
            try:
                _s = str(ultimo_sync_ventas)[:19].replace('T', ' ')
                _ts = _dts.strptime(_s, '%Y-%m-%d %H:%M:%S')
                if _ahora is not None:
                    horas_desde_sync = round((_ahora - _ts).total_seconds() / 3600.0, 1)
            except Exception:
                pass
    except Exception:
        pass

    return jsonify({
        "clientes": clientes,
        "resumen": resumen,
        "sync_ventas": {
            "ultimo": ultimo_sync_ventas,
            "horas_desde": horas_desde_sync,
        },
        "parametros": {
            "cobertura_dias_minimo": cob_critico,
            "cobertura_dias_alerta": cob_alerta,
            "cobertura_dias_vigilar": cob_vigilar,
            "ventana_ventas": ventana,
        },
    })


@bp.route("/api/plan/alertas-ia", methods=["GET"])
def plan_alertas_ia():
    """Alertas IA proactivas para el calendario · Sebastián 19-may-2026.

    Banner accionable arriba del Calendario EOS. Consolida 3 tipos:

    1. **cobertura_critica** · producto Animus DTC con urgencia CRITICO
       y SIN lote programado en horizonte próximo · "se va a agotar"
    2. **adelantar_lote** · producto con urgencia URGENTE cuyo próximo
       lote está MÁS allá del horizonte de cobertura · "adelantar"
    3. **mp_faltante_b2b** · pedido B2B activo con MP insuficiente · "compra"

    Cada alerta trae acción sugerida + payload para que el frontend
    pueda actuar (ej. abrir modal de generar lote prefilled).

    SOLO LECTURA · no modifica nada.
    """
    err = _require_login()
    if err:
        return err
    from datetime import timedelta as _td

    try:
        cob_critico = max(7, int(request.args.get("cobertura_dias_minimo", 20)))
        cob_alerta = max(cob_critico + 1, int(request.args.get("cobertura_dias_alerta", 25)))
        cob_vigilar = max(cob_alerta + 1, int(request.args.get("cobertura_dias_vigilar", 45)))
        ventana = max(30, min(180, int(request.args.get("ventana_ventas", 60))))
    except Exception:
        cob_critico, cob_alerta, cob_vigilar, ventana = 20, 25, 45, 60

    conn = get_db()
    c = conn.cursor()

    alertas = []

    # ─── 1+2 · Animus DTC: CRITICO / URGENTE / adelantar ───────────────
    productos_animus = _calcular_animus_dtc(c, ventana, cob_critico, cob_alerta, cob_vigilar)

    hoy = _hoy_colombia()
    horizonte_str = (hoy + _td(days=cob_alerta * 2)).isoformat()

    # próximo lote programado por producto (activo · futuro)
    prox_lote = {}
    for r in c.execute(
        """SELECT UPPER(TRIM(producto)) AS p,
                  MIN(substr(fecha_programada,1,10)) AS prox_fecha
           FROM produccion_programada
           WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
             AND substr(fecha_programada,1,10) >= ?
           GROUP BY UPPER(TRIM(producto))""",
        (hoy.isoformat(),),
    ).fetchall():
        prox_lote[r[0]] = r[1]

    for p in productos_animus:
        urg = p.get("urgencia") or ""
        nombre = p.get("producto_nombre") or ""
        key = nombre.upper().strip()
        prox = prox_lote.get(key)
        cob = p.get("dias_cobertura")
        cob_txt = f"{cob}d" if cob is not None else "sin datos"

        if urg == "CRITICO":
            # Si NO hay lote programado o el lote es muy lejano → alerta crítica
            if not prox or prox > horizonte_str:
                alertas.append({
                    "tipo": "cobertura_critica",
                    "severidad": "critica",
                    "titulo": f"🚨 {nombre} · stock se agota en {cob_txt}",
                    "detalle": (
                        f"Cobertura {cob_txt} (≤{cob_critico}d crítico). "
                        + (f"Próximo lote programado: {prox}" if prox else "Sin lote programado.")
                        + f" Recomendado: producir {p.get('kg_a_producir', 0):.0f}kg ya."
                    ),
                    "accion": "generar_lote",
                    "payload": {
                        "producto": nombre,
                        "kg_sugerido": p.get("kg_a_producir", 0),
                        "fecha_sugerida": hoy.isoformat(),
                    },
                })
        elif urg == "URGENTE":
            # Si el lote programado es MÁS lejos que la cobertura → adelantar
            if prox and cob is not None:
                cob_dia = (hoy + _td(days=int(cob))).isoformat()
                if prox > cob_dia:
                    alertas.append({
                        "tipo": "adelantar_lote",
                        "severidad": "advertencia",
                        "titulo": f"⏩ {nombre} · adelantar lote",
                        "detalle": (
                            f"Cobertura {cob_txt}, pero próximo lote es el {prox}. "
                            f"Recomendado adelantarlo a {cob_dia} o antes."
                        ),
                        "accion": "adelantar",
                        "payload": {
                            "producto": nombre,
                            "fecha_actual": prox,
                            "fecha_sugerida": cob_dia,
                        },
                    })
            elif not prox:
                alertas.append({
                    "tipo": "cobertura_critica",
                    "severidad": "advertencia",
                    "titulo": f"⚠️ {nombre} · urgencia URGENTE sin lote programado",
                    "detalle": (
                        f"Cobertura {cob_txt} ({cob_critico+1}-{cob_alerta}d). "
                        f"Recomendado: programar {p.get('kg_a_producir', 0):.0f}kg."
                    ),
                    "accion": "generar_lote",
                    "payload": {
                        "producto": nombre,
                        "kg_sugerido": p.get("kg_a_producir", 0),
                        "fecha_sugerida": hoy.isoformat(),
                    },
                })

    # ─── 3 · Pedidos B2B activos con MP faltante ──────────────────────
    for r in c.execute(
        """SELECT id, cliente_nombre, producto_nombre,
                  COALESCE(cantidad_uds,0), COALESCE(ml_unidad,30),
                  fecha_estimada
           FROM pedidos_b2b
           WHERE estado IN ('pendiente','confirmado','en_produccion')
           ORDER BY fecha_estimada ASC""",
    ).fetchall():
        pid, cli, prod_b2b, uds, ml, fecha = r
        kg = round((uds * ml) / 1000.0, 2)
        try:
            chk = _check_mp_para_pedido_b2b(c, prod_b2b, kg)
        except Exception:
            continue
        if not chk["ok"] and chk["mps_faltantes"]:
            n_mps = len(chk["mps_faltantes"])
            principales = ", ".join(
                m["material_nombre"] or m["material_id"]
                for m in chk["mps_faltantes"][:3]
            )
            if n_mps > 3:
                principales += f" (+{n_mps - 3} más)"
            alertas.append({
                "tipo": "mp_faltante_b2b",
                "severidad": "advertencia",
                "titulo": f"📦 Pedido B2B {cli} · faltan MPs",
                "detalle": (
                    f"{prod_b2b} ({kg}kg) para el {fecha or 'sin fecha'}. "
                    f"Faltan {n_mps} MP(s): {principales}. "
                    f"Generá solicitudes de compra desde Abastecimiento."
                ),
                "accion": "ver_abastecimiento",
                "payload": {
                    "pedido_id": pid,
                    "producto": prod_b2b,
                    "mps_faltantes": chk["mps_faltantes"][:10],
                },
            })

    # Ordenar: crítica primero, luego advertencia, luego info
    orden_sev = {"critica": 0, "advertencia": 1, "info": 2}
    alertas.sort(key=lambda a: (orden_sev.get(a["severidad"], 9), a["titulo"]))

    return jsonify({
        "alertas": alertas,
        "total": len(alertas),
        "por_severidad": {
            "critica": sum(1 for a in alertas if a["severidad"] == "critica"),
            "advertencia": sum(1 for a in alertas if a["severidad"] == "advertencia"),
            "info": sum(1 for a in alertas if a["severidad"] == "info"),
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
    # FIX 23-may-2026 · auditoría · también incluye fecha_creacion (para
    # distinguir SIN_HISTORIAL vs SIN_VENTAS_REAL) y excluye productos
    # marcados como descontinuados en sku_planeacion_config.
    productos = c.execute(
        """SELECT fh.producto_nombre,
                  COALESCE(NULLIF(TRIM(fh.codigo_pt),''),
                           UPPER(SUBSTR(REPLACE(REPLACE(fh.producto_nombre,' ',''),'.',''),1,4)))
                       AS codigo,
                  COALESCE(fh.lote_size_kg, 0),
                  COALESCE(fh.tiene_10ml,0), COALESCE(fh.uds_10ml_por_lote,0),
                  COALESCE(fh.tipo_10ml,''),
                  COALESCE(fh.imagen_url,''),
                  COALESCE(fh.fecha_creacion,'')
           FROM formula_headers fh
           LEFT JOIN sku_planeacion_config spc
                  ON UPPER(TRIM(spc.producto_nombre)) = UPPER(TRIM(fh.producto_nombre))
           WHERE COALESCE(fh.activo,1) = 1
             AND LOWER(COALESCE(spc.estado,'activo')) NOT IN
                 ('descontinuado','desactivado','inactivo')
           ORDER BY fh.producto_nombre""",
    ).fetchall()

    if not productos:
        return []

    # 2. Mapeo producto → sku_principal (para Shopify)
    # Estructura sku_producto_map: sku → producto_nombre
    # FIX 24-may PM · cargamos también es_regalo (mig 170) para excluir
    # del cálculo de velocidad SKUs que son regalo (BBM mini, promos).
    sku_to_prod = {}
    prod_to_skus = {}  # inverso · diagnóstico: ¿qué SKUs mapean a cada producto?
    skus_regalo = set()
    tono_por_sku = {}  # Sebastián 25-may-2026 PM · desglose por tono multi-SKU
    try:
        rows_sku = c.execute(
            """SELECT sku, producto_nombre, COALESCE(es_regalo, 0),
                      COALESCE(tono_label, '') FROM sku_producto_map
               WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
                 AND TRIM(producto_nombre) != ''""",
        ).fetchall()
        _has_tono = True
    except Exception:
        # mig 177 (tono_label) puede no estar aplicada en instancias viejas
        rows_sku = c.execute(
            """SELECT sku, producto_nombre, COALESCE(es_regalo, 0), '' FROM sku_producto_map
               WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
                 AND TRIM(producto_nombre) != ''""",
        ).fetchall()
        _has_tono = False
    for r in rows_sku:
        sku_up = r[0].upper()
        sku_to_prod[sku_up] = r[1]
        prod_to_skus.setdefault(r[1], []).append(sku_up)
        if r[2]:
            skus_regalo.add(sku_up)
        if r[3]:
            tono_por_sku[sku_up] = r[3]

    # FIX #2 · 23-may-2026 Sebastián · "velocidad o cantidad mal" · auditoría:
    # _inferir_ml_presentacion usaba heurística por substring del nombre (default
    # 30ml si no matchea) → cualquier producto nuevo o con nombre inusual
    # caía silenciosamente al default. Ahora se consulta producto_presentaciones
    # (tabla canónica de envases con volumen_ml por SKU Shopify). Si no hay
    # data, fallback heurística + flag ml_inferido visible en UI.
    ml_por_sku = {}
    try:
        for r in c.execute(
            """SELECT UPPER(TRIM(sku_shopify)), volumen_ml
               FROM producto_presentaciones
               WHERE COALESCE(activo,1)=1
                 AND sku_shopify IS NOT NULL
                 AND TRIM(sku_shopify) != ''
                 AND COALESCE(volumen_ml,0) > 0""",
        ).fetchall():
            ml_por_sku[r[0]] = float(r[1])
    except Exception:
        # Tabla puede no existir en tests antiguos
        pass

    # 3. Stock por SKU (re-uso helper)
    from blueprints.programacion import _resolved_stock_por_sku
    resolved_stock = _resolved_stock_por_sku(c.connection, empresa='ANIMUS')
    # resolved_stock: {sku_upper: {descripcion, uds, fuente}}

    # FIX 1-jun-2026 Sebastián · caso "Limpiador BHA: vende pero stock 0".
    # El stock se atribuía SOLO por los SKU de sku_producto_map (skus_de_prod).
    # Si el SKU de la VARIANTE en Shopify (con el que el sync escribe stock_pt)
    # difiere del SKU de la ORDEN (mapeado · con el que SÍ funciona la velocidad),
    # ese stock quedaba huérfano → Stock=0 aunque Shopify tuviera unidades.
    # Atribuimos ese stock huérfano al producto vía producto_presentaciones.sku_shopify
    # (mapeo autoritativo de envases) o, en su defecto, vía la descripción exacta que
    # el sync guardó. ADITIVO: solo cuenta SKUs que NO están en sku_to_prod (los que
    # sí están ya los suma skus_de_prod abajo) → imposible doble-contar.
    _pres_sku_to_prod = {}
    try:
        for _r in c.execute(
            """SELECT UPPER(TRIM(sku_shopify)), producto_nombre
               FROM producto_presentaciones
               WHERE COALESCE(activo,1)=1 AND sku_shopify IS NOT NULL
                 AND TRIM(sku_shopify) != ''""",
        ).fetchall():
            if _r[0] and _r[1]:
                _pres_sku_to_prod[_r[0]] = str(_r[1]).strip()
    except Exception:
        pass
    _prod_nombres_lc = {(p[0] or '').strip().lower(): (p[0] or '').strip()
                        for p in productos if p[0]}
    extra_stock_by_prod_lc = {}   # prod_lc → uds de SKUs huérfanos atribuidos
    for _sku, _info in resolved_stock.items():
        if _sku in sku_to_prod:
            continue   # ya cubierto por skus_de_prod (evita doble conteo)
        _uds = int(_info.get('uds', 0) or 0)
        if _uds <= 0:
            continue
        _p = _pres_sku_to_prod.get(_sku)
        if not _p:
            _desc = (_info.get('descripcion') or '').strip()
            if _desc.lower() in _prod_nombres_lc:
                _p = _prod_nombres_lc[_desc.lower()]
        if _p:
            _k = _p.strip().lower()
            extra_stock_by_prod_lc[_k] = extra_stock_by_prod_lc.get(_k, 0) + _uds

    # 4. Ventas por SKU últimos N días
    # PERF-FIX 23-may-2026 · auditoría · `date(creado_en) >= ?` con función
    # wrapper bloquea uso de idx_aso_creado en PG · ahora comparación directa
    # contra timestamp · index usable
    # FIX 24-may · multi-ventana 30d/60d/90d para detectar aceleración
    # · Sebastián: 'BHA 60d=370/mes pero mayo va a 480/mes'. Antes solo
    # ventana fija promediaba abril+mayo escondiendo tendencia. Ahora
    # calculamos las 3 ventanas en una pasada (1 query).
    ventas_por_sku = {}      # ventana principal (60d default)
    ventas_30d_por_sku = {}  # último mes
    ventas_90d_por_sku = {}  # 3 meses
    _vd_iso = ventana_desde + 'T00:00:00' if 'T' not in ventana_desde else ventana_desde
    # Cutoff ISO para 30d y 90d (independientes de ventana principal)
    _cut30 = (hoy - _td(days=30)).strftime('%Y-%m-%d') + 'T00:00:00'
    _cut90 = (hoy - _td(days=90)).strftime('%Y-%m-%d') + 'T00:00:00'
    # Usar el más amplio de los 3 como WHERE base
    _vd_base = min(_vd_iso, _cut90)
    # SHOPIFY-AUDIT 23-may-PM · filtrar cancelled/refunded para no inflar
    # velocidad con devoluciones + filtro opt-in B2B vs DTC vía env var
    # SHOPIFY_B2B_TAGS (CSV). Si un tag de la orden o cliente coincide,
    # se excluye de velocidad DTC.
    import os as _os_local
    _b2b_tags_raw = (_os_local.environ.get('SHOPIFY_B2B_TAGS') or '').strip()
    _b2b_clauses = ''
    _b2b_params = []
    if _b2b_tags_raw:
        for _t in _b2b_tags_raw.split(','):
            _t = _t.strip().lower()
            if _t:
                _b2b_clauses += " AND LOWER(COALESCE(tags,'')) NOT LIKE ? AND LOWER(COALESCE(customer_tags,'')) NOT LIKE ?"
                _b2b_params.extend(['%' + _t + '%', '%' + _t + '%'])
    # FIX 30-may-2026 · audit Plan · robustez: si tags/customer_tags no existen
    # (mig 166 sin aplicar en PG) y hay filtro B2B, la query crasheaba TODA la
    # planificación. Ahora degrada al SELECT sin filtro B2B en vez de romper.
    _vel_base_sql = """SELECT sku_items, creado_en FROM animus_shopify_orders
           WHERE creado_en >= ?
             AND sku_items IS NOT NULL AND sku_items != ''
             AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
             AND LOWER(COALESCE(estado_pago,'')) NOT IN ('refunded','voided','partially_refunded')"""
    try:
        _vel_rows = c.execute(_vel_base_sql + _b2b_clauses,
                              tuple([_vd_base] + _b2b_params)).fetchall()
    except Exception as _e_b2b:
        log.warning('velocidad · filtro B2B falló (%s) · degradando sin filtro', _e_b2b)
        _vel_rows = c.execute(_vel_base_sql, (_vd_base,)).fetchall()
    for r in _vel_rows:
        try:
            items = _json.loads(r[0]) if r[0] else []
        except Exception:
            continue
        creado = (r[1] or '')
        # Comparaciones string-wise (ISO 8601 ordena correctamente)
        en_60 = creado >= _vd_iso
        en_30 = creado >= _cut30
        en_90 = creado >= _cut90
        for it in items:
            sku = str(it.get("sku", "") or "").strip().upper()
            qty = int(it.get("qty") or it.get("cantidad") or it.get("quantity") or 0)
            if not sku or qty <= 0:
                continue
            # FEATURE 24-may-2026 · Sebastián: SKUs marcados es_regalo=1 no
            # cuentan para velocidad (BBM mini es regalo, no se vende).
            # Sin esto, los regalos inflaban la velocidad y planificación
            # producía bulk para satisfacer demanda ficticia.
            if sku in skus_regalo:
                continue
            if en_60:
                ventas_por_sku[sku] = ventas_por_sku.get(sku, 0) + qty
            if en_30:
                ventas_30d_por_sku[sku] = ventas_30d_por_sku.get(sku, 0) + qty
            if en_90:
                ventas_90d_por_sku[sku] = ventas_90d_por_sku.get(sku, 0) + qty

    # 5. Pipeline 7d (lotes recién fabricados que aún no aparecen en Available)
    # Suma kg de produccion_programada con fin_real_at >= hoy-7d agrupado por producto
    pipeline_kg_por_prod = {}
    for r in c.execute(
        """SELECT producto, COALESCE(SUM(COALESCE(kg_real, cantidad_kg, 0)), 0)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= ?
             AND date(fin_real_at) <= date('now', '-5 hours')
             -- FIX 30-may-2026 · evitar doble conteo con góndola CC: un lote
             -- 'completado' ya pasó a stock_pt (liberación QC) · contarlo además
             -- como pipeline lo sumaba 2 veces e inflaba la cobertura ~7d.
             AND LOWER(COALESCE(estado,'')) NOT IN ('completado','cancelado')
           GROUP BY producto""",
        (pipeline_desde,),
    ).fetchall():
        if r[0]:
            pipeline_kg_por_prod[r[0]] = float(r[1] or 0)

    # 5.b · FIX P0 audit 24-may-2026 · doble-cuenta Fijo↔Sugerida.
    # Antes el cron auto-sugerir veía cobertura insuficiente (porque Fijo
    # pendiente NO contaba como pipeline) y programaba Sugeridas adicionales
    # SOBRE Fijo ya garantizado. Ahora sumamos Fijo del horizonte 60d
    # (estado activo, sin fin_real_at) al pipeline para reflejar que ese
    # bulk va a entrar al stock futuro.
    # Por qué solo Fijo: las Sugeridas son recomendaciones reemplazables;
    # el Fijo es compromiso firme del usuario o B2B. Lo Fijo garantiza
    # entrada de bulk.
    pipeline_fijo_kg_por_prod = {}
    try:
        for r in c.execute(
            """SELECT producto, COALESCE(SUM(COALESCE(cantidad_kg, 0)), 0)
               FROM produccion_programada
               WHERE fin_real_at IS NULL
                 AND COALESCE(estado, 'programado') NOT IN ('cancelado', 'completado')
                 AND COALESCE(origen, '') IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')
                 AND date(fecha_programada) >= date('now', '-5 hours')
                 AND date(fecha_programada) <= date('now', '-5 hours', '+60 days')
               GROUP BY producto"""
        ).fetchall():
            if r[0]:
                pipeline_fijo_kg_por_prod[r[0]] = float(r[1] or 0)
    except Exception:
        pass

    # FIX 30-may-2026 · Sebastián · "el lote no es todo Animus, va una parte a B2B".
    # La porción comprometida a clientes B2B (registrada en pedidos_b2b_lote) NO
    # cubre la demanda DTC de Animus · restarla del pipeline Fijo para que cobertura
    # y "durará X días" reflejen lo que REALMENTE le queda a Animus. Cubre tanto
    # lotes dedicados eos_b2b (100% B2B) como aportes sumados a lotes canónicos.
    b2b_fijo_kg_por_prod = {}
    try:
        for r in c.execute(
            """SELECT pp.producto, COALESCE(SUM(COALESCE(pbl.kg_aporte, 0)), 0)
               FROM produccion_programada pp
               JOIN pedidos_b2b_lote pbl ON pbl.lote_produccion_id = pp.id
               WHERE pp.fin_real_at IS NULL
                 AND COALESCE(pp.estado, 'programado') NOT IN ('cancelado', 'completado')
                 AND COALESCE(pp.origen, '') IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')
                 AND date(pp.fecha_programada) >= date('now', '-5 hours')
                 AND date(pp.fecha_programada) <= date('now', '-5 hours', '+60 days')
               GROUP BY pp.producto"""
        ).fetchall():
            if r[0]:
                b2b_fijo_kg_por_prod[r[0]] = float(r[1] or 0)
    except Exception:
        pass

    # FIX 24-may PM · auto-sugerencia Nivel 1 (Sebastián) · detectar
    # huérfanos vendiendo y sugerirlos al producto cuyo nombre contiene
    # substrings del SKU. Pre-calcular el set de huérfanos para evitar
    # O(n²) en el loop.
    sku_to_prod_keys = set(sku_to_prod.keys())
    huerfanos_dict = {
        sku: uds for sku, uds in ventas_por_sku.items()
        if sku not in sku_to_prod_keys and uds > 0
    }

    def _sugerir_huerfanos(prod_nombre, top_n=3):
        """Devuelve hasta top_n huérfanos cuyo SKU matchea el nombre
        del producto. Scoring por substring largo."""
        if not huerfanos_dict or not prod_nombre:
            return []
        # Palabras del nombre del producto, filtradas (>= 3 chars,
        # no genéricas)
        palabras = [w.upper().strip() for w in prod_nombre.split()
                     if len(w) >= 3 and w.upper().strip() not in
                     ('DE', 'DEL', 'CON', 'PARA', 'EL', 'LA', 'LOS', 'LAS')]
        if not palabras:
            return []
        sugerencias = []
        for sku, uds in huerfanos_dict.items():
            sku_up = sku.upper()
            score = 0
            for w in palabras:
                # Substring exacto >=5 chars · 100 pts
                if len(w) >= 5 and w in sku_up:
                    score += 100
                # Primeros 4 chars · 60 pts
                elif len(w) >= 4 and w[:4] in sku_up:
                    score += 60
                # Primeros 3 chars · 30 pts
                elif w[:3] in sku_up:
                    score += 30
                # Iniciales (1 letra de cada palabra) · 10 pts
                elif w[0] in sku_up:
                    score += 10
            if score >= 60:  # umbral mínimo
                sugerencias.append({
                    'sku': sku, 'uds_60d': int(uds), 'score': score,
                })
        sugerencias.sort(key=lambda x: -x['score'])
        return sugerencias[:top_n]

    # 6. Procesar cada producto
    out = []
    for prod_nombre, codigo, lote_kg, tiene_10ml, uds_10ml, tipo_10ml, imagen, fecha_creacion in productos:
        # SKUs de este producto (puede haber varios: 30ml, 10ml, etc)
        # FIX 23-may-2026 · lookup case-insensitive · sku_producto_map y
        # formula_headers pueden tener diferencias de case/espacios · antes
        # case-sensitive perdía matches válidos
        _prod_key_lc = (prod_nombre or '').strip().lower()
        skus_de_prod = [
            sku for sku, pname in sku_to_prod.items()
            if (pname or '').strip().lower() == _prod_key_lc
        ]

        # Stock total uds + ventas en 3 ventanas (predictiva 24-may PM)
        stock_uds_total = 0
        ventas_periodo_total = 0
        ventas_30d_total = 0
        ventas_90d_total = 0
        for sku in skus_de_prod:
            stk = resolved_stock.get(sku, {})
            stock_uds_total += int(stk.get("uds", 0) or 0)
            ventas_periodo_total += int(ventas_por_sku.get(sku, 0) or 0)
            ventas_30d_total += int(ventas_30d_por_sku.get(sku, 0) or 0)
            ventas_90d_total += int(ventas_90d_por_sku.get(sku, 0) or 0)
        # FIX 1-jun-2026 · sumar stock de SKUs huérfanos (variante Shopify cuyo SKU
        # no está en sku_producto_map pero sí mapea a este producto vía presentaciones
        # o descripción exacta). Caso Limpiador BHA. Aditivo, sin doble conteo.
        stock_uds_total += extra_stock_by_prod_lc.get(_prod_key_lc, 0)

        # ml por presentación · Sebastián 13-may-2026: "los sueros son
        # de 30, los limpiadores de 150, geles e hidratantes de 50 ml".
        # FIX #2 · 23-may-2026 · primero buscar ml en producto_presentaciones
        # ponderado por ventas reales · si no hay match, fallback heurística
        # del nombre + flag ml_inferido visible al usuario.
        ml_inferido = False
        ml_total_pond = 0.0
        uds_total_pond = 0
        for _sku in skus_de_prod:
            ml_sku = ml_por_sku.get(_sku.upper().strip())
            uds_sku = int(ventas_por_sku.get(_sku, 0) or 0)
            if ml_sku and uds_sku > 0:
                ml_total_pond += ml_sku * uds_sku
                uds_total_pond += uds_sku
        if uds_total_pond > 0:
            ml_promedio = ml_total_pond / uds_total_pond
        else:
            # Fallback: 1) ml de cualquier SKU mapeado aunque no haya vendido
            #          2) heurística por nombre (legacy)
            ml_fallback_sku = None
            for _sku in skus_de_prod:
                ml_sku = ml_por_sku.get(_sku.upper().strip())
                if ml_sku:
                    ml_fallback_sku = ml_sku
                    break
            if ml_fallback_sku:
                ml_promedio = ml_fallback_sku
            else:
                ml_promedio = _inferir_ml_presentacion(prod_nombre)
                ml_inferido = True
        # VELOCIDAD PREDICTIVA · Sebastián 24-may PM · "que sea predictivo
        # 100% · una sola velocidad que muestre la realidad". Algoritmo:
        # 1) Calcular vel_30d, vel_60d, vel_90d
        # 2) Detectar tendencia comparando vel_30d vs vel_60d
        # 3) Ponderar dinámicamente:
        #    · Aceleración fuerte (>30%) → confía en 30d + buffer 10%
        #    · Aceleración moderada (>15%) → 60% peso 30d + 40% peso 60d
        #    · Caída fuerte (>15%) → 70% peso 60d (más conservador)
        #    · Estable → 50/50 entre 30d y 60d
        # 4) Cap por arriba/abajo con 90d para no sobre-reaccionar
        # Caso BHA: 30d=15.4, 60d=12.3 → +25% aceleración moderada →
        #   0.6 × 15.4 + 0.4 × 12.3 = 14.16 uds/día = 425/mes (realista)
        # FIX P2 audit 24-may-2026 · ventana efectiva por antigüedad del
        # producto. Antes un producto creado hace 10d con 30 ventas se
        # calculaba vel_60d=0.5 (subestimado 6×). Ahora denominador =
        # min(ventana, dias_desde_creacion) con piso 7d para evitar
        # sobre-amplificación con productos de <1 semana.
        def _dias_desde_creacion_local(fc):
            if not fc:
                return None
            try:
                from datetime import datetime as _dt_v
                return (hoy - _dt_v.strptime(str(fc)[:10], '%Y-%m-%d').date()).days
            except Exception:
                return None
        _dias_prod_vel = _dias_desde_creacion_local(fecha_creacion)
        if _dias_prod_vel and _dias_prod_vel > 0:
            _div_30 = float(min(30, max(_dias_prod_vel, 7)))
            _div_60 = float(min(int(ventana), max(_dias_prod_vel, 7)))
            _div_90 = float(min(90, max(_dias_prod_vel, 7)))
        else:
            _div_30, _div_60, _div_90 = 30.0, float(ventana), 90.0
        vel_30d = ventas_30d_total / _div_30
        vel_60d = ventas_periodo_total / _div_60
        vel_90d = ventas_90d_total / _div_90
        if vel_60d < 0.001:
            # Sin histórico · usar lo poco que haya
            velocidad_uds_dia = max(vel_30d, vel_90d)
            tendencia = 'sin_historico'
        else:
            ratio_30_60 = vel_30d / vel_60d if vel_60d > 0 else 1.0
            if ratio_30_60 > 1.30:
                velocidad_uds_dia = vel_30d * 1.10  # aceleración + buffer
                tendencia = 'aceleracion_fuerte'
            elif ratio_30_60 > 1.15:
                velocidad_uds_dia = vel_30d * 0.6 + vel_60d * 0.4
                tendencia = 'aceleracion_moderada'
            elif ratio_30_60 < 0.70:
                velocidad_uds_dia = vel_30d * 0.3 + vel_60d * 0.7  # caída suave
                tendencia = 'caida_fuerte'
            elif ratio_30_60 < 0.85:
                velocidad_uds_dia = vel_30d * 0.5 + vel_60d * 0.5
                tendencia = 'caida_moderada'
            else:
                velocidad_uds_dia = vel_30d * 0.5 + vel_60d * 0.5
                tendencia = 'estable'
        # Cap con 90d para evitar locuras: nunca menor a vel_90d × 0.5 ni
        # mayor a vel_90d × 2 (si hay histórico 90d significativo)
        if vel_90d > 0.001:
            velocidad_uds_dia = max(velocidad_uds_dia, vel_90d * 0.5)
            velocidad_uds_dia = min(velocidad_uds_dia, vel_90d * 2.0)
        velocidad_kg_dia = (velocidad_uds_dia * ml_promedio) / 1000.0
        # Stock kg = uds × ml / 1000 + pipeline reciente + Fijo pendiente
        # FIX P0 audit 24-may-2026 · sumar Fijo futuro (60d) al stock total
        # para evitar doble-cuenta cuando el cron auto-sugerir corra de nuevo.
        stock_kg_gondola = (stock_uds_total * ml_promedio) / 1000.0
        pipeline_kg = pipeline_kg_por_prod.get(prod_nombre, 0.0)
        pipeline_fijo_kg = pipeline_fijo_kg_por_prod.get(prod_nombre, 0.0)
        # FIX 30-may-2026 · restar la porción B2B de los lotes Fijo: lo comprometido
        # a otros clientes (Fernando Meza, etc.) NO cubre demanda Animus DTC, así que
        # no debe inflar la cobertura. Antes "durará 191d" usaba el lote completo.
        b2b_fijo_kg = b2b_fijo_kg_por_prod.get(prod_nombre, 0.0)
        pipeline_fijo_kg = max(0.0, pipeline_fijo_kg - b2b_fijo_kg)
        stock_kg_total = stock_kg_gondola + pipeline_kg + pipeline_fijo_kg

        # FIX #2-b · 23-may-2026 Sebastián · AZ HIBRID CLEAR tenía
        # lote_size_kg=0.1 en BD → modal planificador sugería 23 lotes
        # de 0.1kg uno por día. Si lote_kg es absurdo (<1kg de bulk),
        # calculamos un lote efectivo = velocidad × 60 días, con flag
        # lote_calculado=true visible al usuario para que arregle BD.
        # FIX 23-may-2026 PM · 30→60d cobertura · antes paso=5d (denso) ·
        # ahora paso=35d (60-cob_alerta 25) · más realista para producción.
        lote_calculado = False
        lote_kg_efectivo = float(lote_kg or 0)
        if lote_kg_efectivo < 1.0 and velocidad_kg_dia > 0.01:
            # ~60d de cobertura como lote estándar · paso re-orden ~35d
            lote_kg_efectivo = max(round(velocidad_kg_dia * 60, 1), 1.0)
            lote_calculado = True

        # Días de cobertura (CON pipeline · stock_kg_total = góndola + producción
        # en camino) · se muestra como anotación "+prod → Xd".
        if velocidad_kg_dia > 0:
            dias_cobertura = round(stock_kg_total / velocidad_kg_dia, 1)
        else:
            dias_cobertura = None
        # FIX 1-jun-2026 Sebastián · días con SOLO stock físico de góndola (sin
        # pipeline). La URGENCIA/alerta se basa en ESTO → un producto agotado
        # (stock 0 → 0d) sale CRÍTICO/rojo arriba aunque tenga lote programado
        # (los chips +prod / 📅 / ⚠ Sin programar indican si la reposición viene).
        # "la condición de generar esa alerta no funciona" · ahora la alerta
        # coincide con la columna 'Alcanza' (que muestra dias_gondola).
        if velocidad_kg_dia > 0:
            dias_gondola = round(stock_kg_gondola / velocidad_kg_dia, 1)
        else:
            dias_gondola = None

        # Urgencia (lógica Sebastián 20-25-45)
        # SHOPIFY-FIX · 22-may-2026 · Bug #6 audit · separar SIN_VENTAS en sub-estados
        # · SIN_HISTORIAL · producto creado < 30 días (sin tiempo de ventas)
        # · SIN_MAPEO · existe formula_headers pero len(skus_de_prod)==0 (huérfano)
        # · SIN_VENTAS_REAL · mapeado + >=30d + 0 ventas (probable descontinuado)
        # FIX 23-may-2026 · auditoría · sub-estados prometidos estaban sin emitir ·
        # ahora SÍ se calculan usando formula_headers.fecha_creacion
        def _dias_desde_creacion(fc):
            if not fc:
                return None
            try:
                from datetime import datetime as _dt_local
                fc10 = str(fc)[:10]
                return (hoy - _dt_local.strptime(fc10, '%Y-%m-%d').date()).days
            except Exception:
                return None
        _dias_prod = _dias_desde_creacion(fecha_creacion)
        if velocidad_uds_dia <= 0.01:
            if not skus_de_prod:
                urgencia = "SIN_MAPEO"
            elif _dias_prod is not None and _dias_prod < 30:
                urgencia = "SIN_HISTORIAL"
            else:
                urgencia = "SIN_VENTAS_REAL"
        elif dias_gondola is None:
            urgencia = "SIN_VENTAS"
        elif dias_gondola <= cob_critico:
            urgencia = "CRITICO"
        elif dias_gondola <= cob_alerta:
            urgencia = "URGENTE"
        elif dias_gondola <= cob_vigilar:
            urgencia = "VIGILAR"
        else:
            urgencia = "OK"

        # Recomendación: 1 lote completo si urgencia en {CRITICO, URGENTE}
        # Para VIGILAR mostramos "próximo lote en X días" sin urgir
        if urgencia in ("CRITICO", "URGENTE"):
            n_lotes_recomendados = 1
            kg_a_producir = float(lote_kg_efectivo)
        else:
            n_lotes_recomendados = 0
            kg_a_producir = 0.0

        # Sumar regalos 10ml si aplica (info para UI)
        regalos_extra_uds = 0
        if tiene_10ml == 1 and tipo_10ml == "regalo" and n_lotes_recomendados > 0:
            regalos_extra_uds = int(uds_10ml or 0) * n_lotes_recomendados

        # Sebastián 25-may-2026 PM · desglose por tono multi-SKU.
        # Caso LIP SERUM (PEACH/MERLOT/MOCCA/MALVA/N) · mismo bulk pero
        # envases distintos. Trae array `tonos[]` cuando hay ≥2 SKUs con
        # tono_label · cada tono con sus ventas + porcentaje del mix +
        # uds estimadas del próximo lote. Si solo hay 1 tono o ninguno,
        # `tonos: []` (frontend no muestra desglose).
        tonos_arr = []
        try:
            skus_del_prod = [s for s in prod_to_skus.get(prod_nombre, [])
                              if s not in skus_regalo]
            # Tonos únicos no vacíos
            _con_tono = [(s, tono_por_sku.get(s, '')) for s in skus_del_prod]
            _con_tono = [(s, t) for s, t in _con_tono if t]
            if len(_con_tono) >= 2:
                # Calcular ventas por tono en la ventana principal
                ventas_por_tono = {}
                for sku_u, tono in _con_tono:
                    ventas_por_tono[tono] = ventas_por_tono.get(tono, 0) + int(
                        ventas_por_sku.get(sku_u, 0))
                _total_uds_tonos = sum(ventas_por_tono.values()) or 1
                # uds estimadas del próximo lote por tono · proporcional al mix
                uds_lote_total = 0
                if ml_promedio > 0 and lote_kg_efectivo > 0:
                    uds_lote_total = int(round(lote_kg_efectivo * 1000.0 / ml_promedio))
                for sku_u, tono in _con_tono:
                    v_t = int(ventas_por_sku.get(sku_u, 0))
                    pct = round(100.0 * v_t / _total_uds_tonos, 1) if _total_uds_tonos > 0 else 0
                    uds_estim_lote = int(round(uds_lote_total * pct / 100.0))
                    tonos_arr.append({
                        'sku': sku_u,
                        'tono_label': tono,
                        'ml_unidad': ml_por_sku.get(sku_u, ml_promedio),
                        'ventas_ventana_uds': v_t,
                        'porcentaje_mix': pct,
                        'uds_estim_lote': uds_estim_lote,
                    })
                # Ordenar por % mix descendente · más vendido primero
                tonos_arr.sort(key=lambda t: -t['porcentaje_mix'])
        except Exception:
            tonos_arr = []

        out.append({
            "codigo_pt": codigo,
            "producto_nombre": prod_nombre,
            "imagen_url": imagen,
            "lote_bulk_kg": lote_kg_efectivo,
            "lote_bulk_kg_bd": float(lote_kg or 0),  # valor crudo BD para diagnóstico
            "lote_calculado": lote_calculado,  # True = ignoramos BD por absurdo

            "tiene_10ml": int(tiene_10ml or 0),
            "uds_10ml_por_lote": int(uds_10ml or 0),
            "tipo_10ml": tipo_10ml or "",
            "stock_uds_total": stock_uds_total,
            "stock_kg_gondola": round(stock_kg_gondola, 2),
            "pipeline_kg": round(pipeline_kg, 2),
            "pipeline_fijo_kg": round(pipeline_fijo_kg, 2),
            "b2b_comprometido_kg": round(b2b_fijo_kg, 2),
            "stock_kg_total": round(stock_kg_total, 2),
            "ventas_periodo_uds": ventas_periodo_total,
            "ventas_30d_uds": ventas_30d_total,
            "ventas_90d_uds": ventas_90d_total,
            "velocidad_uds_dia": round(velocidad_uds_dia, 2),
            "velocidad_kg_dia": round(velocidad_kg_dia, 3),
            "velocidad_uds_dia_30d": round(vel_30d, 2),
            "velocidad_uds_dia_60d": round(vel_60d, 2),
            "velocidad_uds_dia_90d": round(vel_90d, 2),
            "tendencia": tendencia,
            "vel_uds_mes_predictiva": round(velocidad_uds_dia * 30, 0),
            "ml_unidad": ml_promedio,
            "ml_inferido": ml_inferido,  # FIX #2 · True = heurística por nombre, no SKU real
            "lote_size_faltante": float(lote_kg or 0) < 1.0,  # FIX #2-b · BD tiene valor absurdo o falta
            "huerfanos_sugeridos": _sugerir_huerfanos(prod_nombre),  # FIX 24-may · auto-sugerencia
            "dias_cobertura": dias_cobertura,
            # FIX 1-jun-2026 Sebastián · "necesidades debe ser en tiempo real y decir
            # si ya está programado". dias_cobertura SUMA pipeline+Fijo (para que el
            # cron no sobre-sugiera) → un producto con góndola 0 pero lote programado
            # mostraba "95.9d" y parecía estático. dias_gondola = SOLO lo físico en
            # góndola / velocidad → refleja la realidad (góndola 0 → 0d). El front
            # pinta dias_gondola (color real) + badge "✅ Programado / ⚠ Sin programar".
            "dias_gondola": dias_gondola,
            "ya_programado": bool(pipeline_fijo_kg > 0.001),
            "urgencia": urgencia,
            "n_lotes_recomendados": n_lotes_recomendados,
            "kg_a_producir": kg_a_producir,
            "regalos_extra_uds": regalos_extra_uds,
            "tonos": tonos_arr,
            "n_tonos": len(tonos_arr),
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
    # PERF-FIX 23-may-2026 · auditoría · antes agregaba TODOS los movimientos
    # (100k+ filas) pero solo se usan ~40-80 MPs de productos activos · ahora
    # restringe con WHERE material_id IN (subquery de formula_items activos) ·
    # PG usa idx_mov_material_id + idx_fi_material_id (mig 152)
    mp_stock_g = {}
    mp_tiene_movimientos = set()
    for r in c.execute(
        """SELECT material_id,
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad
                                    WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad
                                    ELSE 0 END), 0),
                  COUNT(*) AS n_mov
           FROM movimientos
           WHERE material_id IS NOT NULL AND TRIM(material_id) != ''
             AND material_id IN (
                 SELECT DISTINCT fi.material_id
                 FROM formula_items fi
                 JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
                 WHERE COALESCE(fh.activo,1) = 1
                   AND fi.material_id IS NOT NULL
                   AND TRIM(fi.material_id) != ''
             )
           GROUP BY material_id""",
    ).fetchall():
        mid = str(r[0]).strip()
        mp_stock_g[mid] = max(float(r[1] or 0), 0)
        if int(r[2] or 0) > 0:
            mp_tiene_movimientos.add(mid)

    # PERF FIX 24-may PM · auditoría agente · pre-cargar pendiente compras
    # bulk para evitar N+1 (era ~2000 queries · ahora 2 GROUP BY).
    try:
        from blueprints.compras import _pendiente_en_compras_bulk as _pend_bulk
        pendiente_compras_g = _pend_bulk(c)
    except Exception:
        pendiente_compras_g = {}

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
    # PERF FIX 24-may PM · auditoría agente · era N+1 (~70 productos × 1
    # query = 70 queries) · ahora 1 sola query con CTE/JOIN para traer
    # fecha + kg en un solo pass.
    ultima_prod = {}
    for r in c.execute(
        """SELECT pp.producto,
                  pp.fecha_programada,
                  COALESCE(pp.kg_real, pp.cantidad_kg, 0) AS kg
           FROM produccion_programada pp
           JOIN (
               SELECT producto, MAX(fecha_programada) AS f
               FROM produccion_programada
               WHERE fin_real_at IS NOT NULL
                 AND COALESCE(kg_real, cantidad_kg, 0) > 0
               GROUP BY producto
           ) ultimo ON ultimo.producto = pp.producto
                    AND ultimo.f = pp.fecha_programada
           WHERE pp.fin_real_at IS NOT NULL
             AND COALESCE(pp.kg_real, pp.cantidad_kg, 0) > 0""",
    ).fetchall():
        # Una fila puede haber varias por mismo (producto, fecha) · tomamos primera
        if r[0] not in ultima_prod:
            ultima_prod[r[0]] = {"fecha": r[1], "kg": round(float(r[2] or 0), 2)}

    # Inyectar lotes pendientes + horizonte en cada producto
    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()

    # FIX 23-may-2026 Sebastián · "fecha sugerida ilógica" · antes la
    # próxima se anclaba SOLO en la última producción completada en Kanban
    # (fin_real_at). Si la última fue hace 6 meses, la próxima salía en el
    # pasado · si había un Fijo futuro ya programado, lo ignoraba.
    # Ahora la base es max(última completada, último Fijo programado futuro)
    # y se clampa proxima >= hoy+3d para no proponer fechas pasadas.
    # PERF FIX 24-may PM · igual que ultima_prod · era N+1 (70 queries) ·
    # ahora 1 sola query con JOIN trae fecha + kg en un pase.
    ult_fijo_prog = {}
    ult_fijo_kg = {}
    for r in c.execute(
        """SELECT pp.producto,
                  substr(pp.fecha_programada,1,10) AS f,
                  pp.cantidad_kg
           FROM produccion_programada pp
           JOIN (
               SELECT producto, MAX(fecha_programada) AS fmax
               FROM produccion_programada
               WHERE COALESCE(origen,'') IN ('eos_plan','eos_b2b','eos_retroactivo')
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                 AND fin_real_at IS NULL
                 AND COALESCE(cantidad_kg,0) > 0
               GROUP BY producto
           ) ultimo ON ultimo.producto = pp.producto
                    AND ultimo.fmax = pp.fecha_programada
           WHERE COALESCE(pp.origen,'') IN ('eos_plan','eos_b2b','eos_retroactivo')
             AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
             AND pp.fin_real_at IS NULL
             AND COALESCE(pp.cantidad_kg,0) > 0""",
    ).fetchall():
        if r[0] not in ult_fijo_prog:
            ult_fijo_prog[r[0]] = r[1]
            ult_fijo_kg[r[0]] = float(r[2] or 0)

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

        # Horizonte: ancla = max(última completada, último Fijo programado)
        up = ultima_prod.get(p["producto_nombre"])
        fpf = ult_fijo_prog.get(p["producto_nombre"])
        fpk = ult_fijo_kg.get(p["producto_nombre"]) or 0.0
        # Determinar mejor ancla
        ancla_fecha = None
        ancla_kg = 0.0
        ancla_es_fijo_futuro = False
        if up and up.get("fecha"):
            try:
                f_up = _date.fromisoformat(up["fecha"][:10])
            except Exception:
                f_up = None
            if fpf:
                try:
                    f_fp = _date.fromisoformat(fpf)
                except Exception:
                    f_fp = None
                if f_fp and (not f_up or f_fp > f_up):
                    ancla_fecha = f_fp
                    ancla_kg = fpk
                    ancla_es_fijo_futuro = True
                else:
                    ancla_fecha = f_up
                    ancla_kg = float(up.get("kg") or 0)
            else:
                ancla_fecha = f_up
                ancla_kg = float(up.get("kg") or 0)
        elif fpf:
            try:
                ancla_fecha = _date.fromisoformat(fpf)
                ancla_kg = fpk
                ancla_es_fijo_futuro = True
            except Exception:
                ancla_fecha = None

        if up and up.get("fecha"):
            p["ultima_produccion_fecha"] = up["fecha"]
            p["ultima_produccion_kg"] = up["kg"]
            try:
                f_up2 = _date.fromisoformat(up["fecha"][:10])
                p["dias_desde_ultima"] = (hoy - f_up2).days
            except Exception:
                p["dias_desde_ultima"] = None
        else:
            p["ultima_produccion_fecha"] = None
            p["ultima_produccion_kg"] = 0.0
            p["dias_desde_ultima"] = None

        p["ancla_es_fijo_futuro"] = ancla_es_fijo_futuro
        if ancla_es_fijo_futuro and ancla_fecha:
            p["ultimo_fijo_programado_fecha"] = ancla_fecha.isoformat()
            p["ultimo_fijo_programado_kg"] = ancla_kg
        else:
            p["ultimo_fijo_programado_fecha"] = None
            p["ultimo_fijo_programado_kg"] = 0.0

        if ancla_fecha and p["velocidad_kg_dia"] > 0 and ancla_kg > 0:
            dur_dias = int(ancla_kg / p["velocidad_kg_dia"])
            p["duracion_lote_dias"] = dur_dias
            try:
                proxima_calc = ancla_fecha + _td(days=max(1, dur_dias - cob_alerta))
                # Clamp: nunca proponer fecha en el pasado o muy próxima
                proxima = max(proxima_calc, hoy + _td(days=3))
                p["proxima_sugerida_fecha"] = proxima.isoformat()
                p["proxima_sugerida_dias"] = (proxima - hoy).days
                p["proxima_clamped"] = (proxima != proxima_calc)
            except Exception:
                p["proxima_sugerida_fecha"] = None
                p["proxima_sugerida_dias"] = None
                p["proxima_clamped"] = False
        else:
            p["duracion_lote_dias"] = None
            p["proxima_sugerida_fecha"] = None
            p["proxima_sugerida_dias"] = None
            p["proxima_clamped"] = False

        # Diagnostic SKUs · ¿este producto tiene mapeo Shopify?
        # FIX 23-may-2026 · CRÍTICO Sebastián · antes usaba `prod_nombre`
        # (variable del loop anterior · cerrada con el último producto) en
        # lugar de p["producto_nombre"] · resultado: TODOS los productos
        # marcaban sin_mapeo=true porque comparaban contra el MISMO nombre
        # (el último iterado). Velocidad calculaba bien pero la urgencia
        # caía a SIN_MAPEO para todo. Síntoma reportado: "todos los productos
        # salen con SIN_MAPEO aunque están mapeados"
        _prod_aqui = p["producto_nombre"]
        # Lookup case-insensitive · sku_producto_map y formula_headers pueden
        # tener diferencia de case/espacios · normalizar ambos lados
        _prod_key = (_prod_aqui or '').strip().lower()
        skus_de_este = [
            s for k, vs in prod_to_skus.items() if (k or '').strip().lower() == _prod_key
            for s in vs
        ]
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
            # Sebastián 14-may-2026: MPs SIN historial de movimientos
            # (nunca entradas ni salidas) NO se chequean · son códigos
            # nuevos importados desde Excel · planta probablemente las
            # tiene en bodega · y AGUA (MPAGUALI01) se hace en planta.
            # Solo bloquear si la MP tiene movimientos previos (probó
            # ser una MP "trackeada") Y su stock actual no cubre lo necesario.
            # FIX 23-may-2026 · auditoría · `mps_faltantes` NO restaba
            # `_pendiente_en_compras_g` · Necesidades reportaba FALTAN_MPS
            # aunque Catalina ya había emitido SOL/OC · bulk re-creaba SOL
            # duplicada · ahora consistente con producciones-faltantes
            # PERF FIX 24-may PM · era N+1 (2000+ queries por request) ·
            # ahora bulk pre-cargado UNA vez al inicio del loop principal.
            faltantes = []
            for it in items_form:
                mid = str(it["material_id"]).strip()
                # Agua: nunca chequear (consumible infinito)
                if mid == 'MPAGUALI01':
                    continue
                # MPs sin historial de movimientos: asumir disponibles
                if mid not in mp_stock_g and mid not in mp_tiene_movimientos:
                    continue
                disponible_g = mp_stock_g.get(mid, 0.0)
                pendiente_g = pendiente_compras_g.get(mid, 0.0)
                falta = it["necesario_g"] - disponible_g - pendiente_g
                if falta > 0.01:  # tolerancia gramos
                    faltantes.append({
                        "material_id": it["material_id"],
                        "material_nombre": it["material_nombre"],
                        "necesario_g": it["necesario_g"],
                        "disponible_g": round(disponible_g, 2),
                        "pendiente_compras_g": round(pendiente_g, 2),
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
    lote_ids_para_b2b = []
    # FEATURE 24-may noche · agregar distribucion_resumen al SELECT con
    # COALESCE para soportar BDs antes de mig 176.
    try:
        prod_rows_plan = c.execute(
            """SELECT pp.producto, pp.id, pp.fecha_programada, pp.estado,
                      pp.origen, COALESCE(pp.cantidad_kg, 0),
                      pp.motivo_pausa, pp.pausado_at, pp.observaciones,
                      COALESCE(pp.distribucion_resumen, '')
               FROM produccion_programada pp
               WHERE pp.estado IN ('pendiente','programado','en_curso','esperando_recurso')
                 AND pp.fin_real_at IS NULL
               ORDER BY pp.fecha_programada ASC""",
        ).fetchall()
    except Exception:
        # Fallback si mig 176 aún no aplicada
        prod_rows_plan = [tuple(list(r) + ['']) for r in c.execute(
            """SELECT pp.producto, pp.id, pp.fecha_programada, pp.estado,
                      pp.origen, COALESCE(pp.cantidad_kg, 0),
                      pp.motivo_pausa, pp.pausado_at, pp.observaciones
               FROM produccion_programada pp
               WHERE pp.estado IN ('pendiente','programado','en_curso','esperando_recurso')
                 AND pp.fin_real_at IS NULL
               ORDER BY pp.fecha_programada ASC""",
        ).fetchall()]
    for r in prod_rows_plan:
        prod_nombre = (r[0] or "").strip()
        if not prod_nombre:
            continue
        lid = int(r[1])
        lote_ids_para_b2b.append(lid)
        plan_por_producto.setdefault(prod_nombre, []).append({
            "id": lid,
            "fecha": (r[2] or "")[:10],
            "estado": r[3],
            "origen": r[4],
            "kg": float(r[5] or 0),
            "motivo_pausa": r[6],
            "pausado_at": r[7],
            "obs_preview": (r[8] or "")[:80],
            "distribucion_resumen": (r[9] or "")[:300],
        })

    # FEATURE B2B 24-may-2026 · enriquecer cada lote con su desglose B2B
    # vía pedidos_b2b_lote (mig 171). Permite a la UI mostrar el chip
    # "+ Xkg Fernando" en el card sin un fetch extra por lote.
    aportes_por_lote = {}
    if lote_ids_para_b2b:
        try:
            ph = ','.join('?' * len(lote_ids_para_b2b))
            for ar in c.execute(
                f"""SELECT lote_produccion_id, cliente_nombre,
                          SUM(kg_aporte) AS kg, COUNT(*) AS n_pedidos
                   FROM pedidos_b2b_lote
                   WHERE lote_produccion_id IN ({ph})
                   GROUP BY lote_produccion_id, cliente_nombre""",
                lote_ids_para_b2b,
            ).fetchall():
                aportes_por_lote.setdefault(ar[0], []).append({
                    'cliente': ar[1] or '',
                    'kg': round(float(ar[2] or 0), 2),
                    'n_pedidos': int(ar[3] or 0),
                })
        except Exception:
            pass
    for lotes in plan_por_producto.values():
        for lote in lotes:
            ap = aportes_por_lote.get(lote['id'], [])
            lote['aportes_b2b'] = ap
            kg_b2b = sum(a['kg'] for a in ap)
            lote['kg_b2b'] = round(kg_b2b, 2)
            lote['kg_dtc'] = round(max(lote['kg'] - kg_b2b, 0), 2)
            lote['tiene_b2b'] = bool(ap)

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

    # Ordenar por urgencia + días de góndola (físico) ascendente · FIX 1-jun-2026:
    # antes el desempate usaba dias_cobertura (con pipeline) → un agotado con lote
    # programado quedaba debajo. Ahora desempata por dias_gondola (lo realmente
    # disponible) para que lo más agotado salga primero.
    ORDEN = {"CRITICO": 0, "URGENTE": 1, "VIGILAR": 2, "OK": 3,
             "SIN_VENTAS": 4, "SIN_VENTAS_REAL": 4, "SIN_HISTORIAL": 4, "SIN_MAPEO": 5}
    out.sort(key=lambda x: (
        ORDEN.get(x["urgencia"], 9),
        x.get("dias_gondola") if x.get("dias_gondola") is not None else 99999,
    ))
    return out


@bp.route("/api/plan/factibilidad", methods=["GET"])
def plan_factibilidad():
    """Factibilidad del plan completo · ¿alcanzan las MP para todo lo programado?

    Toma las producciones de `produccion_programada` en un horizonte (default
    30 días) que aún NO descontaron inventario, explota cada fórmula × cantidad
    y hace una asignación greedy por fecha contra el stock real de MP.

    SOLO LECTURA · no modifica ninguna programación ni el calendario.

    Query params:
        dias: horizonte en días (default 30, máx 365)
        solo_fijo: 1 (default) = solo producciones Fijas
                   (eos_plan/eos_b2b/eos_retroactivo) · 0 = incluir todas
                   (Sugeridas IA, manual). Sebastián 23-may pidió no inflar
                   con sugerencias IA.
        incluir_atrasadas: 1 (default) = producciones con fecha pasada pero
                           estado pendiente (su MP aún se va a consumir)

    Devuelve: resumen, lista de producciones (factible/bloqueada + MP faltante)
    y compra_consolidada (qué MP comprar para que el plan entero sea ejecutable).

    AUDITORÍA 23-may-2026 · 3 agentes encontraron 11 bugs · todos cerrados:
      F1 · usar _get_mp_stock (cuarentena + bridge + memo)
      F2 · descontar OCs/SOLs pendientes de compra_consolidada
      F3 · JOIN producto con UPPER+TRIM
      F4 · MP sin movimientos = stock 0 (no skip silente)
      F5 · greedy consistente · consume stock incluso si bloqueada
      F6 · default solo_fijo=1 (consistente con Abastecimiento)
      F7 · incluir atrasadas pendientes
      F8 · excluir productos descontinuados
      F9 · fallback lotes mejor cuando lote_size=0
      F10 · enriquecer compra con proveedor + lead_time
      F11 · marcar MPs archivadas en maestro_mps
    """
    err = _require_login()
    if err:
        return err
    from datetime import datetime, timedelta, timezone
    try:
        dias = max(1, min(365, int(request.args.get("dias", 30))))
    except Exception:
        dias = 30
    solo_fijo = str(request.args.get('solo_fijo', '1')).lower() in ('1', 'true', 'yes')
    incluir_atrasadas = str(request.args.get('incluir_atrasadas', '1')).lower() in ('1', 'true', 'yes')
    conn = get_db()
    c = conn.cursor()

    # 1. Fórmula por producto · necesario_g por MP para UN lote bulk.
    # F3 · UPPER+TRIM en JOIN y en la key del dict
    formula_por_prod = {}
    lote_size = {}
    for r in c.execute(
        """SELECT UPPER(TRIM(fi.producto_nombre)) AS prod_norm,
                  fi.material_id,
                  COALESCE(fi.material_nombre,'') AS mat_nom,
                  COALESCE(fi.cantidad_g_por_lote,0) AS cant_g,
                  COALESCE(fi.porcentaje,0) AS pct,
                  COALESCE(fh.lote_size_kg,0) AS lote_kg
           FROM formula_items fi
           JOIN formula_headers fh
                  ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(fi.producto_nombre))
           WHERE COALESCE(fh.activo,1)=1
             AND fi.material_id IS NOT NULL AND TRIM(fi.material_id)!=''""",
    ).fetchall():
        prod, mid, mnom, cant_g, pct, lote_kg = r
        if lote_kg and float(lote_kg) > 0:
            lote_size[prod] = float(lote_kg)
        nec_g = float(cant_g or 0)
        if nec_g <= 0 and pct and lote_kg and float(lote_kg) > 0:
            nec_g = (float(pct)/100.0) * float(lote_kg) * 1000.0
        if nec_g <= 0:
            continue
        formula_por_prod.setdefault(prod, []).append({
            "material_id": str(mid).strip(),
            "material_nombre": str(mnom)[:50],
            "necesario_g_lote": round(nec_g, 2),
        })

    # 2. Stock MP canonical · F1 · usar _get_mp_stock que respeta cuarentena
    # + bridge + memoización en flask.g (no duplica scan masivo)
    try:
        from blueprints.programacion import _get_mp_stock as _gms
        mp_stock_raw = _gms(conn)
    except Exception:
        mp_stock_raw = {}
    # mp_stock_raw incluye keys por material_id, nombre upper, normalizado ·
    # nos interesa solo los material_id (que son los keys que usan formulas)
    mp_stock_g = {}
    mp_tiene_mov = set()
    for k, v in mp_stock_raw.items():
        # Heurística: keys con formato 'MPNNNNN' o similar (corta + sin espacios)
        # los tratamos como material_id. El resto son nombres alternativos.
        if k and len(k) <= 30 and ' ' not in k and v >= 0:
            ks = str(k).strip()
            mp_stock_g[ks] = float(v or 0)
            if v > 0:
                mp_tiene_mov.add(ks)

    # 3. Pendientes en compras (OCs activas + SOLs sin OC) · F2
    pendientes_compras = {}
    try:
        for cm, gp in c.execute("""
            SELECT UPPER(TRIM(sci.codigo_mp)),
                   COALESCE(SUM(sci.cantidad_g),0)
            FROM solicitudes_compra_items sci
            JOIN solicitudes_compra sc ON sc.numero = sci.numero
            WHERE sc.estado IN ('Pendiente','Aprobada')
              AND COALESCE(sc.numero_oc,'')=''
              AND sci.codigo_mp IS NOT NULL AND TRIM(sci.codigo_mp) != ''
              AND COALESCE(sc.categoria,'') NOT IN ('Empaque','Material de Empaque')
            GROUP BY UPPER(TRIM(sci.codigo_mp))
        """).fetchall():
            pendientes_compras[cm] = float(gp or 0)
    except Exception:
        pass
    # FIX 24-may-2026 noche · Sebastián clarificó que Factibilidad debe ser
    # simulación TEMPORAL acumulativa · OC con fecha_entrega_est conocida
    # debe sumarse al stock SOLO cuando llega (no antes). Antes el algoritmo
    # sumaba TODO al stock inicial sin timeline → lotes del 5-jun y del
    # 10-jun competían por stock que llega el 15-jun.
    #
    # pendientes_compras = SOL sin OC + OC sin fecha (asume "ya")
    # oc_timeline[fecha_iso][mid] = suma de OC que llega ese día específico
    oc_timeline = {}
    try:
        for cm, fent, gp in c.execute("""
            SELECT UPPER(TRIM(oci.codigo_mp)),
                   COALESCE(oc.fecha_entrega_est,'') AS fecha_est,
                   COALESCE(SUM(oci.cantidad_g - COALESCE(oci.cantidad_recibida_g,0)),0)
            FROM ordenes_compra_items oci
            JOIN ordenes_compra oc ON oc.numero_oc = oci.numero_oc
            WHERE oc.estado IN ('Borrador','Revisada','Autorizada','Parcial')
              AND oci.codigo_mp IS NOT NULL AND TRIM(oci.codigo_mp) != ''
            GROUP BY UPPER(TRIM(oci.codigo_mp)), COALESCE(oc.fecha_entrega_est,'')
        """).fetchall():
            cant = float(gp or 0)
            if cant <= 0:
                continue
            fent_str = (fent or '')[:10].strip()
            if not fent_str:
                # OC sin fecha conocida → asume disponible "ya"
                pendientes_compras[cm] = pendientes_compras.get(cm, 0.0) + cant
            else:
                oc_timeline.setdefault(fent_str, {})[cm] = \
                    oc_timeline.get(fent_str, {}).get(cm, 0.0) + cant
    except Exception:
        pass

    # 4. Info MP (proveedor + lead time + activo) · F10 · F11
    mp_meta = {}
    try:
        for r in c.execute("""
            SELECT mm.codigo_mp,
                   COALESCE(mm.nombre_comercial, mm.nombre_inci, mm.codigo_mp),
                   COALESCE(NULLIF(TRIM(mlt.proveedor_principal),''),
                            mm.proveedor, ''),
                   COALESCE(mlt.lead_time_dias, 14),
                   COALESCE(mm.activo, 1)
            FROM maestro_mps mm
            LEFT JOIN mp_lead_time_config mlt ON mlt.material_id = mm.codigo_mp
        """).fetchall():
            mp_meta[r[0]] = {
                'nombre': r[1] or r[0],
                'proveedor': (r[2] or '').strip(),
                'lead_time_dias': int(r[3] or 14),
                'activo': bool(r[4]),
            }
    except sqlite3.OperationalError:
        pass

    # 5. Productos descontinuados · F8
    productos_descontinuados = set()
    try:
        for r in c.execute("""
            SELECT UPPER(TRIM(producto_nombre))
            FROM sku_planeacion_config
            WHERE LOWER(COALESCE(estado,'activo')) IN ('descontinuado','desactivado','inactivo')
        """).fetchall():
            if r[0]:
                productos_descontinuados.add(r[0])
    except sqlite3.OperationalError:
        pass

    # 6. Producciones programadas en el horizonte que aún no descontaron MP.
    # F6 · solo_fijo · F7 · incluir atrasadas pendientes
    hoy = datetime.now(timezone.utc) - timedelta(hours=5)   # hora Colombia
    desde = hoy.strftime("%Y-%m-%d")
    hasta = (hoy + timedelta(days=dias)).strftime("%Y-%m-%d")
    where_fechas = (
        " AND ((substr(fecha_programada,1,10) >= ? "
        "       AND substr(fecha_programada,1,10) <= ?)"
    )
    params_fechas = [desde, hasta]
    if incluir_atrasadas:
        where_fechas += (
            " OR (substr(fecha_programada,1,10) < ? "
            "     AND LOWER(COALESCE(estado,'')) IN ('pendiente','programado','atrasada')"
            "     AND inventario_descontado_at IS NULL)"
        )
        params_fechas.append(desde)
    where_fechas += ")"
    where_origen = ""
    if solo_fijo:
        where_origen = (
            " AND COALESCE(origen,'') IN "
            "     ('eos_plan','eos_b2b','eos_retroactivo')"
        )
    # FIX audit 24-may-2026 noche · alineado con consumo-horizontes ·
    # 'esperando_recurso' es lote pausado por falta de MP · si lo cuento
    # como consumo de MP el cálculo es circular (ese lote NO se va a
    # producir hasta que tenga la MP que le falta).
    sql_prog = (
        """SELECT id, producto, fecha_programada, COALESCE(cantidad_kg,0),
                  COALESCE(lotes,1), COALESCE(origen,'')
           FROM produccion_programada
           WHERE inventario_descontado_at IS NULL
             AND LOWER(COALESCE(estado,'')) NOT IN
                 ('cancelada','cancelado','completada','completado','esperando_recurso')"""
        + where_fechas + where_origen +
        " ORDER BY fecha_programada ASC, id ASC"
    )
    filas = c.execute(sql_prog, params_fechas).fetchall()

    # 7. SIMULACIÓN TEMPORAL ACUMULATIVA · Sebastián 24-may-2026 noche:
    # "factibilidad debe pararse en el ahora · con el inventario actual ·
    # mostrar de allí en adelante · acumulativo · si la producción de hoy
    # usa algo de mañana debe descontar".
    #
    # Stock inicial = stock kardex + SOL/OC sin fecha (lump-sum, "ya está").
    # Luego procesamos eventos en orden cronológico:
    #   - LLEGA_OC(fecha, mid, cant) → stock[mid] += cant
    #   - PRODUCCION(fecha, lote)    → evaluar faltantes con stock actual,
    #                                  descontar (factible o bloqueada).
    # Así un lote del 10-jun ve el stock ya consumido por los del 5-jun
    # MÁS las OC que llegaron entre 5-jun y 10-jun.
    stock = dict(mp_stock_g)
    # Stock inicial incluye pendientes sin fecha (SOL en proceso + OC sin
    # fecha conocida · asumimos "ya disponibles" sin compromiso temporal).
    for mid, cant in pendientes_compras.items():
        stock[mid] = stock.get(mid, 0.0) + float(cant or 0)

    # Construir lista de eventos cronológicos: producciones + arribos OC.
    # Cada evento es (fecha_iso, tipo, payload). Sort por fecha + prioridad
    # (las OC que llegan el mismo día primero, para que los lotes del día
    # las puedan usar).
    # FIX 24-may-2026 noche · Sebastián: "factibilidad muestra producciones
    # que ya pasaron". Los lotes con fecha < hoy y estado activo (no
    # iniciados aún) son demanda real pendiente · van a producirse, solo
    # tarde. Los re-ubicamos en el timeline AL DÍA DE HOY (para que
    # consuman stock actual primero) pero marcamos `atrasada=true` con
    # `dias_atraso` para que la UI muestre badge en vez de fecha confusa.
    eventos = []
    for fid, prod, fecha, cant_kg, lotes, origen_v in filas:
        f_iso = str(fecha or '')[:10]
        # Re-ubicar atrasados a "hoy" en el timeline. Mantenemos fecha
        # original en el payload para que la UI pueda mostrar la real.
        f_efectiva = max(f_iso, desde) if f_iso else desde
        eventos.append((f_efectiva, 1, ('PROD', fid, prod, fecha, cant_kg, lotes, origen_v, f_iso)))
    for f_oc, mids in oc_timeline.items():
        # OC con fecha futura · si ya pasó (f_oc < hoy) la consideramos disponible
        # ya hoy (asumimos que llegó). Sino, mantiene su fecha real.
        f_efectiva = max(f_oc, desde)
        eventos.append((f_efectiva, 0, ('OC', mids)))
    eventos.sort(key=lambda e: (e[0], e[1]))

    producciones = []
    sin_formula = 0
    descontinuados_n = 0
    necesidad_total = {}          # material_id -> gramos que pide TODO el plan
    nombre_mp = {}
    for _f_iso, _prio, ev in eventos:
        ev_tipo = ev[0]
        if ev_tipo == 'OC':
            # Llegó OC · suma al stock antes de procesar producciones del día
            mids = ev[1]
            for mid, cant in mids.items():
                stock[mid] = stock.get(mid, 0.0) + float(cant or 0)
            continue
        # ev_tipo == 'PROD'
        _, fid, prod, fecha, cant_kg, lotes, origen_v, f_iso_original = ev
        prod_norm = str(prod or '').strip().upper()
        # Calcular si es atrasada y cuántos días
        atrasada = bool(f_iso_original and f_iso_original < desde)
        dias_atraso = 0
        if atrasada:
            try:
                from datetime import date as _date_a
                dias_atraso = (
                    _date_a.fromisoformat(desde) -
                    _date_a.fromisoformat(f_iso_original)
                ).days
            except Exception:
                dias_atraso = 0
        # F8 · skip descontinuados
        if prod_norm in productos_descontinuados:
            descontinuados_n += 1
            continue
        items = formula_por_prod.get(prod_norm)
        if not items:
            sin_formula += 1
            producciones.append({
                "id": fid, "producto": prod, "fecha": fecha,
                "cantidad_kg": round(float(cant_kg or 0), 1),
                "factible": None, "sin_formula": True, "mps_faltantes": [],
                "origen": origen_v,
                "atrasada": atrasada, "dias_atraso": dias_atraso,
            })
            continue
        lk = lote_size.get(prod_norm, 0)
        if cant_kg and float(cant_kg) > 0 and lk > 0:
            n_lotes = float(cant_kg) / lk
        elif cant_kg and float(cant_kg) > 0 and lk <= 0:
            n_lotes = 1.0
            lk = float(cant_kg)
        else:
            n_lotes = float(lotes or 1)
        req = []
        for it in items:
            mid = it["material_id"]
            if mid == 'MPAGUALI01':       # agua · consumible infinito
                continue
            need = it["necesario_g_lote"] * n_lotes
            if lk > 0 and lk != lote_size.get(prod_norm, lk):
                need = it["necesario_g_lote"] * (float(cant_kg) / lk)
            req.append((mid, it["material_nombre"], need))
            necesidad_total[mid] = necesidad_total.get(mid, 0.0) + need
            nombre_mp[mid] = it["material_nombre"]
        faltantes = []
        for mid, mnom, need in req:
            disp = stock.get(mid, 0.0)
            if need - disp > 0.01:
                faltantes.append({
                    "material_id": mid, "material_nombre": mnom,
                    "necesario_g": round(need, 1),
                    "disponible_g": round(max(disp, 0.0), 1),
                    "faltante_g": round(need - disp, 1),
                })
        factible = len(faltantes) == 0
        # F5 · consumir stock SIEMPRE (factible o bloqueada) · si A bloquea
        # MP-X, B que la comparte tampoco la tiene en su fecha posterior.
        for mid, _mnom, need in req:
            stock[mid] = max(stock.get(mid, 0.0) - need, 0.0)
        producciones.append({
            "id": fid, "producto": prod, "fecha": fecha,
            "cantidad_kg": round(float(cant_kg or 0), 1),
            "factible": factible, "sin_formula": False,
            "mps_faltantes": faltantes,
            "origen": origen_v,
            "atrasada": atrasada, "dias_atraso": dias_atraso,
        })

    # 8. Compra consolidada · F2 descontar pendientes · F10 proveedor + LT
    compra = []
    for mid, total_need in necesidad_total.items():
        mid_up = mid.upper()
        pendiente = float(pendientes_compras.get(mid_up, 0))
        stock_actual = float(mp_stock_g.get(mid, 0))
        falta = total_need - stock_actual - pendiente
        if falta > 0.01:
            meta = mp_meta.get(mid, {})
            compra.append({
                "material_id": mid,
                "material_nombre": meta.get('nombre') or nombre_mp.get(mid, ''),
                "proveedor_sugerido": meta.get('proveedor', ''),
                "lead_time_dias": meta.get('lead_time_dias', 14),
                "mp_activo": meta.get('activo', True),
                "necesidad_total_g": round(total_need, 1),
                "stock_actual_g": round(stock_actual, 1),
                "pendiente_compras_g": round(pendiente, 1),
                "faltante_g": round(falta, 1),
                "faltante_kg": round(falta/1000.0, 2),
            })
    # Ordenar por faltante desc · MPs archivadas al final
    compra.sort(key=lambda x: (not x.get('mp_activo', True), -x["faltante_g"]))

    n_fact = sum(1 for p in producciones if p["factible"] is True)
    n_bloq = sum(1 for p in producciones if p["factible"] is False)
    return jsonify({
        "horizonte_dias": dias,
        "solo_fijo": solo_fijo,
        "incluir_atrasadas": incluir_atrasadas,
        "resumen": {
            "total": len(producciones),
            "factibles": n_fact,
            "bloqueadas": n_bloq,
            "sin_formula": sin_formula,
            "descontinuados_excluidos": descontinuados_n,
            "mps_a_comprar": len(compra),
        },
        "producciones": producciones,
        "compra_consolidada": compra,
    })


_FACTIBILIDAD_PLAN_HTML = """<!doctype html>
<html lang="es-CO"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Factibilidad del Plan · EOS</title>
<style>
  body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:20px;}
  h1{font-size:20px;margin:0 0 4px;}
  .sub{color:#8b949e;font-size:13px;margin-bottom:18px;}
  .cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;}
  .card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;min-width:110px;}
  .card .n{font-size:1.9em;font-weight:700;}
  .card .l{font-size:11px;color:#8b949e;}
  .verde{color:#3fb950;} .rojo{color:#f85149;} .gris{color:#8b949e;} .ama{color:#d29922;}
  select{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 8px;}
  table{width:100%;border-collapse:collapse;margin-top:6px;font-size:13px;}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #21262d;vertical-align:top;}
  th{color:#8b949e;font-weight:600;}
  .sec{font-size:15px;font-weight:700;margin:24px 0 4px;}
  .pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;}
  .pill.ok{background:#1f3b27;color:#3fb950;}
  .pill.bloq{background:#3d1f1f;color:#f85149;}
  .pill.sf{background:#2a2a2a;color:#8b949e;}
  .falta{color:#f85149;font-size:12px;}
  #err{color:#f85149;margin:8px 0;}
</style></head><body>
<h1>Factibilidad del Plan</h1>
<div class="sub">&iquest;Alcanzan las materias primas para todo lo programado? &middot; solo lectura &mdash; no cambia ninguna programaci&oacute;n</div>
<div>Horizonte:
  <select id="dias" onchange="cargar()">
    <option value="15">15 d&iacute;as</option>
    <option value="30" selected>30 d&iacute;as</option>
    <option value="60">60 d&iacute;as</option>
    <option value="90">90 d&iacute;as</option>
  </select>
</div>
<div id="err"></div>
<div class="cards" id="cards"></div>
<div class="sec">Producciones programadas</div>
<table id="tprod"><thead><tr><th>Producto</th><th>Fecha</th><th>Cantidad</th><th>Estado</th><th>Falta</th></tr></thead><tbody></tbody></table>
<div class="sec">Compra consolidada &mdash; qu&eacute; comprar para que el plan entero sea ejecutable</div>
<table id="tcompra"><thead><tr><th>Material</th><th>C&oacute;digo</th><th>Faltante</th></tr></thead><tbody></tbody></table>
<script>
async function cargar(){
  var dias=document.getElementById('dias').value;
  document.getElementById('err').textContent='';
  try{
    var r=await fetch('/api/plan/factibilidad?dias='+dias);
    if(!r.ok){document.getElementById('err').textContent='Error '+r.status;return;}
    render(await r.json());
  }catch(e){document.getElementById('err').textContent='Error: '+e;}
}
function render(d){
  var s=d.resumen||{};
  document.getElementById('cards').innerHTML=
    card(s.total,'producciones','gris')+
    card(s.factibles,'factibles','verde')+
    card(s.bloqueadas,'bloqueadas','rojo')+
    card(s.mps_a_comprar,'MP a comprar','ama')+
    (s.sin_formula?card(s.sin_formula,'sin formula','gris'):'');
  var tb=document.querySelector('#tprod tbody');
  tb.innerHTML=(d.producciones||[]).map(function(p){
    var pill=p.sin_formula?'<span class="pill sf">sin formula</span>':
      (p.factible?'<span class="pill ok">factible</span>':'<span class="pill bloq">bloqueada</span>');
    var falta=(p.mps_faltantes||[]).map(function(m){
      return esc(m.material_nombre)+' (falta '+fmt(m.faltante_g)+' g)';}).join('<br>');
    return '<tr><td>'+esc(p.producto)+'</td><td>'+esc(p.fecha)+'</td><td>'+
      (p.cantidad_kg||0)+' kg</td><td>'+pill+'</td><td class="falta">'+falta+'</td></tr>';
  }).join('')||'<tr><td colspan="5" class="gris">No hay producciones programadas en el horizonte</td></tr>';
  var tc=document.querySelector('#tcompra tbody');
  tc.innerHTML=(d.compra_consolidada||[]).map(function(m){
    return '<tr><td>'+esc(m.material_nombre)+'</td><td>'+esc(m.material_id)+
      '</td><td class="falta">'+fmt(m.faltante_g)+' g ('+m.faltante_kg+' kg)</td></tr>';
  }).join('')||'<tr><td colspan="3" class="verde">Nada que comprar &mdash; el plan es ejecutable</td></tr>';
}
function card(n,l,cls){return '<div class="card"><div class="n '+cls+'">'+(n||0)+'</div><div class="l">'+l+'</div></div>';}
function fmt(n){return (n||0).toLocaleString('es-CO');}
function esc(s){var e=document.createElement('div');e.textContent=s==null?'':s;return e.innerHTML;}
cargar();
</script></body></html>
"""


@bp.route("/admin/factibilidad-plan", methods=["GET"])
def plan_factibilidad_page():
    """Página · análisis de factibilidad del plan de producción (solo lectura)."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/factibilidad-plan")
    from flask import Response
    return Response(_FACTIBILIDAD_PLAN_HTML, mimetype="text/html")


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

    # Validar reglas operativas · Sebastián 14-may-2026 (auditoría W4):
    # - No fin de semana ni festivo (skip_validacion_dia override)
    # - Lotes grandes >50kg ocupan el día solos
    # - Complejos (Vit C / Triactive) solo Lun o Mié
    # - Max 2 producciones por día
    skip_val = bool(body.get("skip_validacion_dia"))
    if not skip_val:
        from datetime import date as _date
        try:
            f_obj = _date.fromisoformat(fecha)
        except ValueError:
            return jsonify({"error": "fecha inválida"}), 400
        if f_obj.weekday() not in DIAS_HABILES:
            return jsonify({
                "error": f"{fecha} es fin de semana · usá skip_validacion_dia=true para forzar",
            }), 422
        if es_festivo_colombia(f_obj):
            return jsonify({
                "error": f"{fecha} es festivo colombiano · usá skip_validacion_dia=true para forzar",
            }), 422
        if _es_producto_complejo(producto) and f_obj.weekday() not in {0, 2}:
            return jsonify({
                "error": f"{producto} es complejo · solo Lun/Mié · usá skip_validacion_dia=true para forzar",
            }), 422
        # Capacidad del día
        rows_dia = cur.execute(
            """SELECT pp.id, COALESCE(pp.cantidad_kg, fh.lote_size_kg, 0)
               FROM produccion_programada pp
               LEFT JOIN formula_headers fh
                 ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
               WHERE date(pp.fecha_programada) = ?
                 AND pp.estado IN ('pendiente','programado','en_curso','esperando_recurso')""",
            (fecha,),
        ).fetchall()
        kgs_dia = [float(r[1] or 0) for r in rows_dia]
        ya_grande = any(k > LOTE_GRANDE_KG for k in kgs_dia)
        es_grande_nuevo = kg > LOTE_GRANDE_KG
        if es_grande_nuevo and len(rows_dia) > 0:
            return jsonify({"error": f"{fecha} ocupado · este lote grande necesita el día solo"}), 422
        if not es_grande_nuevo and ya_grande:
            return jsonify({"error": f"{fecha} ya tiene un lote grande · no se pueden agregar más"}), 422
        if not es_grande_nuevo and len(rows_dia) >= MAX_PRODUCCIONES_POR_DIA:
            return jsonify({"error": f"{fecha} ya tiene {len(rows_dia)} producciones (max {MAX_PRODUCCIONES_POR_DIA})"}), 422

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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
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
           -- FIX 30-may-2026 · el cruce era CIEGO: contaba solo 'calendar'/'manual'
           -- (legacy Google Cal) y NO los orígenes nativos EOS (Fijo eos_plan/b2b/
           -- retroactivo + Sugeridas eos_canonico/auto_plan/sugerido) → marcaba como
           -- "URGENTE_SIN_AGENDAR" lo que SÍ estaba programado. Google Cal fuera ·
           -- todo autónomo en EOS. (n_calendar_legacy ~L11287 y cancelables ~L12804
           --  SÍ deben seguir solo calendar/manual a propósito · NO tocar.)
           WHERE origen IN ('eos_plan','eos_b2b','eos_retroactivo',
                            'eos_canonico','auto_plan','sugerido',
                            'calendar','manual')
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
    # - fecha_producir_sugerida = agotamiento - BUFFER_REORDEN_DIAS (25) días
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
                fecha_producir_sugerida = (hoy + _td(days=max(0, int(dias_hasta_agotamiento) - BUFFER_REORDEN_DIAS))).isoformat()
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
           WHERE origen IN ('eos_plan','eos_b2b','eos_retroactivo',
                            'eos_canonico','auto_plan','sugerido',
                            'calendar','manual')
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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
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
  <h1>📊 Comparar Calendario EOS vs Necesidades reales</h1>
  <div class="muted">Análisis read-only · cruza lo programado en EOS (Fijo + Sugeridas, todos los orígenes) contra lo que el sistema dice que necesitás producir (basado en Shopify ventas + stock actual). NO modifica nada.</div>
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
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad
                                    WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad
                                    ELSE 0 END), 0)
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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
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
                  COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad
                                    WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad
                                    ELSE 0 END), 0)
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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
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


@bp.route("/admin/configurar-canonicos", methods=["GET"])
def configurar_canonicos_page():
    """Página única editable · todos los productos · kg, ml, frecuencia."""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/configurar-canonicos")
    from flask import Response
    return Response(_CONFIG_CANONICOS_HTML, mimetype="text/html")


@bp.route("/api/plan/configurar-canonicos", methods=["GET", "POST"])
def configurar_canonicos_api():
    """GET: lista de productos con datos calculados + valores actuales.
    POST: persiste cambios masivos en producto_canonico_config.
    """
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        items = body.get("items") or []
        if not isinstance(items, list):
            return jsonify({"error": "items debe ser lista"}), 400
        n_saved = 0
        for it in items:
            prod = (it.get("producto") or "").strip()
            if not prod:
                continue
            try:
                kg = float(it.get("kg_por_lote") or 0)
                ml = int(it.get("ml_unidad") or 30)
                freq = int(it.get("frecuencia_dias") or 0)
            except (ValueError, TypeError):
                continue
            notas = (it.get("notas") or "").strip()
            activo = 1 if it.get("activo", True) else 0
            c.execute(
                f"""INSERT INTO producto_canonico_config
                    (producto_nombre, kg_por_lote, ml_unidad, frecuencia_dias,
                     activo, actualizado_at, actualizado_por, notas)
                    VALUES (?,?,?,?,?,{SQLITE_NOW_COL},?,?)
                    ON CONFLICT(producto_nombre) DO UPDATE SET
                      kg_por_lote = excluded.kg_por_lote,
                      ml_unidad = excluded.ml_unidad,
                      frecuencia_dias = excluded.frecuencia_dias,
                      activo = excluded.activo,
                      actualizado_at = {SQLITE_NOW_COL},
                      actualizado_por = excluded.actualizado_por,
                      notas = excluded.notas""",
                (prod, kg, ml, freq, activo, user, notas),
            )
            n_saved += 1
        conn.commit()
        audit_log(c, usuario=user, accion="CONFIGURAR_CANONICOS",
                  tabla="producto_canonico_config", registro_id=None,
                  antes={"n_items": len(items)},
                  despues={"n_saved": n_saved})
        conn.commit()
        return jsonify({"ok": True, "saved": n_saved})

    # GET · construir lista
    # 1) Productos activos en formula_headers
    productos_fh = {}
    for r in c.execute(
        """SELECT producto_nombre, COALESCE(lote_size_kg, 0)
           FROM formula_headers WHERE COALESCE(activo, 1) = 1
           ORDER BY producto_nombre""",
    ).fetchall():
        productos_fh[r[0]] = float(r[1] or 0)

    # 2) Config existente
    config_existente = {}
    for r in c.execute(
        """SELECT producto_nombre, kg_por_lote, ml_unidad, frecuencia_dias,
                  activo, actualizado_at, actualizado_por, notas
           FROM producto_canonico_config""",
    ).fetchall():
        config_existente[r[0]] = {
            "kg_por_lote": float(r[1] or 0),
            "ml_unidad": int(r[2] or 30),
            "frecuencia_dias": int(r[3] or 0),
            "activo": bool(r[4]),
            "actualizado_at": r[5],
            "actualizado_por": r[6],
            "notas": r[7] or "",
        }

    # 3) Necesidades para cálculo Shopify
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)
    nec_map = {n["producto_nombre"]: n for n in necesidades}

    # 4) Pedidos B2B
    b2b_por_producto = {}
    for r in c.execute(
        """SELECT producto_nombre,
                  SUM(cantidad_uds * COALESCE(ml_unidad, 30)) / 1000.0 AS kg_total,
                  COUNT(*) AS n_pedidos
           FROM pedidos_b2b
           WHERE estado NOT IN ('despachado','cancelado')
           GROUP BY producto_nombre""",
    ).fetchall():
        b2b_por_producto[r[0]] = {
            "kg_pendiente": round(float(r[1] or 0), 2),
            "n_pedidos": int(r[2] or 0),
        }

    # 5) Histórico
    historico_por_prod = {}
    for r in c.execute(
        """SELECT producto, COUNT(*),
                  AVG(COALESCE(kg_real, cantidad_kg, 0)),
                  MAX(fin_real_at)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= date('now','-5 hours','-180 day')
             AND COALESCE(kg_real, cantidad_kg, 0) > 0
           GROUP BY producto""",
    ).fetchall():
        historico_por_prod[r[0]] = {
            "n_producciones": int(r[1] or 0),
            "kg_promedio": round(float(r[2] or 0), 1),
            "ultima_fecha": (r[3] or "")[:10] if r[3] else None,
        }

    items = []
    for prod, lote_excel in productos_fh.items():
        nec = nec_map.get(prod, {})
        b2b = b2b_por_producto.get(prod, {})
        hist = historico_por_prod.get(prod, {})
        cfg = config_existente.get(prod, {})

        vel_uds_dia = nec.get("velocidad_uds_dia", 0) or 0
        ml_actual = cfg.get("ml_unidad") or nec.get("ml_unidad") or 30
        kg_mes_shopify = round((vel_uds_dia * 30 * ml_actual) / 1000.0, 2)
        kg_mes_b2b = round((b2b.get("kg_pendiente", 0)) / 3.0, 2)
        kg_mes_total = round(kg_mes_shopify + kg_mes_b2b, 2)

        # Frecuencia sugerida
        kg_lote = cfg.get("kg_por_lote") or hist.get("kg_promedio") or lote_excel
        if kg_mes_total > 0.001 and kg_lote > 0:
            dias_dura = (kg_lote / kg_mes_total) * 30
            freq_sugerida = max(int(dias_dura - 20), 15)
        else:
            freq_sugerida = 0

        items.append({
            "producto": prod,
            "lote_excel_kg": lote_excel,
            "kg_lote_actual": cfg.get("kg_por_lote", 0) or 0,
            "ml_actual": ml_actual,
            "frecuencia_actual": cfg.get("frecuencia_dias", 0) or 0,
            "activo": cfg.get("activo", True) if cfg else True,
            "notas": cfg.get("notas", ""),
            "actualizado_at": cfg.get("actualizado_at"),
            "actualizado_por": cfg.get("actualizado_por"),
            "kg_mes_shopify": kg_mes_shopify,
            "kg_mes_b2b": kg_mes_b2b,
            "kg_mes_total": kg_mes_total,
            "frecuencia_sugerida": freq_sugerida,
            "vel_uds_dia": round(vel_uds_dia, 2),
            "stock_kg": nec.get("stock_kg_total", 0),
            "dias_cobertura": nec.get("dias_cobertura"),
            "urgencia": nec.get("urgencia", "SIN_VENTAS"),
            "histor_n": hist.get("n_producciones", 0),
            "histor_kg_prom": hist.get("kg_promedio", 0),
            "histor_ultima": hist.get("ultima_fecha"),
            "b2b_n_pedidos": b2b.get("n_pedidos", 0),
            "b2b_kg_pendiente": b2b.get("kg_pendiente", 0),
        })

    return jsonify({
        "items": items,
        "n": len(items),
    })


@bp.route("/admin/calendario-simple", methods=["GET"])
def calendario_simple_page():
    """Calendario grid server-side · sin JS · render directo desde BD.
    Sebastián 14-may-2026: el calendario JS oculta lotes · vista alternativa.
    Query: ?mes=YYYY-MM (default = mes actual)
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/calendario-simple")
    from datetime import date as _date, timedelta as _td
    from flask import Response
    import html as _h

    mes_param = (request.args.get("mes") or "").strip()
    hoy = _hoy_colombia()
    try:
        if mes_param:
            year, mm = mes_param.split("-")
            ref = _date(int(year), int(mm), 1)
        else:
            ref = _date(hoy.year, hoy.month, 1)
    except Exception:
        ref = _date(hoy.year, hoy.month, 1)

    # Mes anterior y siguiente
    if ref.month == 1:
        prev_m = _date(ref.year - 1, 12, 1)
    else:
        prev_m = _date(ref.year, ref.month - 1, 1)
    if ref.month == 12:
        next_m = _date(ref.year + 1, 1, 1)
    else:
        next_m = _date(ref.year, ref.month + 1, 1)

    # Lotes activos del mes
    inicio_mes = ref
    if ref.month == 12:
        fin_mes = _date(ref.year + 1, 1, 1) - _td(days=1)
    else:
        fin_mes = _date(ref.year, ref.month + 1, 1) - _td(days=1)

    # Lunes de la primera semana
    offset_lun = inicio_mes.weekday()
    inicio_grid = inicio_mes - _td(days=offset_lun)
    # 6 semanas
    fin_grid = inicio_grid + _td(days=42)

    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        """SELECT producto, fecha_programada, COALESCE(cantidad_kg, 0),
                  estado, origen, id
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','esperando_recurso','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= ?
             AND date(fecha_programada) <= ?
           ORDER BY fecha_programada""",
        (inicio_grid.isoformat(), fin_grid.isoformat()),
    ).fetchall()
    por_fecha = {}
    for r in rows:
        f = (r[1] or "")[:10]
        por_fecha.setdefault(f, []).append({
            "producto": r[0], "kg": float(r[2] or 0),
            "estado": r[3], "origen": r[4], "id": r[5],
        })

    # Festivos del rango
    festivos = set()
    for off in range(45):
        d = inicio_grid + _td(days=off)
        if es_festivo_colombia(d):
            festivos.add(d.isoformat())

    MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    h = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Calendario simple · EOS</title>
<style>
body{font-family:-apple-system,sans-serif;background:#f8fafc;margin:0;padding:18px;color:#1e293b}
.wrap{max-width:1500px;margin:0 auto}
h1{color:#0f766e;margin:0}
.bar{display:flex;justify-content:space-between;align-items:center;background:white;padding:14px;border-radius:10px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.bar a, .bar .lbl{font-size:14px;font-weight:700;color:#475569;text-decoration:none;padding:8px 14px;background:#f1f5f9;border-radius:6px}
.bar a:hover{background:#e2e8f0}
.lbl{font-size:18px !important;color:#0f766e !important;background:transparent !important}
.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;background:white;padding:8px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.head{background:#f1f5f9;padding:8px;text-align:center;font-weight:800;color:#475569;font-size:12px;border-radius:5px}
.day{background:white;border:1px solid #e2e8f0;border-radius:6px;padding:6px;min-height:110px;font-size:11px}
.day.fest{background:#fef2f2;border-color:#fca5a5}
.day.fdesem{background:#f8fafc;opacity:.6}
.day.hoy{border:2px solid #0f766e;background:#f0fdfa}
.day.otro{opacity:.35}
.dnum{font-weight:800;color:#1e293b;margin-bottom:4px;display:flex;justify-content:space-between}
.fmark{background:#fecaca;color:#7f1d1d;padding:1px 4px;border-radius:3px;font-size:9px;font-weight:700}
.lote{background:#e0e7ff;color:#3730a3;padding:3px 5px;border-radius:4px;margin-bottom:3px;border-left:3px solid #6366f1;font-weight:600;line-height:1.2}
</style></head><body><div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700">&larr; Volver</a>
<h1>📅 Calendario simple · vista directa desde BD</h1>
"""
    h += f'<div class="bar">'
    h += f'<div><a href="?mes={prev_m.isoformat()[:7]}">← Anterior</a>'
    h += f'<a href="?mes={hoy.isoformat()[:7]}" style="margin-left:6px">Hoy</a></div>'
    h += f'<div class="lbl">{MESES_ES[ref.month - 1]} {ref.year}</div>'
    h += f'<div><a href="?mes={next_m.isoformat()[:7]}">Siguiente →</a></div>'
    h += '</div>'

    h += '<div class="grid">'
    for d in DIAS_ES:
        h += f'<div class="head">{d}</div>'

    for sem in range(6):
        for d in range(7):
            fecha = inicio_grid + _td(days=sem * 7 + d)
            f_iso = fecha.isoformat()
            es_finde = d >= 5
            es_fest = f_iso in festivos
            es_hoy = fecha == hoy
            es_otro_mes = fecha.month != ref.month
            lotes = por_fecha.get(f_iso, [])

            cls = "day"
            if es_hoy:
                cls += " hoy"
            if es_fest:
                cls += " fest"
            if es_finde and not es_fest:
                cls += " fdesem"
            if es_otro_mes:
                cls += " otro"

            h += f'<div class="{cls}">'
            h += f'<div class="dnum"><span>{fecha.day}</span>'
            if es_fest:
                h += '<span class="fmark">FEST</span>'
            h += '</div>'
            for lt in lotes:
                prod_corto = _h.escape(lt["producto"])[:24]
                h += f'<div class="lote" title="{_h.escape(lt["producto"])} · {lt["kg"]:.0f}kg · {lt["estado"]}">'
                h += f'{prod_corto}<br><span style="opacity:.7">{lt["kg"]:.0f}kg</span></div>'
            h += '</div>'

    h += '</div></div></body></html>'
    return Response(h, mimetype="text/html")


@bp.route("/admin/plan-simple", methods=["GET"])
def plan_simple_page():
    """Vista simple server-side · solo lee BD · renderiza HTML directo.
    Sebastián 14-may-2026: "sigue saliendo solo 3 productos" en
    calendario JS · vista alternativa sin lógica JS compleja.
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/plan-simple")
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        """SELECT producto, fecha_programada, COALESCE(cantidad_kg,0),
                  estado, origen
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','esperando_recurso','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
           ORDER BY fecha_programada, producto""",
    ).fetchall()

    # Agrupar por mes
    from collections import defaultdict
    por_mes = defaultdict(list)
    for r in rows:
        fecha = (r[1] or "")[:10]
        mes = fecha[:7]  # YYYY-MM
        por_mes[mes].append({
            "producto": r[0], "fecha": fecha, "kg": float(r[2] or 0),
            "estado": r[3], "origen": r[4],
        })

    MESES_ES = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
    }

    from flask import Response
    import html
    html_str = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Plan simple · EOS</title>
<style>
body{font-family:-apple-system,sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1100px;margin:0 auto}
h1{color:#0f766e;margin:0 0 6px}
.mes{background:white;border-radius:10px;padding:14px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.mes h2{margin:0 0 10px;color:#475569;font-size:16px;padding-bottom:6px;border-bottom:2px solid #e2e8f0}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:6px 8px;text-align:left}
tr{border-bottom:1px solid #f1f5f9}
.kg{text-align:right;font-weight:700;color:#0f766e;font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700}
.tag-eos_canonico{background:#e0e7ff;color:#3730a3}
.tag-eos_plan{background:#dcfce7;color:#166534}
.tag-calendar{background:#fef9c3;color:#854d0e}
.dia{color:#64748b;font-size:11px}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;margin-right:8px;text-align:center;min-width:90px}
.kpi-val{font-size:22px;font-weight:800;color:#0f766e}
.kpi-lbl{font-size:10px;color:#64748b;text-transform:uppercase}
</style></head><body><div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700">&larr; Volver</a>
<h1>📋 Plan simple · vista directa BD</h1>
<div style="color:#64748b;font-size:12px;margin-bottom:14px">Server-side · sin JavaScript · si acá los ves todos pero en el calendario no, el bug es del JS visual.</div>
"""
    total_lotes = sum(len(v) for v in por_mes.values())
    total_kg = sum(it["kg"] for v in por_mes.values() for it in v)
    productos_unicos = len({it["producto"] for v in por_mes.values() for it in v})
    html_str += f'<div style="margin-bottom:14px">'
    html_str += f'<span class="kpi"><div class="kpi-lbl">Lotes</div><div class="kpi-val">{total_lotes}</div></span>'
    html_str += f'<span class="kpi"><div class="kpi-lbl">Productos</div><div class="kpi-val">{productos_unicos}</div></span>'
    html_str += f'<span class="kpi"><div class="kpi-lbl">Total kg</div><div class="kpi-val">{total_kg:.0f}</div></span>'
    html_str += '</div>'

    DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    from datetime import date as _date

    for mes in sorted(por_mes.keys()):
        year, mm = mes.split("-")
        nombre_mes = f"{MESES_ES.get(mm, mm)} {year}"
        lotes = por_mes[mes]
        html_str += f'<div class="mes"><h2>{nombre_mes} · {len(lotes)} lotes · {sum(l["kg"] for l in lotes):.0f} kg</h2>'
        html_str += '<table><tr><th>Día</th><th>Fecha</th><th>Producto</th><th class="kg">kg</th><th>Origen</th></tr>'
        for lt in lotes:
            try:
                dt = _date.fromisoformat(lt["fecha"])
                dia = DIAS_ES[dt.weekday()]
            except Exception:
                dia = "?"
            tag_class = f"tag tag-{lt['origen']}" if lt["origen"] else "tag"
            html_str += f'<tr><td class="dia">{dia}</td><td>{html.escape(lt["fecha"])}</td><td><strong>{html.escape(lt["producto"])}</strong></td><td class="kg">{lt["kg"]:.0f}</td><td><span class="{tag_class}">{html.escape(lt["origen"] or "—")}</span></td></tr>'
        html_str += '</table></div>'

    html_str += '</div></body></html>'
    return Response(html_str, mimetype="text/html")


@bp.route("/api/plan/listar-canonicos", methods=["GET"])
def listar_canonicos():
    """Lista TODOS los eos_canonico activos · debug rápido para Sebastián.
    Devuelve agrupado por producto con conteo + primer/último lote.
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        """SELECT producto, COUNT(*),
                  MIN(fecha_programada), MAX(fecha_programada),
                  GROUP_CONCAT(fecha_programada, '|')
           FROM produccion_programada
           WHERE origen = 'eos_canonico'
             AND estado IN ('pendiente','programado','esperando_recurso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
           GROUP BY producto
           ORDER BY producto""",
    ).fetchall()
    out = [{
        "producto": r[0],
        "n_lotes": int(r[1] or 0),
        "primera_fecha": r[2],
        "ultima_fecha": r[3],
        "todas_fechas": (r[4] or "").split("|"),
    } for r in rows]
    return jsonify({
        "n_productos": len(out),
        "total_lotes": sum(x["n_lotes"] for x in out),
        "productos": out,
    })


@bp.route("/api/plan/health-canonicos", methods=["GET"])
def health_canonicos():
    """Diagnóstico · cuenta lotes activos por origen + última mig aplicada.
    Sebastián 14-may-2026: "solo me salen 2" · ver si mig 136 corrió.
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()

    # Última mig aplicada
    try:
        ultima_mig = c.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
        ultima = int(ultima_mig[0] or 0) if ultima_mig else 0
    except Exception:
        ultima = -1

    # Conteos por origen · solo activos futuros
    por_origen = {}
    for r in c.execute(
        """SELECT origen, COUNT(*), MIN(fecha_programada), MAX(fecha_programada)
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','esperando_recurso','en_curso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
           GROUP BY origen""",
    ).fetchall():
        por_origen[r[0] or "(NULL)"] = {
            "n_lotes": int(r[1] or 0),
            "primer_fecha": r[2],
            "ultima_fecha": r[3],
        }

    # Conteo total · ver si mig 136 se aplicó
    total_eos_canonico = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE origen = 'eos_canonico' AND estado = 'programado'
             AND fin_real_at IS NULL"""
    ).fetchone()[0]

    # Buscar marker mig 136 en observaciones (señal de que corrió)
    mig136_evidence = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE observaciones LIKE '%Plan-limpio mig 136%'"""
    ).fetchone()[0]

    mig136_cancelado = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE observaciones LIKE '%CANCELADO_PLAN_LIMPIO_MIG136%'"""
    ).fetchone()[0]

    # Sebastián 14-may-2026 ronda 2: "solo sale el gel hidratante"
    # Agregar info de mig 137 (plan denso 96 lotes)
    mig137_evidence = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE observaciones LIKE '%Plan-denso mig137%'"""
    ).fetchone()[0]
    mig137_cancelado = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE observaciones LIKE '%CANCELADO_PLAN_DENSO_MIG137%'"""
    ).fetchone()[0]
    # Replica EXACTA de la consulta del listado que usa el calendario
    listado_rows = c.execute(
        """SELECT pp.producto, COUNT(*) as n
             FROM produccion_programada pp
             WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
               AND pp.fecha_programada >= date('now', '-5 hours', '-7 day')
             GROUP BY pp.producto
             ORDER BY pp.producto""",
    ).fetchall()
    productos_listado = [{"producto": r[0], "n_lotes": int(r[1])} for r in listado_rows]
    total_listado = sum(p["n_lotes"] for p in productos_listado)

    return jsonify({
        "ultima_mig_aplicada": ultima,
        "mig_136_aplicada": mig136_evidence > 0,
        "mig_136_inserts_visible": mig136_evidence,
        "mig_136_cancelados_visible": mig136_cancelado,
        "mig_137_aplicada": mig137_evidence > 0,
        "mig_137_inserts_visible": mig137_evidence,
        "mig_137_cancelados_visible": mig137_cancelado,
        "esperado_post_mig_137": 96,
        "total_eos_canonico_activos": int(total_eos_canonico or 0),
        "por_origen_activos_futuros": por_origen,
        # Esto es lo MISMO que devuelve el listado al calendar visual
        "listado_calendar_replica": {
            "total_lotes": total_listado,
            "productos_unicos": len(productos_listado),
            "productos": productos_listado,
        },
    })


@bp.route("/api/plan/lotes-producto", methods=["GET"])
def lotes_producto_diag():
    """Diagnóstico · lista TODOS los lotes activos de un producto (con
    matching normalizado). Útil cuando hay duplicados visibles.

    Sebastián 14-may-2026: "sigue apareciendo Limpiador facial H
    viernes 22 y lunes 25". Endpoint para ver TODOS los lotes que
    pueden estar generando ese duplicado.

    Query: ?q=limpiador hidratante (substring fuzzy en producto)
    """
    err = _require_login()
    if err:
        return err
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "pasá ?q=nombre_producto"}), 400

    import unicodedata
    def _norm(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().upper())
        return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

    q_norm = _norm(q)
    conn = get_db()
    c = conn.cursor()

    rows = c.execute(
        """SELECT id, producto, fecha_programada, origen, estado,
                  cantidad_kg, fin_real_at, inicio_real_at,
                  motivo_pausa, observaciones
           FROM produccion_programada
           ORDER BY fecha_programada DESC""",
    ).fetchall()

    matched = []
    for r in rows:
        if q_norm in _norm(r[1]):
            matched.append({
                "id": r[0], "producto": r[1],
                "fecha": (r[2] or "")[:10],
                "origen": r[3], "estado": r[4],
                "kg": float(r[5] or 0),
                "fin_real_at": r[6],
                "inicio_real_at": r[7],
                "motivo_pausa": r[8],
                "obs_preview": (r[9] or "")[:120],
                "es_activo": (r[4] in ('pendiente','programado','en_curso','esperando_recurso')
                              and not r[6] and not r[7]),
            })

    # Agrupar por nombre exacto · para ver variantes
    variantes = {}
    for m in matched:
        variantes.setdefault(m["producto"], 0)
        variantes[m["producto"]] += 1

    return jsonify({
        "query": q,
        "n_total": len(matched),
        "n_activos": sum(1 for m in matched if m["es_activo"]),
        "variantes_nombre": variantes,
        "lotes": matched[:100],
    })


@bp.route("/api/plan/limpiar-duplicados", methods=["POST"])
def limpiar_duplicados():
    """Detecta y cancela duplicados activos · mismo producto + fecha cercana.

    Sebastián 14-may-2026: "limpiador hidratante dos veces · calendario
    tiene cosas viejas y mezcla google calendar con propuesta nueva".

    Regla: si hay 2+ lotes activos del MISMO producto en ventana ±21 días,
    conservar SOLO el más nuevo por origen-prioridad:
    1. eos_plan (manual del usuario · prioridad máxima)
    2. eos_canonico (algoritmo)
    3. calendar (legacy)
    4. manual (legacy)

    NUNCA toca lotes con fin_real_at, inicio_real_at, o estado completado.
    Audit log LIMPIAR_DUPLICADOS.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    conn = get_db()
    c = conn.cursor()

    # Prioridad por origen · 0 = mejor (no se cancela en dedup)
    # Sebastián 19-may-2026: orígenes FIJOS (lo que el usuario fijó / B2B
    # / históricos) tienen máxima prioridad y nunca son los cancelados.
    PRIORIDAD = {
        'eos_plan': 0,
        'eos_b2b': 0,
        'eos_retroactivo': 0,
        'eos_canonico': 1,
        'calendar': 2,
        'manual': 3,
    }

    # 1) Listar todos los lotes activos por producto
    rows = c.execute(
        """SELECT id, producto, fecha_programada, origen, cantidad_kg
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','en_curso','esperando_recurso')
             AND fin_real_at IS NULL
             AND inicio_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
           ORDER BY producto, fecha_programada""",
    ).fetchall()

    # 2) Agrupar por producto NORMALIZADO · Sebastián 14-may-2026:
    # "sigue apareciendo Limpiador facial H viernes 22 y lunes 25". Causa:
    # produccion_programada tenía variantes del mismo producto con
    # nombres ligeramente distintos (Calendar legacy "Limpiador Hidratante"
    # vs canónico "LIMPIADOR FACIAL HIDRATANTE"). El detector previo
    # agrupaba por nombre exacto · ahora normaliza upper+trim+sin acentos.
    import unicodedata
    def _norm_prod(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().upper())
        return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').replace('  ', ' ')

    from datetime import date as _date
    por_producto = {}
    for r in rows:
        key_norm = _norm_prod(r[1])
        por_producto.setdefault(key_norm, []).append({
            "id": r[0], "producto_real": r[1],
            "fecha": r[2][:10] if r[2] else None,
            "origen": r[3] or "manual", "kg": float(r[4] or 0),
        })

    cancelar_ids = []
    duplicados_detectados = []
    for prod, lotes in por_producto.items():
        if len(lotes) < 2:
            continue
        # Para cada par, ver si están a <21d
        marcados_cancelados = set()
        for i, la in enumerate(lotes):
            if la["id"] in marcados_cancelados or la["fecha"] is None:
                continue
            for j, lb in enumerate(lotes[i + 1:], start=i + 1):
                if lb["id"] in marcados_cancelados or lb["fecha"] is None:
                    continue
                try:
                    fa = _date.fromisoformat(la["fecha"])
                    fb = _date.fromisoformat(lb["fecha"])
                    if abs((fb - fa).days) < 21:
                        # Conflicto · cancelar el de menor prioridad
                        pa = PRIORIDAD.get(la["origen"], 9)
                        pb = PRIORIDAD.get(lb["origen"], 9)
                        # Sebastián 25-may-2026 PM · audit P0 · si AMBOS son
                        # Fijo (eos_plan/eos_b2b/eos_retroactivo · prio 0),
                        # NO tocar nada · el usuario debe resolver el
                        # duplicado manualmente. Violar Fijo era el bug raíz
                        # del 19-may-2026 que perdió producción.
                        if pa == 0 and pb == 0:
                            duplicados_detectados.append({
                                'producto': la.get('producto_real') or prod,
                                'aviso': 'AMBOS Fijos · no cancelado automáticamente',
                                'lote_a': {'id': la['id'], 'fecha': la['fecha'], 'origen': la['origen']},
                                'lote_b': {'id': lb['id'], 'fecha': lb['fecha'], 'origen': lb['origen']},
                            })
                            continue
                        if pa <= pb:
                            cancelar_ids.append(lb["id"])
                            marcados_cancelados.add(lb["id"])
                            duplicados_detectados.append({
                                "producto": la.get("producto_real") or prod,
                                "conserva": {"id": la["id"], "fecha": la["fecha"], "origen": la["origen"], "nombre": la.get("producto_real")},
                                "cancela": {"id": lb["id"], "fecha": lb["fecha"], "origen": lb["origen"], "nombre": lb.get("producto_real")},
                            })
                        else:
                            cancelar_ids.append(la["id"])
                            marcados_cancelados.add(la["id"])
                            duplicados_detectados.append({
                                "producto": lb.get("producto_real") or prod,
                                "conserva": {"id": lb["id"], "fecha": lb["fecha"], "origen": lb["origen"], "nombre": lb.get("producto_real")},
                                "cancela": {"id": la["id"], "fecha": la["fecha"], "origen": la["origen"], "nombre": la.get("producto_real")},
                            })
                            break  # la ya no existe, sigue con próximo i
                except Exception:
                    pass

    # 3) Aplicar cancelaciones
    # Sebastián 25-may-2026 PM · audit P0 · defense in depth · UPDATE excluye
    # Fijo aunque el algoritmo del loop ya filtra · doble salvaguarda.
    n_canceladas = 0
    if cancelar_ids:
        placeholders = ",".join(["?"] * len(cancelar_ids))
        n_canceladas = c.execute(
            f"""UPDATE produccion_programada
                SET estado = 'cancelado',
                    observaciones = COALESCE(observaciones,'') ||
                      ' · CANCELADO_LIMPIAR_DUPLICADOS_' || {SQLITE_NOW_COL}
                WHERE id IN ({placeholders})
                  AND COALESCE(origen,'') NOT IN ('eos_plan','eos_b2b','eos_retroactivo')""",
            cancelar_ids,
        ).rowcount
    conn.commit()

    audit_log(c, usuario=user, accion="LIMPIAR_DUPLICADOS",
              tabla="produccion_programada", registro_id=None,
              antes={"detectados": len(duplicados_detectados)},
              despues={"canceladas": n_canceladas})
    conn.commit()

    return jsonify({
        "ok": True,
        "duplicados_detectados": len(duplicados_detectados),
        "canceladas": n_canceladas,
        "detalle": duplicados_detectados[:50],
        "metodologia": (
            "Detecta pares de lotes activos del mismo producto con fechas "
            "a ±21 días. Conserva el de mayor prioridad: eos_plan > "
            "eos_canonico > calendar > manual. Cancela el otro."
        ),
    })


@bp.route("/api/plan/generar-plan-perfecto", methods=["POST"])
def generar_plan_perfecto():
    """Genera el calendario PERFECTO · algoritmo determinista para
    reglas duras + IA opcional para reporte ejecutivo.

    Sebastián 14-may-2026: "4 primeros puntos nosotros, 2 últimos IA".

    Algoritmo determinista (puntos 1-4):
      1. Input: producto_canonico_config + histórico + ventas
      2. Ajuste por velocidad: si vel_reciente >30% baseline →
         reducir frecuencia (60d→45d, etc)
      3. Prioridad: complejos (Vit C/Triactive) > grandes (>50kg) > otros
      4. Reglas duras: L-V, skip festivos, max 2/día, grandes solos,
         complejos Lun/Mié, producir 20d antes agotamiento

    IA (puntos 5-6 · opcional):
      5. Reporte ejecutivo · qué se programó y por qué
      6. Análisis de conflictos · si hay productos sin slot

    Body: {usar_ia: bool (default true), horizonte_dias: int (default 365)}

    Returns:
      plan[]: lotes generados
      cancelados_viejos: N
      conflictos[]: productos sin slot disponible
      reporte_ia: texto con explicación (si usar_ia=true)
      stats_ajuste_velocidad: productos con frecuencia ajustada
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    usar_ia = bool(body.get("usar_ia", True))
    try:
        horizonte_dias = max(30, min(730, int(body.get("horizonte_dias") or 365)))
    except (ValueError, TypeError):
        horizonte_dias = 365

    conn = get_db()
    c = conn.cursor()
    from datetime import date as _date, timedelta as _td

    # ── PUNTO 1 · INPUT: producto_canonico_config ──
    rows_cfg = c.execute(
        """SELECT producto_nombre, kg_por_lote, ml_unidad, frecuencia_dias, notas
           FROM producto_canonico_config
           WHERE COALESCE(activo, 1) = 1
             AND kg_por_lote > 0
             AND frecuencia_dias > 0""",
    ).fetchall()
    if not rows_cfg:
        return jsonify({"error": "Sin config válida · llená /admin/configurar-canonicos primero"}), 400
    configs = [{
        "producto": r[0], "kg": float(r[1]), "ml": int(r[2] or 30),
        "freq_base": int(r[3]), "notas": r[4] or "",
    } for r in rows_cfg]

    # Última producción real por producto
    ultima_real = {}
    productos_lista = [c["producto"] for c in configs]
    placeholders = ",".join(["?"] * len(productos_lista))
    for r in c.execute(
        f"""SELECT producto, MAX(fin_real_at)
            FROM produccion_programada
            WHERE fin_real_at IS NOT NULL AND producto IN ({placeholders})
            GROUP BY producto""",
        productos_lista,
    ).fetchall():
        ultima_real[r[0]] = (r[1] or "")[:10]

    # ── PUNTO 2 · AJUSTE POR VELOCIDAD ──
    nec_baseline = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                          cob_alerta=25, cob_vigilar=45)
    nec_reciente = _calcular_animus_dtc(c, ventana=14, cob_critico=20,
                                          cob_alerta=25, cob_vigilar=45)
    bl_map = {n["producto_nombre"]: n.get("velocidad_kg_dia", 0) or 0
              for n in nec_baseline}
    rc_map = {n["producto_nombre"]: n.get("velocidad_kg_dia", 0) or 0
              for n in nec_reciente}

    ajustes_velocidad = []
    for cfg in configs:
        prod = cfg["producto"]
        vel_bl = bl_map.get(prod, 0)
        vel_rc = rc_map.get(prod, 0)
        cfg["vel_baseline_kg_dia"] = vel_bl
        cfg["vel_reciente_kg_dia"] = vel_rc
        freq_original = cfg["freq_base"]
        cfg["freq_final"] = freq_original  # default · sin ajuste
        if vel_bl > 0.01 and vel_rc > vel_bl * 1.30:
            # Velocidad aumentó >30% · reducir frecuencia proporcionalmente
            factor = vel_bl / vel_rc  # menor que 1
            nueva_freq = max(int(freq_original * factor), 14)
            cfg["freq_final"] = nueva_freq
            ajustes_velocidad.append({
                "producto": prod,
                "vel_baseline_kg_dia": round(vel_bl, 3),
                "vel_reciente_kg_dia": round(vel_rc, 3),
                "delta_pct": round((vel_rc - vel_bl) / vel_bl * 100, 1),
                "freq_original": freq_original,
                "freq_ajustada": nueva_freq,
            })

    # ── PUNTO 3 · PRIORIDAD: complejos > grandes > otros ──
    def _tier(cfg):
        if _es_producto_complejo(cfg["producto"]):
            return 0  # complejo · más restrictivo
        if cfg["kg"] > LOTE_GRANDE_KG:
            return 1  # grande
        return 2  # mediano/pequeño
    configs_ordenados = sorted(configs, key=lambda c: (_tier(c), c["freq_final"]))

    # ── PASO PREVIO · LIMPIEZA TOTAL · cancelar TODO lo viejo sin ejecutar ──
    # Sebastián 14-may-2026: "limpiador hidratante dos veces · siento que
    # el calendario tiene cosas viejas y mezcla". Antes solo cancelaba
    # eos_canonico, pero quedaban Calendar legacy + Manual de mig viejas.
    # Ahora cancela TODO con origen IN (eos_canonico, calendar, manual)
    # con fecha pendiente/programado sin ejecutar. NUNCA toca:
    # - eos_plan (lo que el usuario programó manualmente)
    # - eos_retroactivo (back-fills · historial)
    # - estados completado / en_curso / cancelado
    n_cancelados = c.execute(
        f"""UPDATE produccion_programada
            SET estado = 'cancelado',
                observaciones = COALESCE(observaciones,'') ||
                  ' · CANCELADO_PLAN_PERFECTO_' || {SQLITE_NOW_COL}
            WHERE origen IN ('eos_canonico','calendar','manual')
              AND estado IN ('pendiente','programado','esperando_recurso')
              AND fin_real_at IS NULL
              AND inicio_real_at IS NULL
              AND producto IN ({placeholders})""",
        productos_lista,
    ).rowcount

    # ── PUNTO 4 · REGLAS DURAS · generar lotes con _proxima_fecha_habil ──
    hoy = _hoy_colombia()
    horizon_end = hoy + _td(days=horizonte_dias)

    plan_lotes = []
    conflictos = []

    for cfg in configs_ordenados:
        prod = cfg["producto"]
        kg = cfg["kg"]
        freq = cfg["freq_final"]

        # Fecha base · Sebastián 14-may-2026: aplicar regla "20 días antes
        # de agotamiento" con velocidad real, comparada contra freq config.
        # Usamos el MÁS TEMPRANO de los dos.
        vel = cfg.get("vel_reciente_kg_dia", 0) or cfg.get("vel_baseline_kg_dia", 0)
        if prod in ultima_real:
            try:
                ult = _date.fromisoformat(ultima_real[prod])
                base_freq = ult + _td(days=freq)
                if vel > 0.001:
                    dias_dura = int(kg / vel)
                    base_20d = ult + _td(days=max(dias_dura - BUFFER_REORDEN_DIAS, 14))
                    base = min(base_freq, base_20d)
                else:
                    base = base_freq
            except Exception:
                base = hoy + _td(days=(7 - hoy.weekday()) % 7 or 7)
        else:
            base = hoy + _td(days=(7 - hoy.weekday()) % 7 or 7)

        # Generar slots
        cur = _proxima_fecha_habil(c, base, prefer_mwf=False,
                                    lote_kg=kg, producto_nombre=prod)
        if cur is None:
            conflictos.append({
                "producto": prod,
                "razon": "No se encontró ningún día hábil compatible en 400 días",
            })
            continue

        slot = 1
        lotes_de_este = []
        while cur and cur <= horizon_end and slot <= 30:  # safety cap
            try:
                cur_iter = c.execute(
                    f"""INSERT INTO produccion_programada
                        (producto, fecha_programada, cantidad_kg, estado, origen,
                         lotes, observaciones)
                        VALUES (?, ?, ?, 'programado', 'eos_canonico', 1, ?)""",
                    (prod, cur.isoformat(), kg,
                     f"Plan-perfecto · {kg}kg cada {freq}d · slot {slot}" +
                     (f" · ajustado por vel +{round((cfg['vel_reciente_kg_dia']-cfg['vel_baseline_kg_dia'])/max(cfg['vel_baseline_kg_dia'],0.001)*100)}%" if freq != cfg["freq_base"] else "")),
                )
                plan_lotes.append({
                    "producto": prod, "fecha": cur.isoformat(),
                    "kg": kg, "slot": slot,
                    "ajustado_velocidad": freq != cfg["freq_base"],
                })
                lotes_de_este.append(cur.isoformat())
                slot += 1
            except Exception as ex:
                conflictos.append({
                    "producto": prod, "slot": slot,
                    "razon": f"Error insert: {ex}",
                })
                break

            siguiente = _proxima_fecha_habil(c, cur + _td(days=freq),
                                              prefer_mwf=False,
                                              lote_kg=kg, producto_nombre=prod)
            if siguiente is None or siguiente <= cur:
                break
            cur = siguiente

    conn.commit()

    # ── PUNTOS 5-6 · IA · reporte ejecutivo ──
    reporte_ia = None
    ia_error = None
    if usar_ia and plan_lotes:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
        if not api_key:
            ia_error = "ANTHROPIC_API_KEY no configurada · reporte sin IA"
        else:
            import json as _json
            import urllib.request as _ureq
            # Resumen compacto para la IA
            contexto = {
                "productos_planificados": len(configs_ordenados),
                "total_lotes_generados": len(plan_lotes),
                "ajustes_por_velocidad": ajustes_velocidad,
                "conflictos": conflictos,
                "horizonte_dias": horizonte_dias,
                "fecha_inicio": hoy.isoformat(),
                "resumen_por_producto": [
                    {"producto": cfg["producto"], "kg_lote": cfg["kg"],
                     "freq_dias": cfg["freq_final"],
                     "n_lotes_generados": sum(1 for p in plan_lotes if p["producto"] == cfg["producto"]),
                     "ajustado": cfg["freq_final"] != cfg["freq_base"]}
                    for cfg in configs_ordenados
                ],
            }
            sys_prompt = (
                "Eres el COO de un laboratorio cosmético. Acabamos de "
                "generar el calendario de producción para 12 meses con "
                "un algoritmo determinista. Tu trabajo es escribir un "
                "REPORTE EJECUTIVO de 3 párrafos para el CEO (Sebastián):\n"
                "- Párrafo 1: Resumen general (N productos, N lotes, total kg).\n"
                "- Párrafo 2: Hallazgos importantes · ajustes por aumento "
                "de velocidad de ventas (qué productos y por qué).\n"
                "- Párrafo 3: Acciones recomendadas · si hay conflictos, "
                "qué hacer · si todo OK, qué monitorear.\n"
                "Máximo 250 palabras. Tono ejecutivo, directo, en español."
            )
            body_ia = _json.dumps({
                "model": "claude-sonnet-4-6",
                "max_tokens": 800,
                "system": sys_prompt,
                "messages": [{"role": "user", "content":
                              _json.dumps(contexto, ensure_ascii=False)[:6000]}],
            }).encode("utf-8")
            req = _ureq.Request(
                "https://api.anthropic.com/v1/messages",
                data=body_ia,
                headers={"x-api-key": api_key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                method="POST",
            )
            try:
                with _ureq.urlopen(req, timeout=60) as resp:
                    data = _json.loads(resp.read().decode("utf-8"))
                reporte_ia = data["content"][0]["text"]
            except Exception as ex:
                ia_error = f"Error IA: {ex}"

    audit_log(c, usuario=user, accion="GENERAR_PLAN_PERFECTO",
              tabla="produccion_programada", registro_id=None,
              antes={"cancelados": n_cancelados},
              despues={"generados": len(plan_lotes),
                       "conflictos": len(conflictos),
                       "ajustes_velocidad": len(ajustes_velocidad)})
    conn.commit()

    return jsonify({
        "ok": True,
        "n_productos_config": len(configs),
        "n_lotes_cancelados_viejos": n_cancelados,
        "n_lotes_generados_nuevos": len(plan_lotes),
        "n_conflictos": len(conflictos),
        "n_ajustes_velocidad": len(ajustes_velocidad),
        "ajustes_velocidad": ajustes_velocidad,
        "conflictos": conflictos,
        "reporte_ia": reporte_ia,
        "ia_error": ia_error,
        "horizonte_dias": horizonte_dias,
        "metodologia": {
            "punto_1": "Input · producto_canonico_config (algoritmo)",
            "punto_2": "Ajuste velocidad · si vel_reciente >30% baseline reducir freq (algoritmo)",
            "punto_3": "Prioridad · complejos > grandes > otros (algoritmo)",
            "punto_4": "Reglas duras · L-V, festivos, max 2/día, etc (algoritmo)",
            "punto_5": "Reporte ejecutivo · Claude Sonnet 4.6 (IA)",
            "punto_6": "Análisis conflictos · Claude Sonnet 4.6 (IA)",
        },
    })


@bp.route("/api/plan/alertas-ventas", methods=["GET"])
def alertas_ventas():
    """Detecta productos donde las ventas RECIENTES superan al baseline
    histórico · sugiere adelantar próximo canónico.

    Sebastián 14-may-2026: "ia para sugerir si se debe adelantar porque
    las ventas aumentaron".

    Lógica:
    1. Para cada producto activo:
       - vel_reciente = ventas últ 14 días / 14
       - vel_baseline = ventas últ 60 días / 60
       - delta_pct = (reciente - baseline) / baseline × 100
    2. Si delta_pct > 30% (configurable via ?umbral=30):
       - Calcular nueva cobertura con vel_reciente
       - Si próximo canónico cae DESPUÉS del agotamiento ajustado:
         sugerir adelantar X días
    3. Devolver lista ordenada por riesgo (cobertura ajustada ASC)
    """
    err = _require_login()
    if err:
        return err

    try:
        umbral_pct = max(10, min(200, int(request.args.get("umbral") or 30)))
    except ValueError:
        umbral_pct = 30

    conn = get_db()
    c = conn.cursor()
    from datetime import date as _date, timedelta as _td

    hoy = _hoy_colombia()

    # 1) Necesidades base (ventana 60d) · da velocidad baseline
    nec_baseline = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                          cob_alerta=25, cob_vigilar=45)
    # 2) Necesidades reciente (ventana 14d) · da velocidad reciente
    nec_reciente = _calcular_animus_dtc(c, ventana=14, cob_critico=20,
                                          cob_alerta=25, cob_vigilar=45)

    rec_map = {n["producto_nombre"]: n for n in nec_reciente}

    # 3) Para cada producto comparar
    alertas = []
    for n_bl in nec_baseline:
        prod = n_bl["producto_nombre"]
        n_rc = rec_map.get(prod, {})

        vel_baseline = n_bl.get("velocidad_kg_dia", 0) or 0
        vel_reciente = n_rc.get("velocidad_kg_dia", 0) or 0

        # Solo productos con baseline > 0 (con ventas históricas)
        if vel_baseline < 0.01:
            continue
        # Solo si velocidad reciente es significativa
        if vel_reciente < 0.01:
            continue

        delta_kg_dia = vel_reciente - vel_baseline
        delta_pct = (delta_kg_dia / vel_baseline) * 100.0

        # Solo alerta si supera umbral
        if delta_pct < umbral_pct:
            continue

        # Cobertura ajustada con vel_reciente
        stock_kg = n_bl.get("stock_kg_total", 0) or 0
        cob_baseline_dias = stock_kg / vel_baseline if vel_baseline > 0 else None
        cob_reciente_dias = stock_kg / vel_reciente if vel_reciente > 0 else None

        # Buscar próximo canónico para este producto
        row_prox = c.execute(
            """SELECT MIN(fecha_programada)
               FROM produccion_programada
               WHERE producto = ?
                 AND estado IN ('pendiente','programado','en_curso','esperando_recurso')
                 AND fin_real_at IS NULL
                 AND date(fecha_programada) >= date('now','-5 hours')""",
            (prod,),
        ).fetchone()
        proximo_canonico = row_prox[0] if row_prox else None
        dias_hasta_proximo = None
        adelantar_dias = 0
        if proximo_canonico and cob_reciente_dias is not None:
            try:
                f_prox = _date.fromisoformat(proximo_canonico[:10])
                dias_hasta_proximo = (f_prox - hoy).days
                # Producir 20 días antes de agotar (regla Sebastián)
                fecha_optima = hoy + _td(days=int(cob_reciente_dias - 20))
                if fecha_optima < f_prox:
                    adelantar_dias = (f_prox - fecha_optima).days
            except Exception:
                pass

        # Severidad
        if cob_reciente_dias and cob_reciente_dias < 15:
            severidad = "CRITICO"
        elif cob_reciente_dias and cob_reciente_dias < 25:
            severidad = "URGENTE"
        elif delta_pct > 100:
            severidad = "BOOM"  # ventas más que duplicadas
        else:
            severidad = "ACELERACION"

        alertas.append({
            "producto": prod,
            "severidad": severidad,
            "delta_pct": round(delta_pct, 1),
            "vel_baseline_kg_dia": round(vel_baseline, 3),
            "vel_reciente_kg_dia": round(vel_reciente, 3),
            "vel_baseline_uds_mes": int((n_bl.get("velocidad_uds_dia", 0) or 0) * 30),
            "vel_reciente_uds_mes": int((n_rc.get("velocidad_uds_dia", 0) or 0) * 30),
            "stock_actual_kg": round(stock_kg, 2),
            "cobertura_baseline_dias": round(cob_baseline_dias, 1) if cob_baseline_dias is not None else None,
            "cobertura_ajustada_dias": round(cob_reciente_dias, 1) if cob_reciente_dias is not None else None,
            "proximo_canonico": proximo_canonico[:10] if proximo_canonico else None,
            "dias_hasta_proximo_canonico": dias_hasta_proximo,
            "adelantar_dias": adelantar_dias,
            "accion_sugerida": (
                "🔥 PRODUCIR YA · stock crítico con velocidad nueva"
                if severidad == "CRITICO"
                else f"⚡ Adelantar próximo canónico {adelantar_dias} días"
                if adelantar_dias > 0
                else "📊 Monitorear · ventas en alza pero cobertura OK"
            ),
        })

    # Ordenar por severidad + cobertura ajustada
    SEVERIDAD_ORDEN = {"CRITICO": 0, "URGENTE": 1, "BOOM": 2, "ACELERACION": 3}
    alertas.sort(key=lambda x: (
        SEVERIDAD_ORDEN.get(x["severidad"], 9),
        x["cobertura_ajustada_dias"] or 99999,
    ))

    return jsonify({
        "umbral_pct": umbral_pct,
        "n_alertas": len(alertas),
        "alertas": alertas,
        "metodologia": (
            f"Compara vel_kg_dia últ 14d vs últ 60d. Alerta si delta >={umbral_pct}%. "
            "Calcula cobertura ajustada con vel_reciente. Sugiere adelantar próximo "
            "canónico si el agotamiento estimado es ANTES de la próxima producción."
        ),
    })


def _auto_programar_sugeridas(conn, dias_horizonte=365, ventana_velocidad=60,
                                  cob_critico=20, cob_alerta=25, cob_vigilar=45,
                                  usuario='cron-auto-sugerir', producto_filtro=None,
                                  origen_nuevo='eos_canonico', lote_kg_override=None):
    """Sebastián 23-may-2026 · 'el sistema calcula próxima producción pero
    no la coloca · se pierde la sugerencia'.

    Para cada producto con velocidad de venta:
      - Calcula proxima_sugerida_fecha (último_lote + duración - cob_alerta)
      - Si la fecha cae en próximos `dias_horizonte` días (default 365 desde
        FIX audit Abastecimiento 24-may-2026 · antes era 90 y se perdía 75%
        de las Sugeridas anuales · Abastecimiento ve 365d en sus horizontes
        así que el cron debe llenar todo el calendario para que coincida)
      - Y NO hay ya lote programado para ese producto en ventana [sug-7d, sug+7d]
      - Inserta producción Sugerida (origen='eos_canonico') con cantidad_kg = lote_bulk_kg

    Devuelve lista de creados. Llamado por cron diario y endpoint manual.
    """
    from datetime import date as _date2, timedelta as _td2
    productos = _calcular_animus_dtc(conn.cursor(), ventana=ventana_velocidad,
                                       cob_critico=cob_critico,
                                       cob_alerta=cob_alerta,
                                       cob_vigilar=cob_vigilar)
    hoy = _hoy_colombia()
    creados = []
    saltados = []
    cur = conn.cursor()
    # FIX 23-may-2026 Sebastián · si no hay fin_real_at (lote programado pero
    # no cerrado en Kanban), usar el Fijo programado como base para calcular
    # proxima_sugerida_fecha. Caso LAH: 70kg programado el 19, no se ha
    # finalizado · sin este fallback, _calcular_animus_dtc deja
    # proxima_sugerida_fecha=None y se salta.
    fijo_prog_por_prod = {}
    try:
        for r in cur.execute(
            """SELECT UPPER(TRIM(producto)) AS prod,
                      MAX(substr(fecha_programada,1,10)) AS f,
                      cantidad_kg
               FROM produccion_programada
               WHERE COALESCE(origen,'') IN ('eos_plan','eos_b2b','eos_retroactivo')
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                 AND fin_real_at IS NULL
                 AND COALESCE(cantidad_kg,0) > 0
               GROUP BY UPPER(TRIM(producto))""",
        ).fetchall():
            fijo_prog_por_prod[r[0]] = {'fecha': r[1], 'kg': float(r[2] or 0)}
    except Exception:
        pass

    filtro_upper = (producto_filtro or '').strip().upper() if producto_filtro else None
    for p in (productos or []):
        if True:
            prod = p.get('producto_nombre') or ''
            if filtro_upper and prod.strip().upper() != filtro_upper:
                continue
            # FIX 23-may-2026 PM Sebastián · "debería poder cambiar para
            # aumentar el lote y que dure más, calcule automático" · si el
            # caller pasó lote_kg_override (UI input editable), usamos ese
            # en lugar del lote_bulk_kg del producto.
            lote_kg = float(p.get('lote_bulk_kg') or 0)
            if lote_kg_override is not None:
                try:
                    _lk = float(lote_kg_override)
                    if 1.0 <= _lk <= 2000.0:
                        lote_kg = _lk
                except Exception:
                    pass
            vel = float(p.get('velocidad_kg_dia') or 0)
            psf = p.get('proxima_sugerida_fecha')

            # Fallback Fijo programado · sólo si _calcular_animus_dtc no
            # encontró producción completada para este producto.
            if not psf and prod and vel > 0 and lote_kg > 0:
                fp = fijo_prog_por_prod.get(prod.upper().strip())
                if fp and fp['kg'] > 0:
                    try:
                        f_base = _date2.fromisoformat(fp['fecha'])
                        dur = max(1, int(fp['kg'] / vel))
                        psf = (f_base + _td2(days=max(1, dur - cob_alerta))).isoformat()
                    except Exception:
                        psf = None

            if not prod:
                continue
            if lote_kg < 1.0:
                # FIX #2-b 23-may · lote_size_kg absurdo (< 1 kg de bulk) ·
                # NO auto-programar · arreglar en /api/admin/lote-size-fix
                saltados.append({'producto': prod,
                                  'razon': f'lote_size_kg={lote_kg} absurdo · fix en admin'})
                continue
            if vel <= 0:
                saltados.append({'producto': prod, 'razon': 'sin velocidad de venta'})
                continue
            if not psf:
                saltados.append({'producto': prod, 'razon': 'sin última producción para calcular base'})
                continue
            try:
                f_sug = _date2.fromisoformat(str(psf)[:10])
            except Exception:
                saltados.append({'producto': prod, 'razon': f'fecha inválida {psf}'})
                continue

            # Sebastián 25-may-2026 PM · FÓRMULAS ALTERNATIVAS · integración
            # del switching automático al auto-programar.
            # Si el producto pertenece a un canónico con >1 variantes
            # (ej. "LIP SERUM Animus" vs "LIP SERUM Espagiria", o PIB CHINO
            # vs Voluminizador), elegir la variante con menos faltante MP
            # ANTES de programar el lote. Así el cron evita lotes que van a
            # caer en esperando_recurso por MP agotada cuando hay variante
            # con stock disponible.
            prod_efectivo = prod
            switch_info = None
            try:
                # 1. Buscar canónico del producto actual
                row_can = cur.execute(
                    """SELECT COALESCE(producto_canonico,'') FROM formula_headers
                       WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))
                       LIMIT 1""", (prod,)).fetchone()
                canonico = (row_can[0] or '').strip() if row_can else ''
                if canonico:
                    seleccion = _seleccionar_variante_optima(conn, canonico, kg_objetivo=lote_kg)
                    if seleccion and seleccion.get('n_variantes_evaluadas', 0) > 1:
                        # Hay >1 variante · si la ganadora es distinta al original, switch
                        ganadora = seleccion.get('producto_nombre') or ''
                        if ganadora and ganadora.upper().strip() != prod.upper().strip():
                            switch_info = {
                                'original': prod,
                                'nuevo': ganadora,
                                'canonico': canonico,
                                'faltante_g': seleccion.get('faltante_total_g', 0),
                                'decision': seleccion.get('decision', ''),
                            }
                            prod_efectivo = ganadora
            except Exception as _e_sw:
                pass  # si _seleccionar_variante_optima falla, seguir con producto original

            # CADENA · Sebastián 23-may-2026 · "cuántas producciones o en cuánto"
            # Generar TODAS las sugeridas que caen en el horizonte, no solo la próxima.
            # Cada lote dura (lote_kg / vel) días · próxima = anterior + (dur - cob_alerta).
            # P0-10 23-may-PM · auditoría · paso mínimo 7d (era 1d) · si el lote
            # bulk es chico vs velocidad alta, paso podía ser 1d → avalancha
            # de 90 lotes en 90 días. Mínimo semanal para evitar spam.
            dur_lote = max(1, int(lote_kg / vel)) if vel > 0 else 0
            paso = max(7, dur_lote - cob_alerta) if dur_lote else 0
            if paso < 7:
                saltados.append({'producto': prod, 'razon': 'paso de cadena <7d (vel o lote inválidos)'})
                continue
            f_cursor = f_sug
            n_para_producto = 0
            while True:
                dias_hasta = (f_cursor - hoy).days
                if dias_hasta < 0:
                    f_cursor = f_cursor + _td2(days=paso)
                    continue
                if dias_hasta > dias_horizonte:
                    break
                # Buscar ya programado en ventana ±7d
                try:
                    fdesde = (f_cursor - _td2(days=7)).isoformat()
                    fhasta = (f_cursor + _td2(days=7)).isoformat()
                    # FIX 1-jun-2026 audit Planta · doble producción:
                    #  (a) chequear la VARIANTE que realmente se va a insertar
                    #      (prod_efectivo), no el original → si la variante ya tiene
                    #      lote ±7d no se duplica.
                    #  (b) NO excluir lotes con inventario_descontado_at: un lote YA
                    #      EN PRODUCCIÓN debe contar como ocupado · si se excluía, el
                    #      cron programaba un Sugerido encima de un Fijo en curso.
                    existing = cur.execute(
                        """SELECT COUNT(*) FROM produccion_programada
                           WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))
                             AND substr(fecha_programada,1,10) BETWEEN ? AND ?
                             AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')""",
                        (prod_efectivo, fdesde, fhasta),
                    ).fetchone()
                    if existing and int(existing[0] or 0) > 0:
                        saltados.append({'producto': prod, 'fecha': f_cursor.isoformat(),
                                          'razon': 'ya hay lote programado ±7d'})
                        f_cursor = f_cursor + _td2(days=paso)
                        continue
                except Exception:
                    break
                # INSERT con origen Sugerido · respeta Fijo vs Sugerido
                # Sebastián 25-may-2026 PM · usa prod_efectivo (variante elegida
                # por _seleccionar_variante_optima) en vez de prod original
                try:
                    obs_extra = ''
                    if switch_info:
                        obs_extra = (f' · 🔀 SWITCH variante: {switch_info["original"]} → '
                                      f'{switch_info["nuevo"]} (canónico {switch_info["canonico"]}, '
                                      f'faltante {switch_info["faltante_g"]:.0f}g)')
                    cur.execute(
                        """INSERT INTO produccion_programada
                           (producto, fecha_programada, cantidad_kg, lotes,
                            estado, origen, observaciones)
                           VALUES (?, ?, ?, 1, 'pendiente', ?, ?)""",
                        (prod_efectivo, f_cursor.isoformat(), lote_kg, origen_nuevo,
                         f'Auto-sugerido · cobertura {p.get("dias_cobertura","?")}d · '
                         f'velocidad {p.get("velocidad_kg_dia","?")} kg/día · '
                         f'lote dura {dur_lote}d' + obs_extra),
                    )
                    creados.append({
                        'producto': prod_efectivo,
                        'producto_original': prod if switch_info else None,
                        'switch_variante': switch_info,
                        'fecha': f_cursor.isoformat(),
                        'cantidad_kg': lote_kg,
                        'urgencia': p.get('urgencia'),
                        'dur_lote_dias': dur_lote,
                    })
                    n_para_producto += 1
                    try:
                        audit_log(cur, usuario=usuario,
                                  accion=('AUTO_PROGRAMAR_SUGERIDA_VARIANTE_SWITCH'
                                            if switch_info else 'AUTO_PROGRAMAR_SUGERIDA'),
                                  tabla='produccion_programada', registro_id='',
                                  despues={
                                      'producto': prod_efectivo,
                                      'producto_original': prod if switch_info else None,
                                      'switch_variante': switch_info,
                                      'fecha': f_cursor.isoformat(),
                                      'cantidad_kg': lote_kg,
                                      'urgencia': p.get('urgencia'),
                                      'razon': ('switch por menos faltante MP'
                                                  if switch_info else
                                                  'cadena velocidad + cob_alerta'),
                                  })
                    except Exception:
                        pass
                except Exception as e:
                    saltados.append({'producto': prod, 'fecha': f_cursor.isoformat(),
                                      'razon': str(e)[:100]})
                    break
                f_cursor = f_cursor + _td2(days=paso)
    if creados:
        conn.commit()
    return {'creados': creados, 'saltados': saltados,
            'n_creados': len(creados), 'n_saltados': len(saltados)}


@bp.route("/api/pedidos-b2b/<int:pid>/asignar-a-animus", methods=["POST"])
def pedidos_b2b_asignar_a_animus(pid):
    """Sebastián 24-may noche: 'le falta la parte asignar produccion y
    allí hace match con lo que ya está programado de animus'.

    Re-asigna un pedido B2B al lote Animus DTC más cercano del mismo
    producto (en lugar de tener lote dedicado eos_b2b). Útil cuando se
    creó un pedido y después aparece un lote Animus cerca · pegarlo
    ahí evita duplicar producción.

    Lógica:
    1. Lee pedido_b2b + su integración actual (pedidos_b2b_lote)
    2. Busca lote Animus DTC (eos_canonico/eos_plan/auto_plan) del mismo
       producto en ventana ±14d de la fecha del pedido
    3. Si encuentra match:
       - Si el lote actual era dedicado (eos_b2b solo de este pedido):
         lo cancela
       - Suma kg_b2b al nuevo lote canónico
       - INSERT/UPDATE pedidos_b2b_lote
       - Marca el pedido como 'confirmado'
    4. Si NO encuentra: devuelve error con sugerencia
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    pedido = cur.execute(
        """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                  COALESCE(cantidad_uds,0), COALESCE(ml_unidad,30),
                  fecha_estimada, COALESCE(envase_codigo,''),
                  COALESCE(estado,'pendiente')
           FROM pedidos_b2b WHERE id = ?""",
        (pid,),
    ).fetchone()
    if not pedido:
        return jsonify({'error': 'Pedido no existe'}), 404
    pid_real, cli_id, cli_nom, producto, uds, ml, fecha_est, env_cod, estado = pedido
    if estado == 'cancelado':
        return jsonify({'error': 'pedido cancelado · no se puede asignar'}), 400
    kg_b2b = round(float(uds or 0) * float(ml or 30) / 1000.0, 2)
    if kg_b2b <= 0:
        return jsonify({'error': 'pedido con kg=0'}), 400
    # Sebastián 25-may-2026 · audit zero-error · validar whitelist envases
    # B2B (clientes_b2b_envases · mig 173) en asignación manual. Antes el
    # POST original validaba pero la re-asignación admin omitía el check ·
    # admin podía aprobar pedido con envase no permitido sin error claro.
    if env_cod and cli_id:
        try:
            _permitido = cur.execute(
                """SELECT 1 FROM clientes_b2b_envases
                   WHERE cliente_id = ?
                     AND UPPER(TRIM(envase_codigo)) = UPPER(TRIM(?))
                     AND COALESCE(activo, 1) = 1
                   LIMIT 1""",
                (cli_id, env_cod),
            ).fetchone()
            if not _permitido:
                return jsonify({
                    'error': (f"Envase '{env_cod}' no está en whitelist del "
                              f"cliente {cli_nom or cli_id} · agregarlo en "
                              f"/admin/clientes-b2b o cambiar el envase del pedido"),
                    'codigo': 'ENVASE_NO_PERMITIDO',
                    'cliente_id': cli_id,
                    'envase_codigo': env_cod,
                }), 403
        except sqlite3.OperationalError:
            # Tabla mig 173 podría no existir en instancias muy viejas ·
            # fallback permisivo (no bloquear si la infra está incompleta)
            pass

    # Fecha objetivo · igual que _integrar_pedido_b2b_al_plan
    from datetime import date as _d, timedelta as _td
    hoy = _hoy_colombia() if '_hoy_colombia' in globals() else _d.today()
    if fecha_est:
        try:
            f_target = _d.fromisoformat(str(fecha_est)[:10]) - _td(days=10)
        except Exception:
            f_target = hoy + _td(days=7)
    else:
        f_target = hoy + _td(days=7)

    # Sebastián 25-may-2026 PM · caso "Centella": el pedido decía no
    # encontrar lote programado pero SÍ existía. Causa: match restrictivo:
    #  - UPPER(TRIM()) no normaliza tildes ni espacios múltiples
    #  - No usa producto_canonico (mig 174) · variantes "Centella Esencia"
    #    vs "Esencia de Centella" no matcheaban aunque comparten canónico
    #  - Ventana ±14d muy chica para B2B (clientes piden con mes+)
    #  - "No encontrado" sin candidatos · admin no sabe qué hacer
    # Ahora:
    #  - LEFT JOIN formula_headers para usar producto_canonico
    #  - Match si nombre exacto OR canónico igual
    #  - Ventana ampliada a ±30d
    #  - Si no hay match en ±30d, devuelve TOP 5 candidatos del canónico
    #    en CUALQUIER fecha futura · frontend puede listar y elegir
    canonico = ''
    try:
        row_can = cur.execute(
            "SELECT COALESCE(producto_canonico,'') FROM formula_headers "
            "WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?)) LIMIT 1",
            (producto,)).fetchone()
        if row_can:
            canonico = (row_can[0] or '').strip()
    except Exception:
        canonico = ''
    # Si no tiene canónico explícito, usar el nombre como canónico
    if not canonico:
        canonico = producto

    lote_animus = cur.execute(
        """SELECT pp.id, pp.fecha_programada, COALESCE(pp.cantidad_kg, 0),
                  COALESCE(pp.origen,''), pp.producto
           FROM produccion_programada pp
           LEFT JOIN formula_headers fh
             ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
           WHERE (UPPER(TRIM(pp.producto)) = UPPER(TRIM(?))
                  OR UPPER(TRIM(COALESCE(fh.producto_canonico,''))) = UPPER(TRIM(?)))
             AND COALESCE(pp.origen,'') IN ('eos_plan','eos_canonico','calendar','manual','auto_plan','sugerido')
             AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado','esperando_recurso')
             AND pp.inicio_real_at IS NULL AND pp.fin_real_at IS NULL
             AND ABS(julianday(pp.fecha_programada) - julianday(?)) <= 30
           ORDER BY ABS(julianday(pp.fecha_programada) - julianday(?)) ASC
           LIMIT 1""",
        (producto, canonico, f_target.isoformat(), f_target.isoformat()),
    ).fetchone()

    if not lote_animus:
        # Buscar candidatos del mismo canónico en CUALQUIER fecha futura
        # para que admin pueda elegir manualmente
        candidatos = []
        try:
            for r in cur.execute(
                """SELECT pp.id, pp.producto, pp.fecha_programada,
                          COALESCE(pp.cantidad_kg,0), COALESCE(pp.origen,''),
                          COALESCE(pp.estado,'')
                   FROM produccion_programada pp
                   LEFT JOIN formula_headers fh
                     ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
                   WHERE (UPPER(TRIM(pp.producto)) = UPPER(TRIM(?))
                          OR UPPER(TRIM(COALESCE(fh.producto_canonico,''))) = UPPER(TRIM(?)))
                     AND COALESCE(pp.origen,'') IN ('eos_plan','eos_canonico','calendar','manual','auto_plan','sugerido')
                     AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
                     AND pp.inicio_real_at IS NULL AND pp.fin_real_at IS NULL
                     AND pp.fecha_programada >= date('now','-5 hours','-7 day')
                   ORDER BY pp.fecha_programada ASC
                   LIMIT 5""",
                (producto, canonico)).fetchall():
                candidatos.append({
                    'id': r[0], 'producto': r[1], 'fecha': r[2],
                    'kg': float(r[3] or 0), 'origen': r[4], 'estado': r[5],
                })
        except Exception:
            pass
        return jsonify({
            'error': (f"No hay lote Animus DTC de '{producto}' en ventana ±30d "
                       f"de {f_target.isoformat()}"),
            'producto_buscado': producto,
            'producto_canonico': canonico,
            'fecha_objetivo': f_target.isoformat(),
            'candidatos_fuera_ventana': candidatos,
            'sugerencia': ('Hay {} lote(s) del mismo producto fuera de la ventana ±30d · '
                           'usá /api/pedidos-b2b/{}/asignar-a-lote/<lote_id> para forzar '
                           'asignación específica, o programá un lote nuevo'
                          ).format(len(candidatos), pid)
                          if candidatos else
                          'Programá primero un lote Animus DTC manualmente, o esperá al cron auto-sugerir',
        }), 404

    lote_animus_id = lote_animus[0]
    lote_fecha = (lote_animus[1] or '')[:10]

    # Limpiar integración previa
    try:
        # Lotes b2b dedicados del pedido (los cancelamos)
        for (lid_b2b,) in cur.execute(
            """SELECT lote_produccion_id FROM pedidos_b2b_lote
               WHERE pedido_b2b_id = ? AND modo = 'lote_dedicado'""",
            (pid,),
        ).fetchall():
            # Verificar que el lote dedicado es solo de ESTE pedido
            otros = cur.execute(
                "SELECT COUNT(*) FROM pedidos_b2b_lote WHERE lote_produccion_id = ? AND pedido_b2b_id != ?",
                (lid_b2b, pid),
            ).fetchone()
            if not otros or int(otros[0] or 0) == 0:
                cur.execute(
                    """UPDATE produccion_programada
                       SET estado = 'cancelado',
                           observaciones = SUBSTR(COALESCE(observaciones,'') ||
                             ' · CANCELADO_REASIGNADO_A_LOTE_' || ?, -1500)
                       WHERE id = ? AND inicio_real_at IS NULL""",
                    (str(lote_animus_id), lid_b2b),
                )
        # Quitar links viejos
        cur.execute("DELETE FROM pedidos_b2b_lote WHERE pedido_b2b_id = ?", (pid,))
    except Exception:
        pass

    # Sumar kg al lote Animus
    cur.execute(
        """UPDATE produccion_programada
           SET cantidad_kg = COALESCE(cantidad_kg, 0) + ?,
               origen = 'eos_plan',
               observaciones = SUBSTR(COALESCE(observaciones,'') ||
                  ' · +' || ? || 'kg B2B ' || ? || ' (pedido #' || ? || ' asignado manual)',
                  -1500)
           WHERE id = ?""",
        (kg_b2b, kg_b2b, cli_nom or '', pid, lote_animus_id),
    )

    # INSERT link estructurado
    try:
        cur.execute(
            """INSERT OR REPLACE INTO pedidos_b2b_lote
                 (pedido_b2b_id, lote_produccion_id, kg_aporte,
                  unidades_aporte, ml_unidad, envase_codigo, modo,
                  cliente_nombre)
               VALUES (?, ?, ?, ?, ?, ?, 'sumado_a_lote_canonico', ?)""",
            (pid, lote_animus_id, kg_b2b, int(uds or 0), float(ml or 30),
             env_cod, cli_nom or ''),
        )
    except Exception:
        pass

    # Marcar pedido como confirmado
    cur.execute(
        "UPDATE pedidos_b2b SET estado = 'confirmado' WHERE id = ? AND estado != 'cancelado'",
        (pid,),
    )

    audit_log(cur, usuario=user, accion='B2B_ASIGNAR_A_ANIMUS',
              tabla='pedidos_b2b', registro_id=pid,
              despues={'lote_animus_id': lote_animus_id,
                        'lote_fecha': lote_fecha,
                        'kg_sumados': kg_b2b})
    # FEATURE 24-may noche · regenerar etiqueta de distribución
    _regenerar_distribucion_lote(cur, lote_animus_id)
    # Refactor observaciones · evento estructurado en el lote Animus
    _registrar_evento_prod(cur, lote_animus_id, 'B2B_ASIGNADO_MANUAL',
        f'+{kg_b2b}kg · {cli_nom or "B2B"} · pedido #{pid} asignado manual',
        user)
    conn.commit()

    # Re-leer total del lote post-suma
    row_post = cur.execute(
        "SELECT cantidad_kg FROM produccion_programada WHERE id=?",
        (lote_animus_id,),
    ).fetchone()
    return jsonify({
        'ok': True,
        'pedido_id': pid,
        'lote_animus_id': lote_animus_id,
        'lote_fecha': lote_fecha,
        'kg_sumados': kg_b2b,
        'kg_total_lote': float(row_post[0] or 0) if row_post else 0,
        'mensaje': f'Pedido asignado al lote Animus DTC #{lote_animus_id} ({lote_fecha}) · +{kg_b2b}kg',
    })


@bp.route("/api/pedidos-b2b/<int:pid>/diagnostico-match", methods=["GET"])
def pedidos_b2b_diagnostico_match(pid):
    """Sebastián 25-may-2026 PM · "intente con centella y decia que no
    estaba programada pero si estaba revisa a fondo que si funcione".
    Endpoint diagnóstico que explica por qué el match B2B↔Animus falla:
    - Qué producto/canónico buscó
    - Qué lotes existen (cualquier estado, cualquier fecha)
    - Por qué se descartó cada uno (fuera de ventana / estado / origen / ya inició)
    Para que admin vea CON SUS OJOS qué pasó.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    pedido = cur.execute(
        """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                  COALESCE(cantidad_uds,0), COALESCE(ml_unidad,30),
                  fecha_estimada, COALESCE(estado,'pendiente')
           FROM pedidos_b2b WHERE id = ?""", (pid,)).fetchone()
    if not pedido:
        return jsonify({'error': 'Pedido no existe'}), 404
    _id, cli_id, cli_nom, producto, uds, ml, fecha_est, estado = pedido
    kg_b2b = round(float(uds or 0) * float(ml or 30) / 1000.0, 2)
    from datetime import date as _d, timedelta as _td
    hoy = _hoy_colombia() if '_hoy_colombia' in globals() else _d.today()
    if fecha_est:
        try:
            f_target = _d.fromisoformat(str(fecha_est)[:10]) - _td(days=10)
        except Exception:
            f_target = hoy + _td(days=7)
    else:
        f_target = hoy + _td(days=7)
    # Canonico
    canonico = ''
    try:
        row_can = cur.execute(
            "SELECT COALESCE(producto_canonico,'') FROM formula_headers "
            "WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?)) LIMIT 1",
            (producto,)).fetchone()
        if row_can:
            canonico = (row_can[0] or '').strip()
    except Exception:
        pass
    if not canonico:
        canonico = producto
    # Lotes candidatos · TODOS los que comparten producto o canonico
    candidatos = []
    try:
        for r in cur.execute(
            """SELECT pp.id, pp.producto, pp.fecha_programada,
                      COALESCE(pp.cantidad_kg,0), COALESCE(pp.origen,''),
                      COALESCE(pp.estado,''),
                      pp.inicio_real_at, pp.fin_real_at,
                      COALESCE(fh.producto_canonico,'') as canonico
               FROM produccion_programada pp
               LEFT JOIN formula_headers fh
                 ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
               WHERE UPPER(TRIM(pp.producto)) = UPPER(TRIM(?))
                  OR UPPER(TRIM(COALESCE(fh.producto_canonico,''))) = UPPER(TRIM(?))
               ORDER BY pp.fecha_programada ASC""",
            (producto, canonico)).fetchall():
            # Determinar por qué se descartaría
            descartado = []
            origen = r[4] or ''
            estado_lote = (r[5] or '').lower()
            if origen not in ('eos_plan','eos_canonico','calendar','manual','auto_plan','sugerido'):
                descartado.append(f'origen={origen} (necesita eos_plan/canónico/etc)')
            if estado_lote in ('cancelado','completado','esperando_recurso'):
                descartado.append(f'estado={estado_lote}')
            if r[6]:
                descartado.append('ya inició producción')
            if r[7]:
                descartado.append('ya terminó')
            # Distancia a target
            dias_dif = None
            try:
                if r[2]:
                    fl = _d.fromisoformat(str(r[2])[:10])
                    dias_dif = (fl - f_target).days
                    if abs(dias_dif) > 30:
                        descartado.append(f'fuera de ±30d ({dias_dif:+d}d)')
            except Exception:
                pass
            candidatos.append({
                'id': r[0], 'producto': r[1], 'fecha': r[2],
                'kg': float(r[3] or 0), 'origen': origen,
                'estado': estado_lote, 'canonico': r[8] or '',
                'dias_de_target': dias_dif,
                'match_directo': len(descartado) == 0,
                'razones_descarte': descartado,
            })
    except Exception as e:
        return jsonify({'error': f'diagnóstico fallo: {e}'}), 500
    return jsonify({
        'pedido_id': pid,
        'cliente': cli_nom,
        'producto_pedido': producto,
        'producto_canonico': canonico,
        'kg_b2b': kg_b2b,
        'fecha_estimada': fecha_est,
        'fecha_target': f_target.isoformat(),
        'ventana_dias': 30,
        'total_lotes_existentes_mismo_producto': len(candidatos),
        'matchearían_directo': sum(1 for c in candidatos if c['match_directo']),
        'candidatos': candidatos,
    })


@bp.route("/api/pedidos-b2b/<int:pid>/asignar-a-lote/<int:lote_id>", methods=["POST"])
def pedidos_b2b_asignar_a_lote(pid, lote_id):
    """Forzar asignación a un lote específico · útil cuando el match
    automático (asignar-a-animus) no encontró por ventana o canónico.

    Sebastián 25-may-2026 PM · "tenga la opción de juntar producción"
    incluso si está fuera de ventana ±30d, vos eligís.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    pedido = cur.execute(
        """SELECT id, cliente_id, cliente_nombre, producto_nombre,
                  COALESCE(cantidad_uds,0), COALESCE(ml_unidad,30),
                  fecha_estimada, COALESCE(envase_codigo,''),
                  COALESCE(estado,'pendiente')
           FROM pedidos_b2b WHERE id = ?""", (pid,)).fetchone()
    if not pedido:
        return jsonify({'error': 'Pedido no existe'}), 404
    _id, cli_id, cli_nom, producto, uds, ml, _fe, env_cod, estado = pedido
    if estado == 'cancelado':
        return jsonify({'error': 'pedido cancelado'}), 400
    kg_b2b = round(float(uds or 0) * float(ml or 30) / 1000.0, 2)
    if kg_b2b <= 0:
        return jsonify({'error': 'pedido con kg=0'}), 400
    lote = cur.execute(
        """SELECT id, producto, fecha_programada, COALESCE(cantidad_kg,0),
                  COALESCE(origen,''), COALESCE(estado,''),
                  inicio_real_at, fin_real_at
           FROM produccion_programada WHERE id = ?""", (lote_id,)).fetchone()
    if not lote:
        return jsonify({'error': f'Lote #{lote_id} no existe'}), 404
    _lid, _lprod, lfecha, _lkg, lorigen, lestado, linicio, lfin = lote
    if (lestado or '').lower() in ('cancelado','completado'):
        return jsonify({'error': f'Lote #{lote_id} está {lestado}'}), 400
    if linicio or lfin:
        return jsonify({'error': f'Lote #{lote_id} ya inició/terminó · no se puede modificar'}), 400
    # Limpiar integración previa del pedido
    for (lid_b2b,) in cur.execute(
        """SELECT lote_produccion_id FROM pedidos_b2b_lote
           WHERE pedido_b2b_id = ? AND modo = 'lote_dedicado'""", (pid,)).fetchall():
        otros = cur.execute(
            "SELECT COUNT(*) FROM pedidos_b2b_lote WHERE lote_produccion_id = ? AND pedido_b2b_id != ?",
            (lid_b2b, pid)).fetchone()
        if not otros or int(otros[0] or 0) == 0:
            cur.execute(
                """UPDATE produccion_programada SET estado='cancelado',
                       observaciones = SUBSTR(COALESCE(observaciones,'') ||
                       ' · CANCELADO_REASIGNADO_MANUAL_LOTE_' || ?, -1500)
                   WHERE id = ? AND inicio_real_at IS NULL""",
                (str(lote_id), lid_b2b))
    cur.execute("DELETE FROM pedidos_b2b_lote WHERE pedido_b2b_id = ?", (pid,))
    # Sumar kg al lote elegido
    cur.execute(
        """UPDATE produccion_programada
           SET cantidad_kg = COALESCE(cantidad_kg,0) + ?,
               origen = 'eos_plan',
               observaciones = SUBSTR(COALESCE(observaciones,'') ||
                  ' · +' || ? || 'kg B2B ' || ? || ' (pedido #' || ? || ' forzado)',
                  -1500)
           WHERE id = ?""",
        (kg_b2b, kg_b2b, cli_nom or '', pid, lote_id))
    try:
        cur.execute(
            """INSERT OR REPLACE INTO pedidos_b2b_lote
                 (pedido_b2b_id, lote_produccion_id, kg_aporte,
                  unidades_aporte, ml_unidad, envase_codigo, modo, cliente_nombre)
               VALUES (?, ?, ?, ?, ?, ?, 'sumado_a_lote_canonico', ?)""",
            (pid, lote_id, kg_b2b, int(uds or 0), float(ml or 30),
             env_cod, cli_nom or ''))
    except Exception:
        pass
    cur.execute("UPDATE pedidos_b2b SET estado='confirmado' WHERE id=? AND estado!='cancelado'", (pid,))
    audit_log(cur, usuario=user, accion='B2B_ASIGNAR_A_LOTE_FORZADO',
              tabla='pedidos_b2b', registro_id=pid,
              despues={'lote_id': lote_id, 'kg_sumados': kg_b2b})
    try:
        _regenerar_distribucion_lote(cur, lote_id)
    except Exception: pass
    try:
        _registrar_evento_prod(cur, lote_id, 'B2B_ASIGNADO_FORZADO',
            f'+{kg_b2b}kg · {cli_nom or "B2B"} · pedido #{pid} (forzado manual)', user)
    except Exception: pass
    conn.commit()
    row_post = cur.execute(
        "SELECT cantidad_kg FROM produccion_programada WHERE id=?", (lote_id,)).fetchone()
    return jsonify({
        'ok': True, 'pedido_id': pid, 'lote_id': lote_id,
        'kg_sumados': kg_b2b,
        'kg_total_lote': float(row_post[0] or 0) if row_post else 0,
        'mensaje': f'Pedido asignado FORZADO al lote #{lote_id} ({(lfecha or "")[:10]}) · +{kg_b2b}kg',
    })


@bp.route("/api/pedidos-b2b/diagnostico-cliente", methods=["GET"])
def pedidos_b2b_diagnostico_cliente():
    """Read-only · estado de las pedidos B2B de un cliente vs el calendario.

    Sebastián 30-may-2026 (caso Kelly Guerra): normalizar sin tocar nada primero.
    Para cada pedido devuelve: estado, kg, lotes vinculados (pedidos_b2b_lote),
    cuántas veces aparece en observaciones (detecta texto duplicado), si hay un
    lote del producto en el calendario, y una recomendación. NO muta nada.
    """
    err = _require_login()
    if err:
        return err
    cliente = (request.args.get("cliente") or "").strip()
    if not cliente:
        return jsonify({"error": "cliente requerido (id o nombre)"}), 400
    conn = get_db()
    c = conn.cursor()

    # Pedidos del cliente · match por cliente_id exacto o nombre LIKE
    _sel = ("SELECT id, cliente_id, cliente_nombre, producto_nombre, "
            "COALESCE(cantidad_uds,0), COALESCE(ml_unidad,30), fecha_estimada, "
            "COALESCE(estado,'pendiente'), {urg} "
            "FROM pedidos_b2b WHERE (cliente_id = ? OR UPPER(COALESCE(cliente_nombre,'')) "
            "LIKE UPPER(?)) ORDER BY fecha_estimada ASC, id ASC")
    like = '%' + cliente + '%'
    try:
        rows = c.execute(_sel.format(urg="COALESCE(urgencia,'media')"),
                         (cliente, like)).fetchall()
    except Exception:
        rows = c.execute(_sel.format(urg="'media'"), (cliente, like)).fetchall()

    pedidos = []
    n_vinc = n_sin_lote = n_dup = 0
    estados_count = {}
    for r in rows:
        pid, cli_id, cli_nom, producto, uds, ml, fest, estado, urg = r
        kg = round(float(uds or 0) * float(ml or 30) / 1000.0, 2)
        estados_count[estado] = estados_count.get(estado, 0) + 1

        # Lotes vinculados (pedidos_b2b_lote)
        vinc = []
        try:
            for lr in c.execute(
                """SELECT pbl.lote_produccion_id, COALESCE(pbl.kg_aporte,0),
                          COALESCE(pbl.modo,''), pp.fecha_programada,
                          COALESCE(pp.estado,''), COALESCE(pp.cantidad_kg,0),
                          COALESCE(pp.origen,''), pp.inicio_real_at, pp.fin_real_at
                   FROM pedidos_b2b_lote pbl
                   LEFT JOIN produccion_programada pp ON pp.id = pbl.lote_produccion_id
                   WHERE pbl.pedido_b2b_id = ?""", (pid,)).fetchall():
                vinc.append({
                    "lote_id": lr[0], "kg_aporte": round(float(lr[1] or 0), 2),
                    "modo": lr[2], "fecha": (lr[3] or "")[:10],
                    "lote_estado": lr[4], "lote_kg": round(float(lr[5] or 0), 2),
                    "origen": lr[6],
                    "iniciado": bool(lr[7]), "terminado": bool(lr[8]),
                })
        except Exception:
            vinc = []
        lotes_distintos = len(set(v["lote_id"] for v in vinc if v["lote_id"]))

        # Veces que el pedido aparece en observaciones (texto duplicado)
        apariciones_texto = 0
        try:
            for (obs,) in c.execute(
                "SELECT COALESCE(observaciones,'') FROM produccion_programada "
                "WHERE observaciones LIKE ?", ('%pedido #' + str(pid) + '%',)
            ).fetchall():
                apariciones_texto += (obs or '').count('pedido #' + str(pid))
        except Exception:
            apariciones_texto = 0

        # ¿Hay un lote ACTIVO futuro de este producto (aunque no esté vinculado)?
        try:
            hay_lote = c.execute(
                """SELECT COUNT(*) FROM produccion_programada
                   WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
                     AND COALESCE(estado,'') NOT IN ('cancelado','completado')
                     AND fin_real_at IS NULL
                     AND date(fecha_programada) >= date('now','-5 hours')""",
                (producto,)).fetchone()[0]
        except Exception:
            hay_lote = 0

        vinculado = len(vinc) > 0
        duplicado = (lotes_distintos > 1) or (apariciones_texto > 1)
        sin_lote = (not vinculado) and (hay_lote == 0)
        if vinculado:
            n_vinc += 1
        if sin_lote:
            n_sin_lote += 1
        if duplicado:
            n_dup += 1

        if duplicado:
            reco = "DUPLICADO · vinculado a varios lotes o repetido en observaciones · deduplicar"
        elif vinculado:
            reco = "OK · vinculado a lote · se puede marcar 'en producción'"
        elif hay_lote > 0:
            reco = "Hay lote del producto en calendario pero el pedido NO está vinculado · vincular (sin sumar kg si ya lo incluiste)"
        else:
            reco = "SIN lote en calendario · falta programar este producto"

        pedidos.append({
            "id": pid, "producto": producto, "uds": int(uds or 0),
            "kg": kg, "fecha_estimada": (fest or "")[:10] if fest else None,
            "estado": estado, "urgencia": str(urg or 'media').lower(),
            "lotes_vinculados": vinc, "n_lotes_distintos": lotes_distintos,
            "apariciones_texto": apariciones_texto,
            "hay_lote_calendario": int(hay_lote or 0),
            "vinculado": vinculado, "duplicado": duplicado, "sin_lote": sin_lote,
            "recomendacion": reco,
        })

    return jsonify({
        "ok": True,
        "cliente": cliente,
        "cliente_nombre": (rows[0][2] if rows else cliente),
        "n_pedidos": len(pedidos),
        "n_vinculados": n_vinc,
        "n_sin_lote": n_sin_lote,
        "n_duplicados": n_dup,
        "estados": estados_count,
        "pedidos": pedidos,
        "nota": ("Read-only · no modifica nada. 'duplicado' = el pedido cuenta "
                 "más de una vez (en >1 lote o repetido en observaciones)."),
    })


@bp.route("/api/admin/sub-skus", methods=["GET"])
def admin_sub_skus_listar():
    """Lista todos los SKUs agrupados por producto canónico con tonos.

    Devuelve estructura:
    {
        productos: [
            {producto_nombre, n_skus, n_regalos, ml_promedio,
             skus: [{sku, tono_label, es_regalo, ml_unidad, ventas_60d, ...}]}
        ]
    }
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    productos_map = {}
    try:
        # SKUs con producto + ventas 60d para contexto
        rows = cur.execute(
            """SELECT spm.sku, spm.producto_nombre,
                      COALESCE(spm.activo, 1),
                      COALESCE(spm.es_regalo, 0),
                      COALESCE(spm.tono_label, ''),
                      COALESCE(pp.volumen_ml, 0) AS ml_unidad
               FROM sku_producto_map spm
               LEFT JOIN producto_presentaciones pp
                 ON UPPER(TRIM(pp.sku_codigo)) = UPPER(TRIM(spm.sku))
                 AND COALESCE(pp.activo, 1) = 1
               WHERE spm.producto_nombre IS NOT NULL
                 AND TRIM(spm.producto_nombre) != ''
               ORDER BY spm.producto_nombre, spm.sku"""
        ).fetchall()
    except Exception:
        # fallback si producto_presentaciones no existe
        rows = cur.execute(
            """SELECT sku, producto_nombre, COALESCE(activo,1),
                      COALESCE(es_regalo,0), COALESCE(tono_label,''), 0
               FROM sku_producto_map
               WHERE producto_nombre IS NOT NULL AND TRIM(producto_nombre) != ''
               ORDER BY producto_nombre, sku"""
        ).fetchall()

    for r in rows:
        prod = r[1].strip() if r[1] else ''
        if not prod:
            continue
        info = productos_map.setdefault(prod, {
            'producto_nombre': prod,
            'skus': [],
            'n_skus': 0, 'n_regalos': 0, 'ml_promedio': 0,
        })
        info['skus'].append({
            'sku': r[0], 'activo': bool(r[2]),
            'es_regalo': bool(r[3]),
            'tono_label': r[4] or '',
            'ml_unidad': float(r[5] or 0),
        })
    for info in productos_map.values():
        skus_act = [s for s in info['skus'] if s['activo'] and not s['es_regalo']]
        info['n_skus'] = len(info['skus'])
        info['n_regalos'] = sum(1 for s in info['skus'] if s['es_regalo'])
        info['n_activos_no_regalo'] = len(skus_act)
        info['n_tonos'] = sum(1 for s in info['skus'] if s['tono_label'])
        mls = [s['ml_unidad'] for s in info['skus'] if s['ml_unidad'] > 0]
        info['ml_promedio'] = round(sum(mls) / len(mls), 1) if mls else 0
    productos = sorted(productos_map.values(),
                       key=lambda p: (-p['n_skus'], p['producto_nombre']))
    return jsonify({'productos': productos, 'total': len(productos)})


@bp.route("/api/admin/sub-skus/<path:sku>", methods=["PATCH"])
def admin_sub_skus_editar(sku):
    """Edita un SKU específico · es_regalo, tono_label, activo, ml_unidad."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    body = request.get_json(silent=True) or {}
    sku_norm = (sku or '').strip().upper()
    if not sku_norm:
        return jsonify({'error': 'SKU requerido'}), 400
    conn = get_db(); cur = conn.cursor()
    sets = []
    params = []
    if 'es_regalo' in body:
        sets.append("es_regalo = ?")
        params.append(1 if body['es_regalo'] else 0)
    if 'tono_label' in body:
        sets.append("tono_label = ?")
        params.append((body.get('tono_label') or '').strip()[:50])
    if 'activo' in body:
        sets.append("activo = ?")
        params.append(1 if body['activo'] else 0)
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(sku_norm)
    try:
        res = cur.execute(
            f"UPDATE sku_producto_map SET {', '.join(sets)} WHERE UPPER(TRIM(sku)) = ?",
            params,
        )
        if res.rowcount == 0:
            return jsonify({'error': f'SKU {sku_norm} no existe en sku_producto_map'}), 404
        # ml_unidad va en producto_presentaciones (no en sku_producto_map)
        if 'ml_unidad' in body:
            try:
                ml = float(body['ml_unidad'])
                if 0 < ml < 5000:
                    # UPSERT en producto_presentaciones
                    pp_existe = cur.execute(
                        "SELECT 1 FROM producto_presentaciones WHERE UPPER(TRIM(sku_codigo)) = ?",
                        (sku_norm,),
                    ).fetchone()
                    if pp_existe:
                        cur.execute(
                            "UPDATE producto_presentaciones SET volumen_ml = ? WHERE UPPER(TRIM(sku_codigo)) = ?",
                            (ml, sku_norm),
                        )
                    else:
                        # producto_nombre desde sku_producto_map
                        pn = cur.execute(
                            "SELECT producto_nombre FROM sku_producto_map WHERE UPPER(TRIM(sku)) = ?",
                            (sku_norm,),
                        ).fetchone()
                        cur.execute(
                            """INSERT INTO producto_presentaciones
                                 (sku_codigo, producto_nombre, volumen_ml, activo)
                               VALUES (?, ?, ?, 1)""",
                            (sku_norm, (pn[0] if pn else ''), ml),
                        )
            except Exception:
                pass
        audit_log(cur, usuario=user, accion='SUB_SKU_PATCH',
                  tabla='sku_producto_map', registro_id=sku_norm,
                  despues=body)
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'sku': sku_norm})


@bp.route("/admin/sub-skus", methods=["GET"])
def admin_sub_skus_pagina():
    """Página HTML standalone · gestión visual de sub-SKUs (tonos + regalos).

    Sebastián 24-may noche · 'Sub-SKUs regalos + tonos variables'.
    Cada producto con multi-SKUs (BLUSH BALM x5 tonos, LIP SERUM x6
    tonos, BBM mini regalo) se ve agrupado · editable inline.
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin/compras</h2></body></html>", 403
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Sub-SKUs</title>
<style>
  body{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:24px}
  .card{max-width:1400px;margin:0 auto 14px;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.08)}
  h1{color:#1e293b;margin:0 0 8px;font-size:22px}
  .filtros{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
  .filtros input,.filtros select{padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px}
  .producto-grp{border:1px solid #e2e8f0;border-radius:10px;margin-bottom:10px;background:#fff}
  .prod-head{padding:12px 16px;background:#f8fafc;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;cursor:pointer}
  .prod-head:hover{background:#f1f5f9}
  .prod-titulo{font-weight:700;color:#1e293b;font-size:14px}
  .prod-meta{font-size:11px;color:#64748b}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;margin-left:6px}
  .b-regalo{background:#fce7f3;color:#9f1239}
  .b-tonos{background:#dbeafe;color:#1e40af}
  .b-multi{background:#fef3c7;color:#92400e}
  .skus-tbl{padding:8px 16px;display:none}
  .skus-tbl.open{display:block}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th{background:#f1f5f9;padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;color:#475569}
  td{border-bottom:1px solid #f1f5f9;padding:6px 8px}
  input.inp-sku{width:100%;padding:4px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px;background:transparent}
  input.inp-sku:hover{background:#fffbeb}
  input.inp-sku:focus{background:#fff;border-color:#7c3aed;outline:none}
  .chk{transform:scale(1.3);cursor:pointer}
  #msg{margin:8px 0;font-size:12px;font-weight:700}
  .btn{padding:6px 12px;border-radius:5px;border:none;font-size:11px;font-weight:700;cursor:pointer}
  .btn-prim{background:#7c3aed;color:#fff}
  .btn-link{background:transparent;color:#475569;border:1px solid #e2e8f0}
</style></head><body>

<div class="card">
  <h1>🎨 Sub-SKUs · gestión visual de tonos y regalos</h1>
  <p style="color:#475569;font-size:13px">Editá inline cada sub-SKU. <strong>Regalo</strong>: no cuenta para velocidad de ventas. <strong>Tono</strong>: etiqueta visible (ROSA, DURAZNO, etc.). <strong>ml</strong>: volumen real por unidad (afecta el cálculo de envases en Abastecimiento).</p>
  <div style="background:#ecfdf5;border:1px solid #86efac;color:#065f46;padding:8px 12px;border-radius:6px;font-size:12px;margin-top:8px">
    💾 <strong>Guardado automático</strong>: cada cambio se persiste al hacer click fuera del campo (no hay botón "Guardar"). El input se pone <span style="background:#bbf7d0;padding:1px 6px;border-radius:3px">verde ✓</span> 1 seg cuando se confirma.
  </div>
  <div id="stats" style="margin-top:10px;font-size:12px"></div>
  <div class="filtros">
    <input id="q" placeholder="🔍 Filtrar por producto o SKU…" oninput="render()">
    <select id="filtro-tipo" onchange="render()">
      <option value="">Todos los productos</option>
      <option value="multi">Solo multi-SKU (3+)</option>
      <option value="con_regalos">Con regalos</option>
      <option value="con_tonos">Con tonos asignados</option>
      <option value="sin_tonos">Multi-SKU SIN tonos</option>
    </select>
    <button class="btn btn-prim" onclick="cargar()">↻ Recargar</button>
    <a href="/admin/clientes-b2b" class="btn btn-link" style="text-decoration:none;line-height:1.4">👥 Clientes B2B</a>
    <a href="/" class="btn btn-link" style="text-decoration:none;line-height:1.4">← Dashboard</a>
  </div>
  <div id="msg"></div>
</div>

<div class="card">
  <div id="lista"><p style="color:#94a3b8;text-align:center;padding:20px">Cargando…</p></div>
</div>

<script>
let DATA=null;
let CSRF_TOK='';

async function _loadCsrf(){
  try{
    const r=await fetch('/api/csrf-token',{credentials:'same-origin'});
    if(r.ok){ const d=await r.json(); CSRF_TOK=d.csrf_token||d.token||''; }
  }catch(_){}
}

function msg(text, ok){
  const el=document.getElementById('msg');
  el.innerHTML='<span style="color:'+(ok?'#15803d':'#dc2626')+'">'+text+'</span>';
  setTimeout(()=>{el.innerHTML=''},4000);
}

async function cargar(){
  try{
    if(!CSRF_TOK) await _loadCsrf();
    const r=await fetch('/api/admin/sub-skus');
    const d=await r.json();
    DATA=d;
    render();
  }catch(e){msg('Error red: '+e.message)}
}

function render(){
  const q=(document.getElementById('q').value||'').toLowerCase().trim();
  const f=document.getElementById('filtro-tipo').value;
  let prods=DATA.productos||[];
  if(f==='multi') prods=prods.filter(p=>p.n_skus>=3);
  if(f==='con_regalos') prods=prods.filter(p=>p.n_regalos>0);
  if(f==='con_tonos') prods=prods.filter(p=>p.n_tonos>0);
  if(f==='sin_tonos') prods=prods.filter(p=>p.n_skus>=2 && p.n_tonos===0);
  if(q){
    prods=prods.filter(p=>{
      if(p.producto_nombre.toLowerCase().indexOf(q)>=0) return true;
      return p.skus.some(s=>s.sku.toLowerCase().indexOf(q)>=0 || (s.tono_label||'').toLowerCase().indexOf(q)>=0);
    });
  }
  // Stats globales sobre TODOS los productos (no filtrados)
  let totalSku=0, conMl=0, conTono=0;
  (DATA.productos||[]).forEach(p=>{
    p.skus.forEach(s=>{
      totalSku++;
      if(s.ml_unidad && s.ml_unidad>0) conMl++;
      if(s.tono_label && s.tono_label.trim()) conTono++;
    });
  });
  const pctMl=totalSku?Math.round(conMl*100/totalSku):0;
  const pctTono=totalSku?Math.round(conTono*100/totalSku):0;
  const statsEl=document.getElementById('stats');
  if(statsEl){
    statsEl.innerHTML=
      '<span style="background:'+(pctMl>=95?'#dcfce7':pctMl>=50?'#fef3c7':'#fee2e2')+';color:#0f172a;padding:4px 10px;border-radius:6px;font-weight:700">📏 '+conMl+' / '+totalSku+' con tamaño ('+pctMl+'%)</span> '+
      '<span style="background:'+(pctTono>=95?'#dcfce7':pctTono>=50?'#fef3c7':'#fee2e2')+';color:#0f172a;padding:4px 10px;border-radius:6px;font-weight:700;margin-left:8px">🎨 '+conTono+' / '+totalSku+' con tono ('+pctTono+'%)</span>';
  }
  const cont=document.getElementById('lista');
  if(!prods.length){cont.innerHTML='<p style="color:#94a3b8;text-align:center;padding:20px">Sin resultados</p>';return}
  cont.innerHTML=prods.map((p,idx)=>renderProducto(p,idx)).join('');
}

function renderProducto(p, idx){
  const badges=[];
  if(p.n_skus>=3) badges.push('<span class="badge b-multi">Multi · '+p.n_skus+' SKUs</span>');
  if(p.n_tonos>0) badges.push('<span class="badge b-tonos">'+p.n_tonos+' tonos</span>');
  if(p.n_regalos>0) badges.push('<span class="badge b-regalo">'+p.n_regalos+' regalo</span>');
  let html='<div class="producto-grp">';
  html+='<div class="prod-head" onclick="toggle('+idx+')">';
  html+='<div><div class="prod-titulo">'+esc(p.producto_nombre)+badges.join('')+'</div>';
  html+='<div class="prod-meta">'+p.n_skus+' SKUs · '+(p.ml_promedio?p.ml_promedio.toFixed(1)+'ml prom · ':'')+p.n_activos_no_regalo+' activos no-regalo</div></div>';
  html+='<span style="color:#7c3aed;font-size:12px;font-weight:700" id="toggle-'+idx+'">▶ Expandir</span>';
  html+='</div>';
  html+='<div class="skus-tbl" id="skus-'+idx+'">';
  html+='<table><thead><tr><th>SKU</th><th style="text-align:center">Activo</th><th style="text-align:center">Regalo</th><th>Tono / etiqueta</th><th style="text-align:right">ml/u</th></tr></thead><tbody>';
  p.skus.forEach(s=>{
    html+='<tr>'
      +'<td style="font-family:ui-monospace;font-weight:600">'+esc(s.sku)+'</td>'
      +'<td style="text-align:center"><input type="checkbox" class="chk" '+(s.activo?'checked':'')+' onchange="patchSku(\\''+esc(s.sku)+'\\',{activo:this.checked}, this)"></td>'
      +'<td style="text-align:center"><input type="checkbox" class="chk" '+(s.es_regalo?'checked':'')+' onchange="patchSku(\\''+esc(s.sku)+'\\',{es_regalo:this.checked}, this)"></td>'
      +'<td><input class="inp-sku" value="'+esc(s.tono_label||'')+'" placeholder="ROSA, DURAZNO, BORGOÑA…" onblur="if(this.value!=this.defaultValue) patchSku(\\''+esc(s.sku)+'\\',{tono_label:this.value}, this)"></td>'
      +'<td style="text-align:right"><input class="inp-sku" type="number" min="0" max="5000" step="0.1" value="'+(s.ml_unidad||0)+'" style="text-align:right;font-family:ui-monospace" onblur="if(parseFloat(this.value)!=parseFloat(this.defaultValue)) patchSku(\\''+esc(s.sku)+'\\',{ml_unidad:parseFloat(this.value)}, this)"></td>'
      +'</tr>';
  });
  html+='</tbody></table>';
  html+='</div></div>';
  return html;
}

function toggle(idx){
  const tbl=document.getElementById('skus-'+idx);
  const lbl=document.getElementById('toggle-'+idx);
  if(tbl.classList.contains('open')){
    tbl.classList.remove('open'); lbl.textContent='▶ Expandir';
  }else{
    tbl.classList.add('open'); lbl.textContent='▼ Contraer';
  }
}

async function patchSku(sku, patch, inputEl){
  // Mientras guarda · borde amarillo
  if(inputEl){
    inputEl.style.transition='background 0.3s,border-color 0.3s';
    inputEl.style.borderColor='#f59e0b';
    inputEl.style.background='#fffbeb';
  }
  try{
    if(!CSRF_TOK) await _loadCsrf();
    const hdrs={'Content-Type':'application/json'};
    if(CSRF_TOK) hdrs['X-CSRF-Token']=CSRF_TOK;
    const r=await fetch('/api/admin/sub-skus/'+encodeURIComponent(sku),{
      method:'PATCH', headers:hdrs, credentials:'same-origin',
      body:JSON.stringify(patch),
    });
    const d=await r.json();
    if(!r.ok){
      msg('✗ Error '+sku+': '+(d.error||r.status));
      if(inputEl){ inputEl.style.borderColor='#dc2626'; inputEl.style.background='#fef2f2'; }
      return;
    }
    msg('✓ '+sku+' guardado',true);
    if(inputEl){
      inputEl.style.borderColor='#16a34a';
      inputEl.style.background='#dcfce7';
      // Reset el defaultValue para que onblur no dispare otra vez si el user vuelve a hacer focus
      if('value' in inputEl) inputEl.defaultValue=inputEl.value;
      setTimeout(()=>{
        inputEl.style.borderColor='';
        inputEl.style.background='';
      },1200);
    }
    // Refrescar la data en memoria sin recargar todo
    const k=Object.keys(patch)[0];
    DATA.productos.forEach(p=>{
      p.skus.forEach(s=>{
        if(s.sku===sku){
          s[k]=patch[k];
        }
      });
    });
    // Recalcular stats sin re-renderizar toda la lista
    try{
      let totalSku=0, conMl=0, conTono=0;
      (DATA.productos||[]).forEach(p=>{
        p.skus.forEach(s=>{
          totalSku++;
          if(s.ml_unidad && s.ml_unidad>0) conMl++;
          if(s.tono_label && s.tono_label.trim()) conTono++;
        });
      });
      const pctMl=totalSku?Math.round(conMl*100/totalSku):0;
      const pctTono=totalSku?Math.round(conTono*100/totalSku):0;
      const statsEl=document.getElementById('stats');
      if(statsEl){
        statsEl.innerHTML=
          '<span style="background:'+(pctMl>=95?'#dcfce7':pctMl>=50?'#fef3c7':'#fee2e2')+';color:#0f172a;padding:4px 10px;border-radius:6px;font-weight:700">📏 '+conMl+' / '+totalSku+' con tamaño ('+pctMl+'%)</span> '+
          '<span style="background:'+(pctTono>=95?'#dcfce7':pctTono>=50?'#fef3c7':'#fee2e2')+';color:#0f172a;padding:4px 10px;border-radius:6px;font-weight:700;margin-left:8px">🎨 '+conTono+' / '+totalSku+' con tono ('+pctTono+'%)</span>';
      }
    }catch(_){}
  }catch(e){
    msg('✗ Error red: '+e.message);
    if(inputEl){ inputEl.style.borderColor='#dc2626'; inputEl.style.background='#fef2f2'; }
  }
}

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}

cargar();
</script>
</body></html>"""


@bp.route("/api/admin/lotes/regenerar-distribucion", methods=["POST"])
def admin_lotes_regenerar_distribucion():
    """Sebastián 24-may noche · regenera distribucion_resumen para
    TODOS los lotes activos con aportes B2B. Útil para back-fill de
    lotes que existían antes de que el helper se llamara automáticamente.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    regenerados = 0
    try:
        # Todos los lotes con al menos 1 aporte B2B + lotes activos sin aporte
        lote_ids = set()
        try:
            for (lid,) in cur.execute(
                "SELECT DISTINCT lote_produccion_id FROM pedidos_b2b_lote"
            ).fetchall():
                lote_ids.add(lid)
        except Exception:
            pass
        # Agregar también lotes activos sin aportes para que muestren 100% DTC
        for (lid,) in cur.execute(
            """SELECT id FROM produccion_programada
               WHERE LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                 AND fin_real_at IS NULL
                 AND COALESCE(distribucion_resumen,'') = ''"""
        ).fetchall():
            lote_ids.add(lid)
        for lid in lote_ids:
            _regenerar_distribucion_lote(cur, lid)
            regenerados += 1
        audit_log(cur, usuario=user, accion='B2B_REGEN_DISTRIBUCION',
                  tabla='produccion_programada', registro_id='bulk',
                  despues={'regenerados': regenerados})
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'regenerados': regenerados})


@bp.route("/api/admin/clientes-b2b/migrar-desde-maquila", methods=["POST"])
def admin_clientes_b2b_migrar_maquila():
    """Migra clientes de la tabla legacy clientes_maquila al maestro
    clientes_b2b_maestro con tipo='MAQUILA'. Útil cuando Sebastián ve
    nombres como Kelly Guerra que estaban en la tabla vieja pero deben
    aparecer en el módulo B2B unificado.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db(); cur = conn.cursor()
    creados, ya_existen, errores = 0, 0, []
    try:
        for r in cur.execute(
            """SELECT codigo, nombre, COALESCE(email,''), COALESCE(telefono,''),
                      COALESCE(comparte_formula_con,'')
               FROM clientes_maquila
               WHERE COALESCE(activo, 1) = 1"""
        ).fetchall():
            cod, nom, email, tel, comparte = r
            cliente_id = (cod or '').strip().lower().replace(' ', '_')
            if not cliente_id:
                continue
            existe = cur.execute(
                "SELECT 1 FROM clientes_b2b_maestro WHERE cliente_id = ?",
                (cliente_id,),
            ).fetchone()
            if existe:
                ya_existen += 1
                continue
            try:
                cur.execute(
                    """INSERT INTO clientes_b2b_maestro
                         (cliente_id, cliente_nombre, email, telefono, tipo, notas)
                       VALUES (?, ?, ?, ?, 'MAQUILA', ?)""",
                    (cliente_id, nom, email, tel,
                     f'Migrado desde clientes_maquila · comparte_formula={comparte}'),
                )
                creados += 1
            except Exception as e:
                errores.append({'cliente_id': cliente_id, 'error': str(e)[:100]})
        audit_log(cur, usuario=user, accion='B2B_MIGRAR_DESDE_MAQUILA',
                  tabla='clientes_b2b_maestro', registro_id='bulk',
                  despues={'creados': creados, 'ya_existen': ya_existen,
                            'errores': len(errores)})
        conn.commit()
    except sqlite3.OperationalError as e:
        return jsonify({'error': f'tabla clientes_maquila no existe: {e}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'creados': creados,
                    'ya_existen': ya_existen, 'errores': errores})


# ════════════════════════════════════════════════════════════════════════
# /admin/auditar-inflaciones · Sebastián 25-may-2026 PM
# "yo habia inflado la produccion en animus porque sabia que fernando
# necesitaria revisa a fondo eso y veras que si"
#
# Detecta lotes Animus DTC donde cantidad_kg > lote_size_kg canónico
# del Excel · sin desglose B2B atribuido · sospechoso de inflación a ojo
# del pasado. Permite atribuir el delta retroactivo a un cliente B2B
# para que el calendario muestre el split correcto.
# ════════════════════════════════════════════════════════════════════════

@bp.route("/api/admin/auditar-inflaciones", methods=["GET"])
def auditar_inflaciones_listar():
    """Lista lotes con sospecha de inflación oculta.

    Algoritmo:
    - kg_real    = pp.cantidad_kg (lo programado)
    - kg_dtc_esp = formula_headers.lote_size_kg (canónico del Excel)
    - kg_b2b_atrib = SUM(pedidos_b2b_lote.kg_aporte) del lote
    - delta = kg_real - kg_dtc_esp - kg_b2b_atrib
    - Si delta > umbral (default 0.5kg) Y kg_b2b_atrib es 0 o muy chico
      → SOSPECHA de inflación a ojo · admin atribuye al cliente correcto.

    Query: ?umbral_kg=0.5 (mínimo delta para flagear)
            ?incluir_atribuidos=0 (si 1, incluye lotes ya con B2B atribuido)
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    try:
        umbral = float(request.args.get('umbral_kg', '0.5') or '0.5')
    except ValueError:
        umbral = 0.5
    if umbral < 0.1: umbral = 0.1
    if umbral > 100: umbral = 100
    incluir_atrib = request.args.get('incluir_atribuidos', '0') == '1'
    conn = get_db(); cur = conn.cursor()
    # Lotes Animus DTC futuros sin completar/cancelar/iniciar
    rows = cur.execute(
        """SELECT pp.id, pp.producto, pp.fecha_programada,
                  COALESCE(pp.cantidad_kg, 0) as kg_real,
                  COALESCE(fh.lote_size_kg, 0) as lote_size_kg,
                  COALESCE(pp.origen,''),
                  COALESCE(pp.observaciones,'')
           FROM produccion_programada pp
           LEFT JOIN formula_headers fh
             ON UPPER(TRIM(fh.producto_nombre)) = UPPER(TRIM(pp.producto))
           WHERE COALESCE(pp.origen,'') IN ('eos_plan','eos_canonico','calendar','manual','auto_plan','sugerido')
             AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado','esperando_recurso')
             AND pp.inicio_real_at IS NULL AND pp.fin_real_at IS NULL
             AND pp.fecha_programada >= date('now','-5 hours','-7 day')
           ORDER BY pp.fecha_programada ASC""").fetchall()
    lote_ids = [r[0] for r in rows]
    b2b_por_lote = {}
    if lote_ids:
        try:
            ph = ','.join('?' * len(lote_ids))
            for br in cur.execute(
                f"""SELECT pbl.lote_produccion_id,
                          COALESCE(NULLIF(TRIM(pbl.cliente_nombre),''),
                                   NULLIF(TRIM(pb.cliente_nombre),''),
                                   'B2B') as cliente,
                          COALESCE(pbl.kg_aporte, 0)
                   FROM pedidos_b2b_lote pbl
                   LEFT JOIN pedidos_b2b pb ON pb.id = pbl.pedido_b2b_id
                   WHERE pbl.lote_produccion_id IN ({ph})""",
                lote_ids).fetchall():
                b2b_por_lote.setdefault(br[0], []).append({
                    'cliente': br[1], 'kg': float(br[2] or 0)})
        except Exception:
            pass
    inflados = []
    for r in rows:
        lote_id, producto, fecha, kg_real, lote_size_kg, origen, obs = r
        kg_real = float(kg_real or 0)
        lote_size_kg = float(lote_size_kg or 0)
        b2b_list = b2b_por_lote.get(lote_id, [])
        kg_b2b_atrib = round(sum(x['kg'] for x in b2b_list), 2)
        # Si no hay lote_size_kg canónico, asumir kg_real (no podemos detectar inflación)
        if lote_size_kg <= 0:
            continue
        delta = round(kg_real - lote_size_kg - kg_b2b_atrib, 2)
        if delta < umbral:
            continue
        if kg_b2b_atrib > 0 and not incluir_atrib:
            # Si ya tiene B2B atribuido pero igual el delta supera el umbral,
            # mostrar solo si --incluir_atribuidos=1 · típicamente es ajuste fino
            continue
        inflados.append({
            'lote_id': lote_id,
            'producto': producto,
            'fecha': fecha,
            'kg_real': kg_real,
            'lote_size_kg': lote_size_kg,
            'kg_b2b_atribuido': kg_b2b_atrib,
            'b2b_clientes': b2b_list,
            'delta_sospechoso': delta,
            'origen': origen,
            'observaciones': obs[:200] if obs else '',
        })
    return jsonify({
        'inflados': inflados,
        'total': len(inflados),
        'kg_total_sospechosos': round(sum(x['delta_sospechoso'] for x in inflados), 2),
        'umbral_kg': umbral,
        'incluir_atribuidos': incluir_atrib,
    })


@bp.route("/api/admin/auditar-inflaciones/atribuir", methods=["POST"])
def auditar_inflaciones_atribuir():
    """Atribuye el delta de un lote inflado a un cliente B2B retroactivo.

    Crea un pedido_b2b retroactivo + el link pedidos_b2b_lote · NO suma
    a cantidad_kg (ya está en el total) · solo etiqueta el desglose.

    Body: {lote_id, cliente_id, kg_atribuir, nota?}
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    d = request.get_json(silent=True) or {}
    try:
        lote_id = int(d.get('lote_id') or 0)
        cliente_id = (d.get('cliente_id') or '').strip()
        kg_atribuir = float(d.get('kg_atribuir') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'inputs inválidos'}), 400
    nota = (d.get('nota') or 'atribución retroactiva inflación')[:200]
    if lote_id <= 0 or not cliente_id or kg_atribuir <= 0:
        return jsonify({'error': 'lote_id, cliente_id y kg_atribuir > 0 requeridos'}), 400
    if kg_atribuir > 10000:
        return jsonify({'error': 'kg_atribuir fuera de rango (max 10000)'}), 400
    conn = get_db(); cur = conn.cursor()
    # Validar lote
    lote = cur.execute(
        "SELECT id, producto, fecha_programada, COALESCE(cantidad_kg,0), COALESCE(estado,''), inicio_real_at, fin_real_at "
        "FROM produccion_programada WHERE id = ?", (lote_id,)).fetchone()
    if not lote:
        return jsonify({'error': f'lote #{lote_id} no existe'}), 404
    if (lote[4] or '').lower() in ('cancelado','completado'):
        return jsonify({'error': f'lote #{lote_id} está {lote[4]}'}), 400
    if lote[5] or lote[6]:
        return jsonify({'error': f'lote #{lote_id} ya inició/terminó · no atribuir retroactivo'}), 400
    # Validar cliente
    cli = cur.execute(
        "SELECT cliente_id, cliente_nombre FROM clientes_b2b_maestro WHERE cliente_id = ?",
        (cliente_id,)).fetchone()
    if not cli:
        return jsonify({'error': f'cliente_id {cliente_id} no existe en clientes_b2b_maestro'}), 404
    cli_nom = cli[1]
    producto = lote[1] or ''
    fecha_lote = lote[2] or ''
    # Crear pedido_b2b retroactivo · ml=50 default · uds = kg_atribuir*1000/ml
    uds_aprox = max(1, int(round(kg_atribuir * 1000 / 50)))
    try:
        cur.execute(
            """INSERT INTO pedidos_b2b
                 (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                  ml_unidad, fecha_estimada, notas, creado_por, estado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmado')""",
            (cliente_id, cli_nom, producto, uds_aprox, 50.0, fecha_lote,
             f'RETROACTIVO inflación · {nota}', f'audit:{user}'))
        pedido_id = cur.lastrowid
    except Exception as e:
        return jsonify({'error': f'no pude crear pedido retroactivo: {e}'}), 500
    # Link pedido↔lote
    try:
        cur.execute(
            """INSERT INTO pedidos_b2b_lote
                 (pedido_b2b_id, lote_produccion_id, kg_aporte,
                  unidades_aporte, ml_unidad, modo, cliente_nombre)
               VALUES (?, ?, ?, ?, 50.0, 'sumado_a_lote_canonico', ?)""",
            (pedido_id, lote_id, kg_atribuir, uds_aprox, cli_nom))
    except Exception as e:
        return jsonify({'error': f'pedido creado pero link falló: {e}'}), 500
    # NO sumamos cantidad_kg · solo etiquetamos el desglose existente
    try:
        cur.execute(
            """UPDATE produccion_programada
               SET observaciones = SUBSTR(COALESCE(observaciones,'') ||
                  ' · ATRIBUIDO_RETROACTIVO +' || ? || 'kg ' || ? || ' (audit '|| ? ||')',
                  -1500)
               WHERE id = ?""",
            (kg_atribuir, cli_nom, user, lote_id))
    except Exception: pass
    audit_log(cur, usuario=user, accion='B2B_ATRIBUIR_RETROACTIVO',
              tabla='pedidos_b2b_lote', registro_id=pedido_id,
              despues={'lote_id': lote_id, 'cliente_id': cliente_id,
                        'kg_atribuir': kg_atribuir, 'nota': nota})
    try: _regenerar_distribucion_lote(cur, lote_id)
    except Exception: pass
    conn.commit()
    return jsonify({
        'ok': True, 'pedido_id_retroactivo': pedido_id, 'lote_id': lote_id,
        'cliente': cli_nom, 'kg_atribuido': kg_atribuir,
        'mensaje': f'✓ {kg_atribuir}kg del lote #{lote_id} atribuidos a {cli_nom} (retroactivo)',
    }), 201


@bp.route("/admin/auditar-inflaciones", methods=["GET"])
def auditar_inflaciones_pagina():
    """Página HTML standalone para limpiar inflaciones del pasado."""
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/auditar-inflaciones')
    user = session.get('compras_user', '')
    try:
        admin_set = set(ADMIN_USERS)
        compras_set = set(COMPRAS_ACCESS)
    except Exception:
        admin_set, compras_set = set(), set()
    if user not in (admin_set | compras_set):
        return ("<html><body style='font-family:system-ui;padding:48px'>"
                 "<h2>Solo admin/compras</h2></body></html>"), 403
    return _AUDITAR_INFLACIONES_HTML


_AUDITAR_INFLACIONES_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Auditar inflaciones</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;margin:0;padding:24px;color:#0f172a}
  .wrap{max-width:1280px;margin:0 auto}
  h1{color:#0f766e;margin:0 0 4px;font-size:22px}
  .sub{color:#64748b;font-size:13px;margin-bottom:18px}
  .card{background:#fff;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
  .stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}
  .stat{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 18px;flex:1;min-width:160px}
  .stat-lbl{font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.5px}
  .stat-val{font-size:22px;font-weight:800;color:#0f172a;margin-top:4px}
  .stat-val.warn{color:#ca8a04}
  .stat-val.danger{color:#dc2626}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#f1f5f9;padding:10px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569;font-weight:700;letter-spacing:.5px}
  td{border-bottom:1px solid #f1f5f9;padding:10px;vertical-align:top}
  tr:hover{background:#f8fafc}
  .lote-id{font-family:monospace;color:#64748b;font-weight:700}
  .delta{font-weight:800;color:#dc2626}
  .delta-info{font-size:11px;color:#64748b;margin-top:2px}
  .btn{padding:6px 12px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer}
  .btn-prim{background:#0f766e;color:#fff}
  .btn-prim:hover{background:#0d635c}
  .btn-sec{background:#e2e8f0;color:#475569}
  .filtros{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
  .filtros label{font-size:12px;color:#475569;font-weight:600}
  .filtros input,.filtros select{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px}
  .empty{text-align:center;color:#94a3b8;padding:30px}
  .modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;justify-content:center;align-items:center;z-index:1000;padding:20px}
  .modal-bg.show{display:flex}
  .modal{background:#fff;border-radius:14px;max-width:480px;width:100%;padding:24px}
  .modal h2{margin:0 0 6px;font-size:18px;color:#0f172a}
  .modal .sub{margin-bottom:14px}
  .modal label{display:block;font-size:12px;color:#475569;font-weight:700;margin:10px 0 4px;text-transform:uppercase;letter-spacing:.5px}
  .modal select,.modal input{width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;font-family:inherit}
  .actions{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}
</style></head><body>
<div class="wrap">
  <h1>🔍 Auditar inflaciones de producción</h1>
  <div class="sub">Sebastián: "yo había inflado la producción en Animus porque sabía que Fernando necesitaría" · atribuí el delta al cliente correcto para que el calendario muestre el split real.</div>

  <div class="filtros card">
    <label>Umbral kg sospechoso ≥</label>
    <input type="number" id="umbral" value="0.5" min="0.1" max="100" step="0.1" style="width:70px">
    <label><input type="checkbox" id="incluir-atrib" style="width:auto"> Incluir lotes ya con B2B atribuido</label>
    <button class="btn btn-prim" onclick="cargar()">🔍 Buscar</button>
    <a href="/admin/clientes-b2b" class="btn btn-sec" style="text-decoration:none">← Clientes B2B</a>
  </div>

  <div class="stats" id="stats"></div>

  <div class="card">
    <table>
      <thead><tr>
        <th>Lote</th>
        <th>Producto</th>
        <th>Fecha</th>
        <th>kg real / canónico</th>
        <th>B2B atribuido</th>
        <th class="delta">Δ sospechoso</th>
        <th></th>
      </tr></thead>
      <tbody id="lista"><tr><td colspan="7" class="empty">Click "Buscar" para listar inflaciones</td></tr></tbody>
    </table>
  </div>
</div>

<!-- Modal atribuir -->
<div class="modal-bg" id="modal" onclick="if(event.target===this)cerrar()">
  <div class="modal">
    <h2>Atribuir delta retroactivo</h2>
    <div class="sub" id="m-info"></div>
    <label>Cliente</label>
    <select id="m-cliente"><option value="">— Cargando —</option></select>
    <label>kg a atribuir</label>
    <input id="m-kg" type="number" min="0.1" max="10000" step="0.1">
    <label>Nota (opcional)</label>
    <input id="m-nota" placeholder="ej. inflado a ojo para Fernando">
    <div class="actions">
      <button class="btn btn-sec" onclick="cerrar()">Cancelar</button>
      <button class="btn btn-prim" onclick="guardar()">💾 Atribuir</button>
    </div>
  </div>
</div>

<script>
let _csrfTok = '';
let _loteSel = null;
let _clientes = [];

fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d && d.csrf_token) _csrfTok = d.csrf_token; });

async function cargarClientes(){
  try{
    const r = await fetch('/api/clientes-b2b');
    const d = await r.json();
    _clientes = d.items || d.clientes || [];
  }catch(_){}
}

function escapeHtml(s){
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function cargar(){
  const umbral = document.getElementById('umbral').value || '0.5';
  const incl = document.getElementById('incluir-atrib').checked ? '1' : '0';
  const lista = document.getElementById('lista');
  const stats = document.getElementById('stats');
  lista.innerHTML = '<tr><td colspan="7" class="empty">Cargando...</td></tr>';
  try{
    const r = await fetch('/api/admin/auditar-inflaciones?umbral_kg=' + umbral + '&incluir_atribuidos=' + incl);
    const d = await r.json();
    if(!r.ok){
      lista.innerHTML = '<tr><td colspan="7" class="empty">Error: ' + (d.error || r.status) + '</td></tr>';
      return;
    }
    stats.innerHTML =
      '<div class="stat"><div class="stat-lbl">Lotes sospechosos</div><div class="stat-val warn">' + d.total + '</div></div>' +
      '<div class="stat"><div class="stat-lbl">kg totales sin atribuir</div><div class="stat-val danger">' + d.kg_total_sospechosos.toFixed(1) + ' kg</div></div>' +
      '<div class="stat"><div class="stat-lbl">Umbral aplicado</div><div class="stat-val">≥ ' + d.umbral_kg + ' kg</div></div>';
    if(!d.inflados.length){
      lista.innerHTML = '<tr><td colspan="7" class="empty">🎉 Sin lotes sospechosos · todo está atribuido correctamente</td></tr>';
      return;
    }
    lista.innerHTML = d.inflados.map(l => {
      const b2bTxt = l.b2b_clientes.length > 0
        ? l.b2b_clientes.map(c => escapeHtml(c.cliente) + ' (' + c.kg + 'kg)').join(', ')
        : '<span style="color:#94a3b8">ninguno</span>';
      return '<tr>'
        + '<td class="lote-id">#' + l.lote_id + '</td>'
        + '<td><strong>' + escapeHtml(l.producto) + '</strong><div class="delta-info">origen: ' + escapeHtml(l.origen) + '</div></td>'
        + '<td>' + escapeHtml(l.fecha) + '</td>'
        + '<td>' + l.kg_real + ' / ' + l.lote_size_kg + ' kg</td>'
        + '<td>' + b2bTxt + '</td>'
        + '<td class="delta">+' + l.delta_sospechoso + ' kg</td>'
        + '<td><button class="btn btn-prim" onclick="abrirAtribuir(' + l.lote_id + ',' + l.delta_sospechoso + ',&quot;' + escapeHtml(l.producto) + '&quot;,&quot;' + escapeHtml(l.fecha) + '&quot;)">⚓ Atribuir</button></td>'
        + '</tr>';
    }).join('');
  }catch(e){
    lista.innerHTML = '<tr><td colspan="7" class="empty">Error red: ' + e.message + '</td></tr>';
  }
}

async function abrirAtribuir(loteId, deltaKg, producto, fecha){
  _loteSel = loteId;
  if(_clientes.length === 0) await cargarClientes();
  const sel = document.getElementById('m-cliente');
  sel.innerHTML = '<option value="">— Elegí cliente —</option>' +
    _clientes.filter(c => c.activo !== false).map(c =>
      '<option value="' + escapeHtml(c.cliente_id) + '">' + escapeHtml(c.cliente_nombre) + ' · ' + escapeHtml(c.tipo || 'B2B') + '</option>'
    ).join('');
  document.getElementById('m-info').textContent =
    'Lote #' + loteId + ' · ' + producto + ' · ' + fecha + ' · delta sospechoso: ' + deltaKg + 'kg';
  document.getElementById('m-kg').value = deltaKg;
  document.getElementById('m-nota').value = '';
  document.getElementById('modal').classList.add('show');
}

function cerrar(){
  document.getElementById('modal').classList.remove('show');
  _loteSel = null;
}

async function guardar(){
  if(!_loteSel) return;
  const cliente = document.getElementById('m-cliente').value;
  const kg = parseFloat(document.getElementById('m-kg').value);
  const nota = document.getElementById('m-nota').value.trim();
  if(!cliente){ alert('Elegí un cliente'); return; }
  if(!(kg > 0)){ alert('kg debe ser > 0'); return; }
  try{
    const r = await fetch('/api/admin/auditar-inflaciones/atribuir', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token': _csrfTok},
      body: JSON.stringify({lote_id: _loteSel, cliente_id: cliente, kg_atribuir: kg, nota: nota}),
    });
    const d = await r.json();
    if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    alert(d.mensaje || '✓ Atribuido');
    cerrar();
    cargar();
  }catch(e){ alert('Error red: ' + e.message); }
}

// Carga clientes al boot · sin esperar primer atribuir
cargarClientes();
</script>
</body></html>
"""


@bp.route("/admin/clientes-b2b", methods=["GET"])
def admin_clientes_b2b_pagina():
    """Página HTML standalone · módulo admin de Clientes B2B.

    Sebastián 24-may noche: 'ya dice kelly guerra que es otro cliente,
    cómo vamos a incorporar esa producción · no creamos el módulo de
    clientes · cómo creamos ese módulo allí para que mapee lo que ya
    está de ese producto y se adicione · y tenga para adicionar otros'.

    Dashboard con:
    - Tabla de clientes B2B (de clientes_b2b_maestro + counts agregados)
    - Botón Migrar desde Maquila (mueve Kelly, etc. al maestro)
    - Botón + Nuevo cliente · form modal
    - Click cliente → vista detalle pedidos
    - Botón + Nuevo pedido · form modal con producto + cantidad + ml + fecha
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin/compras</h2></body></html>", 403

    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Clientes B2B</title>
<style>
  body{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:24px}
  .card{max-width:1400px;margin:0 auto 14px;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.08)}
  h1{color:#1e293b;margin:0 0 8px;font-size:22px}
  h2{color:#0f766e;margin:18px 0 12px;font-size:15px}
  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
  th{background:#f1f5f9;padding:10px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569}
  td{border-bottom:1px solid #f1f5f9;padding:10px}
  tr.row-cli{cursor:pointer}
  tr.row-cli:hover{background:#f0fdf4}
  .btn{padding:8px 16px;border-radius:6px;border:none;font-size:12px;font-weight:700;cursor:pointer;margin-right:6px}
  .btn-prim{background:#7c3aed;color:#fff}
  .btn-sec{background:#0891b2;color:#fff}
  .btn-warn{background:#f59e0b;color:#fff}
  .btn-link{background:transparent;color:#475569;border:1px solid #e2e8f0}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700}
  .b-MAQUILA{background:#fef3c7;color:#92400e}
  .b-B2B{background:#dbeafe;color:#1e40af}
  .b-INFLUENCER{background:#fce7f3;color:#9f1239}
  .b-OTRO{background:#f1f5f9;color:#475569}
  .modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:none;align-items:center;justify-content:center;padding:20px}
  .modal{background:#fff;border-radius:14px;padding:24px;max-width:720px;width:100%;max-height:90vh;overflow:auto}
  label{display:block;font-size:11px;color:#475569;margin-bottom:3px;margin-top:8px;font-weight:600}
  input, select, textarea{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;box-sizing:border-box}
  .info{background:#dbeafe;border-left:4px solid #1e40af;padding:12px 16px;border-radius:6px;color:#1e3a8a;font-size:12px;margin:12px 0}
  .actions-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px}
</style></head><body>

<div class="card">
  <h1>👥 Clientes B2B · módulo admin</h1>
  <p style="color:#475569;font-size:13px">Gestión unificada de clientes B2B + maquila + influencer. Cada cliente puede tener pedidos que entran al calendario de producción y suman al consumo.</p>
  <div class="actions-row">
    <button class="btn btn-prim" onclick="abrirModalCliente()">+ Nuevo cliente</button>
    <button class="btn btn-sec" onclick="migrarMaquila()" title="Trae clientes que están en clientes_maquila (legacy) al maestro B2B">📦 Migrar desde Maquila</button>
    <a href="/admin/diag-flujo-abast" class="btn btn-link" style="text-decoration:none;line-height:1.4">📊 Abastecimiento</a>
    <a href="/" class="btn btn-link" style="text-decoration:none;line-height:1.4">← Dashboard</a>
  </div>
  <div id="msg-out" style="margin-top:10px;font-size:12px"></div>
</div>

<div class="card">
  <h2>Clientes registrados</h2>
  <table id="tbl-clientes">
    <thead><tr>
      <th>Cliente</th>
      <th>Tipo</th>
      <th>Contacto</th>
      <th style="text-align:right">Pedidos activos</th>
      <th style="text-align:right">Total pedidos</th>
      <th>Último pedido</th>
      <th></th>
    </tr></thead>
    <tbody><tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:20px">Cargando…</td></tr></tbody>
  </table>
</div>

<div class="card" id="card-detalle" style="display:none">
  <h2 id="detalle-titulo">Detalle cliente</h2>
  <div id="detalle-info"></div>
  <div class="actions-row">
    <button class="btn btn-prim" onclick="abrirModalPedido()">+ Nuevo pedido</button>
    <button class="btn btn-link" onclick="cerrarDetalle()">Cerrar</button>
  </div>
  <h2 style="margin-top:18px">Pedidos del cliente</h2>
  <table id="tbl-pedidos">
    <thead><tr>
      <th>ID</th>
      <th>Producto</th>
      <th style="text-align:right">Cant.</th>
      <th style="text-align:right">ml/u</th>
      <th>Fecha entrega</th>
      <th>Envase</th>
      <th>Estado</th>
      <th>Lote calendario</th>
      <th></th>
    </tr></thead>
    <tbody></tbody>
  </table>
</div>

<!-- Modal Nuevo Cliente -->
<div id="modal-cliente" class="modal-bg" onclick="if(event.target===this)cerrarModalCliente()">
  <div class="modal">
    <h2>+ Nuevo cliente B2B</h2>
    <label>ID (slug · sin espacios)</label>
    <input id="c-id" placeholder="kelly_guerra" style="text-transform:lowercase">
    <label>Nombre</label>
    <input id="c-nombre" placeholder="Kelly Guerra">
    <label>Tipo</label>
    <select id="c-tipo">
      <option value="B2B">B2B (cliente regular mayorista)</option>
      <option value="MAQUILA">Maquila (produce con nuestra fórmula, su marca)</option>
      <option value="INFLUENCER">Influencer (línea propia)</option>
      <option value="OTRO">Otro</option>
    </select>
    <label>Email contacto</label>
    <input id="c-email" type="email" placeholder="kelly@empresa.com">
    <label>Teléfono</label>
    <input id="c-telefono" placeholder="+57 ...">
    <label>Notas</label>
    <textarea id="c-notas" rows="2"></textarea>
    <!-- Sebastián 25-may-2026 PM · checkbox flujo unificado -->
    <div style="margin-top:14px;padding:12px 14px;background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#0f766e;font-weight:600;margin:0">
        <input type="checkbox" id="c-portal" style="width:auto;margin:0;cursor:pointer">
        🤝 Generar acceso al portal del cliente
      </label>
      <div style="font-size:11px;color:#475569;margin-top:6px;margin-left:24px">
        Crea credencial con password random · te muestro mensaje listo para mandar al cliente por WhatsApp/email.
      </div>
    </div>
    <div class="actions-row">
      <button class="btn btn-prim" onclick="guardarCliente()">💾 Guardar</button>
      <button class="btn btn-link" onclick="cerrarModalCliente()">Cancelar</button>
    </div>
  </div>
</div>

<!-- Modal Credencial generada · Sebastián 25-may-2026 PM -->
<div id="modal-cred" class="modal-bg" onclick="if(event.target===this)cerrarModalCred()">
  <div class="modal" style="max-width:540px">
    <h2 style="color:#0f766e">✓ Cliente creado · acceso portal generado</h2>
    <div style="background:#ecfeff;border:2px solid #0891b2;border-radius:10px;padding:14px;margin:14px 0">
      <div style="font-size:11px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:.5px">Email</div>
      <div id="cred-email-v" style="font-family:monospace;font-size:15px;font-weight:700;color:#0f172a;background:#fff;padding:6px 10px;border-radius:5px;border:1px solid #cbd5e1;margin-top:4px;cursor:pointer;user-select:all" onclick="copiarTxt(this)"></div>
      <div style="font-size:11px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:.5px;margin-top:10px">Contraseña (mostrada UNA vez)</div>
      <div id="cred-pass-v" style="font-family:monospace;font-size:15px;font-weight:700;color:#0f172a;background:#fff;padding:6px 10px;border-radius:5px;border:1px solid #cbd5e1;margin-top:4px;cursor:pointer;user-select:all" onclick="copiarTxt(this)"></div>
    </div>
    <div style="background:#fef3c7;border-left:3px solid #f59e0b;padding:10px 12px;border-radius:5px;font-size:11px;color:#92400e;margin-bottom:10px">
      ⚠ Copiá la contraseña ahora · al cerrar este modal no se vuelve a mostrar.
    </div>
    <label style="margin-top:8px">📝 Mensaje listo para enviar</label>
    <textarea id="cred-mensaje-v" rows="8" readonly style="font-family:monospace;font-size:12px;cursor:pointer;background:#f8fafc" onclick="this.select();copiarTxt(this)"></textarea>
    <div class="actions-row" style="flex-wrap:wrap;gap:8px">
      <button class="btn btn-prim" onclick="abrirWhatsApp()" style="background:#25d366">📱 Abrir WhatsApp</button>
      <button class="btn" onclick="abrirGmail()" style="background:#ea4335;color:#fff">📧 Abrir Gmail</button>
      <button class="btn btn-link" onclick="cerrarModalCred()">Cerrar</button>
    </div>
  </div>
</div>

<!-- Modal Nuevo Pedido -->
<div id="modal-pedido" class="modal-bg" onclick="if(event.target===this)cerrarModalPedido()">
  <div class="modal">
    <h2 id="modal-pedido-titulo">+ Nuevo pedido</h2>
    <label>Producto</label>
    <input id="p-producto" list="lista-productos" placeholder="LIMPIADOR FACIAL BHA 2%">
    <datalist id="lista-productos"></datalist>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
      <div><label>Unidades</label><input id="p-uds" type="number" min="1" value="100"></div>
      <div><label>ml por unidad</label><input id="p-ml" type="number" min="1" value="30" step="0.1"></div>
      <div><label>Fecha entrega</label><input id="p-fecha" type="date"></div>
    </div>
    <label>Envase (opcional · vacío usa default del producto)</label>
    <input id="p-envase" placeholder="ENV-500-FB" style="text-transform:uppercase">
    <label>Notas</label>
    <textarea id="p-notas" rows="2"></textarea>
    <div class="info">El pedido se va a integrar al calendario · si hay un lote del mismo producto ±10d se suman los kg; sino se crea un lote dedicado.</div>
    <div class="actions-row">
      <button class="btn btn-prim" onclick="guardarPedido()">💾 Crear pedido</button>
      <button class="btn btn-link" onclick="cerrarModalPedido()">Cancelar</button>
    </div>
  </div>
</div>

<script>
let CLIENTE_ACTUAL = null;
let CLIENTES = [];

async function cargarClientes() {
  const r = await fetch('/api/clientes-b2b?incluir_pedidos=1');
  const d = await r.json();
  CLIENTES = d.clientes || d.items || [];
  const tbody = document.querySelector('#tbl-clientes tbody');
  if (!CLIENTES.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:20px">Sin clientes · click "+ Nuevo cliente" o "📦 Migrar desde Maquila"</td></tr>';
    return;
  }
  tbody.innerHTML = '';
  CLIENTES.forEach(c => {
    const tr = document.createElement('tr');
    tr.className = 'row-cli';
    const ult = c.ultimo_pedido_fecha ? String(c.ultimo_pedido_fecha).slice(0, 10) : '—';
    const badge = '<span class="badge b-' + (c.tipo || 'B2B') + '">' + (c.tipo || 'B2B') + '</span>';
    const contacto = [c.email, c.telefono].filter(x => x).join(' · ') || '—';
    const pendientes = c.pedidos_pendientes || 0;
    const total = c.pedidos_total || 0;
    tr.innerHTML = '<td><strong>' + esc(c.cliente_nombre) + '</strong><br><span style="font-size:10px;color:#94a3b8;font-family:monospace">' + esc(c.cliente_id) + '</span></td>' +
      '<td>' + badge + '</td>' +
      '<td style="font-size:11px;color:#64748b">' + esc(contacto) + '</td>' +
      '<td style="text-align:right;font-weight:700;color:' + (pendientes > 0 ? '#7c3aed' : '#94a3b8') + '">' + pendientes + '</td>' +
      '<td style="text-align:right">' + total + '</td>' +
      '<td>' + ult + '</td>' +
      '<td><button class="btn btn-link" onclick="verDetalle(\\''+ c.cliente_id +'\\')">Ver</button></td>';
    tbody.appendChild(tr);
  });
  cargarProductos();
}

async function cargarProductos() {
  try {
    const r = await fetch('/api/admin/skus-huerfanos-top?limit=1');
    const d = await r.json();
    const dl = document.getElementById('lista-productos');
    if (dl && d.productos_disponibles) {
      dl.innerHTML = d.productos_disponibles.map(p => '<option value="' + esc(p) + '">').join('');
    }
  } catch (e) {}
}

async function verDetalle(cliente_id) {
  CLIENTE_ACTUAL = CLIENTES.find(c => c.cliente_id === cliente_id);
  if (!CLIENTE_ACTUAL) return;
  document.getElementById('detalle-titulo').textContent = '👤 ' + CLIENTE_ACTUAL.cliente_nombre;
  const contacto = [CLIENTE_ACTUAL.email, CLIENTE_ACTUAL.telefono].filter(x => x).join(' · ') || 'Sin contacto';
  document.getElementById('detalle-info').innerHTML =
    '<div><span class="badge b-' + (CLIENTE_ACTUAL.tipo || 'B2B') + '">' + (CLIENTE_ACTUAL.tipo || 'B2B') + '</span> · ' +
    '<code>' + esc(CLIENTE_ACTUAL.cliente_id) + '</code> · ' + esc(contacto) + '</div>';
  document.getElementById('card-detalle').style.display = 'block';
  // Cargar pedidos
  const r = await fetch('/api/pedidos-b2b?cliente_id=' + encodeURIComponent(cliente_id) + '&incluir_terminales=1');
  const d = await r.json();
  const tbody = document.querySelector('#tbl-pedidos tbody');
  const items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#94a3b8;padding:14px">Sin pedidos · click "+ Nuevo pedido"</td></tr>';
    return;
  }
  tbody.innerHTML = items.map(p => {
    const lote = p.lote_consolidado;
    const loteHtml = lote ? ('Lote #' + lote.lote_id + '<br><span style="font-size:10px;color:#64748b">' + lote.fecha_lote + ' · ' + lote.modo + '</span>') : '<span style="color:#94a3b8">no integrado</span>';
    return '<tr>' +
      '<td>' + p.id + '</td>' +
      '<td><strong>' + esc(p.producto_nombre) + '</strong></td>' +
      '<td style="text-align:right">' + p.cantidad_uds + '</td>' +
      '<td style="text-align:right">' + (p.ml_unidad || 30) + '</td>' +
      '<td>' + (p.fecha_estimada || '—') + '</td>' +
      '<td><code style="font-size:10px">' + (p.envase_codigo || '—') + '</code></td>' +
      '<td><span class="badge b-' + (p.estado === 'cancelado' ? 'OTRO' : 'B2B') + '">' + p.estado + '</span></td>' +
      '<td style="font-size:11px">' + loteHtml + '</td>' +
      '<td>' + (p.estado !== 'cancelado' ? '<button class="btn btn-link" onclick="cancelarPedido(' + p.id + ')">✕</button>' : '') + '</td>' +
      '</tr>';
  }).join('');
  // Pre-llenar fecha por defecto en pedidos
  const hoy = new Date(); hoy.setDate(hoy.getDate() + 14);
  document.getElementById('p-fecha').value = hoy.toISOString().slice(0, 10);
}

function cerrarDetalle() {
  document.getElementById('card-detalle').style.display = 'none';
  CLIENTE_ACTUAL = null;
}

function abrirModalCliente() { document.getElementById('modal-cliente').style.display = 'flex'; }
function cerrarModalCliente() { document.getElementById('modal-cliente').style.display = 'none'; }
function abrirModalPedido() {
  if (!CLIENTE_ACTUAL) { alert('Seleccioná un cliente primero'); return; }
  document.getElementById('modal-pedido-titulo').textContent = '+ Nuevo pedido para ' + CLIENTE_ACTUAL.cliente_nombre;
  document.getElementById('modal-pedido').style.display = 'flex';
}
function cerrarModalPedido() { document.getElementById('modal-pedido').style.display = 'none'; }

async function guardarCliente() {
  const portalCheck = document.getElementById('c-portal');
  const generarPortal = portalCheck ? portalCheck.checked : false;
  const body = {
    cliente_id: (document.getElementById('c-id').value || '').trim().toLowerCase(),
    cliente_nombre: document.getElementById('c-nombre').value.trim(),
    email: document.getElementById('c-email').value.trim(),
    telefono: document.getElementById('c-telefono').value.trim(),
    tipo: document.getElementById('c-tipo').value,
    notas: document.getElementById('c-notas').value.trim(),
    generar_credencial_portal: generarPortal,
  };
  if (!body.cliente_id || !body.cliente_nombre) { alert('ID y nombre requeridos'); return; }
  if (generarPortal && (!body.email || body.email.indexOf('@') < 0)) {
    alert('Email válido es requerido si querés generar acceso al portal');
    return;
  }
  const r = await fetch('/api/clientes-b2b', {
    method:'POST',
    headers:{'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokPlan || '')},
    body: JSON.stringify(body)
  });
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
  cerrarModalCliente();
  ['c-id','c-nombre','c-email','c-telefono','c-notas'].forEach(id => document.getElementById(id).value = '');
  if (portalCheck) portalCheck.checked = false;
  await cargarClientes();
  showMsg('✓ Cliente creado · ' + body.cliente_nombre, '#15803d');
  // Si se generó credencial portal, mostrar modal con email + password + mensaje
  if (d.portal_credencial && d.portal_credencial.password) {
    window._credMensajeActual = d.portal_credencial.mensaje || '';
    window._credEmailActual = d.portal_credencial.email || '';
    window._credTelActual = body.telefono || '';
    document.getElementById('cred-email-v').textContent = d.portal_credencial.email || '';
    document.getElementById('cred-pass-v').textContent = d.portal_credencial.password || '';
    document.getElementById('cred-mensaje-v').value = d.portal_credencial.mensaje || '';
    document.getElementById('modal-cred').classList.add('show');
  } else if (d.portal_credencial && d.portal_credencial.error) {
    alert('Cliente OK pero falló credencial portal: ' + d.portal_credencial.error);
  }
}

// CSRF · token para los POSTs a /api/clientes-b2b
window._csrfTokPlan = '';
fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d && d.csrf_token) window._csrfTokPlan = d.csrf_token; })
  .catch(() => {});

function cerrarModalCred(){
  document.getElementById('modal-cred').classList.remove('show');
}
function copiarTxt(el){
  const t = el.value !== undefined ? el.value : el.textContent;
  if(navigator.clipboard){
    navigator.clipboard.writeText(t).then(function(){
      const orig = el.style.background;
      el.style.background = '#dcfce7';
      setTimeout(function(){ el.style.background = orig; }, 600);
    });
  } else {
    if(el.select) el.select();
    try{ document.execCommand('copy'); }catch(_){}
  }
}
function abrirWhatsApp(){
  const msg = encodeURIComponent(window._credMensajeActual || '');
  const tel = (window._credTelActual || '').replace(/\\D/g, '');
  // Si tiene teléfono, abrir chat directo · sino, abrir wa.me sin destinatario
  const url = tel ? ('https://wa.me/' + tel + '?text=' + msg) : ('https://wa.me/?text=' + msg);
  window.open(url, '_blank');
}
function abrirGmail(){
  const subject = encodeURIComponent('Acceso Portal Espagiria');
  const body = encodeURIComponent(window._credMensajeActual || '');
  const to = encodeURIComponent(window._credEmailActual || '');
  const url = 'https://mail.google.com/mail/?view=cm&fs=1&to=' + to + '&su=' + subject + '&body=' + body;
  window.open(url, '_blank');
}

async function guardarPedido() {
  if (!CLIENTE_ACTUAL) return;
  const body = {
    cliente_id: CLIENTE_ACTUAL.cliente_id,
    cliente_nombre: CLIENTE_ACTUAL.cliente_nombre,
    producto_nombre: document.getElementById('p-producto').value.trim(),
    cantidad_uds: parseInt(document.getElementById('p-uds').value) || 0,
    ml_unidad: parseFloat(document.getElementById('p-ml').value) || 30,
    fecha_estimada: document.getElementById('p-fecha').value,
    envase_codigo: (document.getElementById('p-envase').value || '').trim().toUpperCase(),
    notas: document.getElementById('p-notas').value.trim(),
  };
  if (!body.producto_nombre || !body.cantidad_uds) { alert('Producto y cantidad requeridos'); return; }
  const r = await fetch('/api/pedidos-b2b', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
  cerrarModalPedido();
  document.getElementById('p-producto').value = '';
  document.getElementById('p-envase').value = '';
  document.getElementById('p-notas').value = '';
  const inteMsg = d.integracion_plan ? ' · Integrado al lote #' + d.integracion_plan.lote_id : '';
  showMsg('✓ Pedido #' + d.id + ' creado · ' + body.cantidad_uds + ' uds · ' + body.producto_nombre + inteMsg, '#15803d');
  await verDetalle(CLIENTE_ACTUAL.cliente_id);
  await cargarClientes();
}

async function cancelarPedido(pid) {
  if (!confirm('¿Cancelar pedido #' + pid + '?')) return;
  const r = await fetch('/api/pedidos-b2b/' + pid, { method:'DELETE' });
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
  showMsg('✓ Pedido cancelado · revertido del calendario', '#15803d');
  if (CLIENTE_ACTUAL) await verDetalle(CLIENTE_ACTUAL.cliente_id);
  await cargarClientes();
}

async function migrarMaquila() {
  if (!confirm('¿Traer clientes desde la tabla legacy clientes_maquila al maestro B2B?\\n\\nLos clientes existentes no se sobrescriben.')) return;
  const r = await fetch('/api/admin/clientes-b2b/migrar-desde-maquila', { method:'POST' });
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
  showMsg('✓ Migrados ' + d.creados + ' · ya existían ' + d.ya_existen + ' · errores ' + d.errores.length, '#15803d');
  await cargarClientes();
}

function showMsg(text, color) {
  const el = document.getElementById('msg-out');
  el.innerHTML = '<span style="color:' + color + ';font-weight:700">' + text + '</span>';
  setTimeout(() => { el.innerHTML = ''; }, 6000);
}

function esc(s) {
  const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML;
}

cargarClientes();
</script>
</body></html>"""


@bp.route("/admin/fusionar-formulas-nf", methods=["GET", "POST"])
def admin_fusionar_formulas_nf():
    """Sebastián 24-may noche: 'NF significa nueva formula · le pertenece
    al producto que ya está'. Es decir, EMULSION HIDRATANTE ILUMINADORA NF
    es la nueva fórmula del producto EMULSION HIDRATANTE ILUMINADORA.

    Esta página detecta parejas (X, X NF), muestra valores actuales y
    permite hacer el merge:
      - La fórmula vieja (X) se marca activo=0 (preserva histórico)
      - La fórmula NF se renombra a X (sin sufijo)
      - lote_size_kg de la NF se completa con el de la vieja si la NF
        está en 0.1 (absurdo) y la vieja tiene valor realista
      - formula_items de la vieja se mantienen (por si auditoría histórica)
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin/compras</h2></body></html>", 403
    conn = get_db(); cur = conn.cursor()

    # Detectar parejas NF
    nf_rows = cur.execute(
        """SELECT producto_nombre, COALESCE(lote_size_kg, 0), COALESCE(activo, 1)
           FROM formula_headers
           WHERE UPPER(producto_nombre) LIKE '% NF'
              OR UPPER(producto_nombre) LIKE '%NUEVA FORMULA%'
              OR UPPER(producto_nombre) LIKE '%NUEVA FÓRMULA%'
           ORDER BY producto_nombre"""
    ).fetchall()

    parejas = []
    for nf_nombre, nf_lote, nf_act in nf_rows:
        # Calcular nombre base (quitar sufijo NF)
        base = nf_nombre
        for sfx in [' NF', ' FORMULA NUEVA', ' FÓRMULA NUEVA', ' NUEVA FORMULA', ' NUEVA FÓRMULA']:
            if base.upper().endswith(sfx):
                base = base[:-len(sfx)].rstrip()
                break
        if base == nf_nombre:
            continue  # no se pudo extraer base
        # Buscar la vieja
        old_row = cur.execute(
            "SELECT producto_nombre, COALESCE(lote_size_kg, 0), COALESCE(activo, 1) "
            "FROM formula_headers WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))",
            (base,),
        ).fetchone()
        # Contar lotes en calendario con cada nombre
        cnt_nf = cur.execute(
            "SELECT COUNT(*) FROM produccion_programada "
            "WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?)) "
            "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')",
            (nf_nombre,),
        ).fetchone()[0] or 0
        cnt_old = cur.execute(
            "SELECT COUNT(*) FROM produccion_programada "
            "WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?)) "
            "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')",
            (base,),
        ).fetchone()[0] or 0
        parejas.append({
            'nf': nf_nombre, 'nf_lote': nf_lote, 'nf_act': bool(nf_act),
            'base': base,
            'old_existe': bool(old_row),
            'old_lote': float(old_row[1]) if old_row else 0,
            'old_act': bool(old_row[2]) if old_row else False,
            'cnt_nf': cnt_nf,
            'cnt_old': cnt_old,
        })

    if request.method == 'POST':
        accion = request.form.get('accion')
        nf_target = request.form.get('nf_target', '').strip()
        if accion != 'fusionar' or not nf_target:
            return "<html><body><h2>Acción inválida</h2></body></html>", 400
        pareja = next((p for p in parejas if p['nf'] == nf_target), None)
        if not pareja:
            return f"<html><body><h2>Pareja no encontrada: {nf_target}</h2></body></html>", 404
        nf = pareja['nf']
        base = pareja['base']
        try:
            # 1. Si NF tiene lote_size absurdo (< 1) y vieja tiene valor → copiar
            if pareja['nf_lote'] < 1 and pareja['old_existe'] and pareja['old_lote'] >= 1:
                cur.execute(
                    "UPDATE formula_headers SET lote_size_kg = ? "
                    "WHERE producto_nombre = ?",
                    (pareja['old_lote'], nf),
                )
            # 2. Marcar la vieja como inactiva (preserva histórico)
            if pareja['old_existe']:
                cur.execute(
                    "UPDATE formula_headers SET activo = 0 WHERE producto_nombre = ?",
                    (base,),
                )
                # Renombrar para no chocar con la NF cuando renombremos
                cur.execute(
                    "UPDATE formula_headers SET producto_nombre = ? "
                    "WHERE producto_nombre = ?",
                    (base + ' [ANTIGUA]', base),
                )
                cur.execute(
                    "UPDATE formula_items SET producto_nombre = ? "
                    "WHERE producto_nombre = ?",
                    (base + ' [ANTIGUA]', base),
                )
            # 3. Renombrar NF al nombre base (sin sufijo)
            cur.execute(
                "UPDATE formula_headers SET producto_nombre = ? "
                "WHERE producto_nombre = ?",
                (base, nf),
            )
            cur.execute(
                "UPDATE formula_items SET producto_nombre = ? "
                "WHERE producto_nombre = ?",
                (base, nf),
            )
            audit_log(cur, usuario=user, accion='FUSIONAR_FORMULA_NF',
                      tabla='formula_headers', registro_id=base,
                      despues={'nf_original': nf, 'base': base,
                                'old_marcada_inactiva': pareja['old_existe'],
                                'lote_size_aplicado': pareja['nf_lote'] if pareja['nf_lote'] >= 1 else pareja['old_lote']})
            conn.commit()
            return f"<html><body style='font-family:system-ui;padding:30px;background:#f8fafc'><h1 style='color:#15803d'>✓ Fusionado: {base}</h1><p>La fórmula NUEVA ahora se llama <code>{base}</code> y se usa cuando una producción matchee. La vieja quedó como <code>{base} [ANTIGUA]</code> con activo=0 (preserva histórico).</p><a href='/admin/fusionar-formulas-nf' style='background:#7c3aed;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:700'>← Ver más parejas</a></body></html>"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return f"<html><body style='font-family:system-ui;padding:30px'><h1 style='color:#dc2626'>Error</h1><pre>{str(e)[:500]}</pre></body></html>", 500

    # Render preview
    rows = ''
    for p in parejas:
        nf_warn = '⚠' if p['nf_lote'] < 1 else '✓'
        old_warn = '⚠' if p['old_existe'] and p['old_lote'] < 1 else ('—' if not p['old_existe'] else '✓')
        bg = '#fef3c7' if p['nf_lote'] < 1 else '#f8fafc'
        boton = f'<form method="POST" style="margin:0" onsubmit="return confirm(\'¿Fusionar {p["nf"]} → {p["base"]}?\\n\\nVieja se marca [ANTIGUA] inactiva. NF se renombra al nombre base.\');"><input type="hidden" name="accion" value="fusionar"><input type="hidden" name="nf_target" value="{p["nf"]}"><button type="submit" style="background:#7c3aed;color:#fff;border:none;padding:6px 12px;border-radius:5px;font-weight:700;cursor:pointer">🔄 Fusionar</button></form>'
        rows += f'<tr style="background:{bg}">'\
                f'<td style="padding:10px">{p["nf"]}</td>'\
                f'<td style="padding:10px;text-align:right">{nf_warn} {p["nf_lote"]:.2f} kg</td>'\
                f'<td style="padding:10px;text-align:right">{p["cnt_nf"]}</td>'\
                f'<td style="padding:10px"><strong style="color:#0f766e">{p["base"]}</strong></td>'\
                f'<td style="padding:10px;text-align:right">{old_warn} {("%.2f kg" % p["old_lote"]) if p["old_existe"] else "—"}</td>'\
                f'<td style="padding:10px;text-align:right">{p["cnt_old"]}</td>'\
                f'<td style="padding:10px;text-align:center">{boton}</td>'\
                f'</tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Fusionar fórmulas NF</title>
<style>
  body{{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:30px}}
  .card{{max-width:1300px;margin:0 auto;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  h1{{color:#1e293b;margin:0 0 10px}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}}
  th{{background:#f1f5f9;padding:10px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569}}
  td{{border-bottom:1px solid #e2e8f0}}
  .info{{background:#dbeafe;border-left:5px solid #1e40af;padding:14px 18px;border-radius:8px;color:#1e3a8a;font-size:13px;margin:14px 0}}
</style></head><body>

<div class="card">
  <h1>🔄 Fusionar fórmulas NF (Nueva Fórmula)</h1>
  <p style="color:#475569">Sebastián: 'NF significa nueva formula · le pertenece al producto que ya está'. Esta herramienta toma cada pareja (producto, producto NF) y reemplaza la fórmula vieja con la NF.</p>

  <div class="info">
    <strong>Qué hace el botón Fusionar:</strong><br>
    1. Si la NF tiene lote_size &lt; 1 (absurdo) y la vieja tiene valor real → copia lote_size de la vieja a la NF.<br>
    2. Marca la fórmula vieja como inactiva (activo=0) y la renombra a <code>X [ANTIGUA]</code> (preserva histórico).<br>
    3. Renombra la NF al nombre base (sin sufijo " NF").<br>
    4. A partir de ahí, las producciones del calendario con el nombre base usan la fórmula nueva.<br>
    Operación auditada en audit_log.
  </div>

  <table>
    <thead><tr>
      <th>Fórmula NF</th>
      <th style="text-align:right">lote_size NF</th>
      <th style="text-align:right">Lotes</th>
      <th>→ Producto base</th>
      <th style="text-align:right">lote_size vieja</th>
      <th style="text-align:right">Lotes</th>
      <th></th>
    </tr></thead>
    <tbody>{rows or '<tr><td colspan=7 style="padding:20px;text-align:center;color:#94a3b8">Ninguna fórmula NF detectada</td></tr>'}</tbody>
  </table>

  <p style="margin-top:18px"><a href="/admin/diag-formulas-sospechosas" style="color:#7c3aed">← Diag fórmulas</a> · <a href="/" style="color:#475569">Dashboard</a></p>
</div></body></html>"""


@bp.route("/admin/diag-formulas-sospechosas", methods=["GET"])
def admin_diag_formulas_sospechosas():
    """Sebastián 24-may noche · el match es 100% pero consumo subestima.
    Causa probable: fórmulas con valores sospechosos. Esta página detecta:

    - lote_size_kg = 0 o < 1 (absurdo · cálculo falla)
    - cantidad_g_por_lote = 0 Y porcentaje = 0 (item silenciado)
    - cantidad_g_por_lote MUY bajo vs porcentaje × lote_size declarado
      (típico bug: 0.6g cuando debería ser 6g · 10× error)

    Muestra todo de una para arreglar con UPDATEs específicos.
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin/compras</h2></body></html>", 403

    conn = get_db(); cur = conn.cursor()

    # 1. Headers con lote_size_kg sospechoso
    headers_mal = cur.execute(
        """SELECT producto_nombre, COALESCE(lote_size_kg, 0), COALESCE(activo, 1)
           FROM formula_headers
           WHERE COALESCE(activo, 1) = 1
             AND (lote_size_kg IS NULL OR lote_size_kg < 1)
           ORDER BY producto_nombre"""
    ).fetchall()

    # 2. Items con AMBOS valores en 0 (no suma nada)
    items_zero = cur.execute(
        """SELECT fi.producto_nombre, fi.material_id, fi.material_nombre,
                  COALESCE(fi.porcentaje, 0), COALESCE(fi.cantidad_g_por_lote, 0),
                  COALESCE(fh.lote_size_kg, 0)
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo, 1) = 1
             AND COALESCE(fi.porcentaje, 0) = 0
             AND COALESCE(fi.cantidad_g_por_lote, 0) = 0
           ORDER BY fi.producto_nombre, fi.material_id"""
    ).fetchall()

    # 3. Items donde g_por_lote diverge del cálculo (% × lote_size × 10)
    # Detecta sub-estimación 10x o 100x típica de bug de seed
    items_diverge = []
    for r in cur.execute(
        """SELECT fi.producto_nombre, fi.material_id, fi.material_nombre,
                  COALESCE(fi.porcentaje, 0) AS pct,
                  COALESCE(fi.cantidad_g_por_lote, 0) AS g,
                  COALESCE(fh.lote_size_kg, 0) AS lk
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE COALESCE(fh.activo, 1) = 1
             AND COALESCE(fi.porcentaje, 0) > 0
             AND COALESCE(fi.cantidad_g_por_lote, 0) > 0
             AND COALESCE(fh.lote_size_kg, 0) > 0"""
    ).fetchall():
        pnom, mid, mnom, pct, g, lk = r
        esperado = (pct / 100.0) * lk * 1000.0  # gramos según % × lote
        if esperado > 0.01:
            ratio = g / esperado
            # Considerar sospechoso si <0.5x o >2x del esperado
            if ratio < 0.5 or ratio > 2.0:
                items_diverge.append({
                    'producto': pnom, 'mid': mid, 'mnom': mnom,
                    'pct': pct, 'g': g, 'lk': lk,
                    'esperado': esperado, 'ratio': ratio,
                })
    items_diverge.sort(key=lambda x: abs(1 - x['ratio']), reverse=True)

    # Render
    headers_rows = ''
    for r in headers_mal[:60]:
        headers_rows += f'<tr style="background:#fee2e2"><td style="padding:6px 10px">{r[0]}</td><td style="padding:6px 10px;text-align:right;font-family:monospace;color:#991b1b;font-weight:700">{r[1]:.3f} kg</td></tr>'

    items_zero_rows = ''
    for r in items_zero[:80]:
        items_zero_rows += f'<tr style="background:#fef3c7"><td style="padding:5px 10px">{r[0]}</td><td style="padding:5px 10px;font-family:monospace">{r[1]}</td><td style="padding:5px 10px">{r[2][:40]}</td><td style="padding:5px 10px;text-align:right;color:#92400e">0%</td><td style="padding:5px 10px;text-align:right;color:#92400e">0 g</td><td style="padding:5px 10px;text-align:right">{r[5]:.1f} kg</td></tr>'
    if len(items_zero) > 80:
        items_zero_rows += f'<tr><td colspan="6" style="padding:8px;text-align:center;color:#94a3b8">… y {len(items_zero) - 80} items más</td></tr>'

    diverge_rows = ''
    for d in items_diverge[:80]:
        color = '#dc2626' if d['ratio'] < 0.5 else '#ea580c'
        bg = '#fee2e2' if d['ratio'] < 0.5 else '#fff7ed'
        diverge_rows += f'<tr style="background:{bg}"><td style="padding:5px 10px">{d["producto"]}</td><td style="padding:5px 10px;font-family:monospace">{d["mid"]}</td><td style="padding:5px 10px">{d["mnom"][:35]}</td><td style="padding:5px 10px;text-align:right">{d["pct"]:.3f}%</td><td style="padding:5px 10px;text-align:right">{d["lk"]:.1f}kg</td><td style="padding:5px 10px;text-align:right;color:#1e293b">{d["g"]:.2f} g</td><td style="padding:5px 10px;text-align:right;color:#0f766e">{d["esperado"]:.2f} g</td><td style="padding:5px 10px;text-align:right;font-weight:700;color:{color}">{d["ratio"]:.2f}×</td></tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Diag fórmulas sospechosas</title>
<style>
  body{{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:30px}}
  .card{{max-width:1400px;margin:0 auto 14px;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  h1{{color:#1e293b;margin:0 0 8px;font-size:22px}}
  h2{{color:#dc2626;margin:18px 0 12px;font-size:16px;border-bottom:2px solid #fbbf24;padding-bottom:6px}}
  .kpi{{display:inline-block;padding:14px 22px;background:#fee2e2;border:1px solid #dc2626;border-radius:8px;margin:4px;text-align:center;min-width:160px}}
  .kpi-val{{font-size:24px;font-weight:800;color:#991b1b}}
  .kpi-lbl{{font-size:10px;color:#64748b;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
  th{{background:#f1f5f9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569}}
  td{{border-bottom:1px solid #f1f5f9}}
  a{{color:#7c3aed;font-weight:700;text-decoration:none;display:inline-block;padding:8px 14px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin:6px 6px 0 0}}
</style></head><body>

<div class="card">
  <h1>🐛 Diagnóstico de fórmulas sospechosas</h1>
  <p style="color:#475569;font-size:13px">Sebastián: 'la lógica está bien pero no muestra la realidad'. Esta página detecta dónde están los datos mal cargados que hacen que el consumo proyectado salga subestimado.</p>
  <div>
    <a href="/admin/diag-flujo-abast">← Diag flujo</a>
    <a href="/admin/llenar-calendario">📅 Llenar calendario</a>
    <a href="/admin/limpiar-sols-ocs">🧹 Limpiar SOLs/OCs</a>
    <a href="/">← Dashboard</a>
  </div>
</div>

<div class="card">
  <h2>🔴 1. Fórmulas con lote_size_kg ausente o &lt; 1</h2>
  <p>Si el lote estándar es 0 o muy chico, el cálculo gramos = g_por_lote × (cant_kg/lote_size) se rompe o subestima.</p>
  <div class="kpi"><div class="kpi-val">{len(headers_mal)}</div><div class="kpi-lbl">Fórmulas con lote_size mal</div></div>
  <table>
    <thead><tr><th>Producto</th><th style="text-align:right">lote_size_kg</th></tr></thead>
    <tbody>{headers_rows or '<tr><td colspan=2 style="padding:14px;text-align:center;color:#15803d">✓ Ningún lote_size sospechoso</td></tr>'}</tbody>
  </table>
</div>

<div class="card">
  <h2>🟡 2. Items con % = 0 Y cantidad_g_por_lote = 0</h2>
  <p>Estos items aportan 0g al consumo silenciosamente. Hay que llenar al menos uno de los dos campos en formula_items.</p>
  <div class="kpi"><div class="kpi-val">{len(items_zero)}</div><div class="kpi-lbl">Items en cero</div></div>
  <table>
    <thead><tr><th>Producto</th><th>MP</th><th>Nombre MP</th><th style="text-align:right">%</th><th style="text-align:right">g/lote</th><th style="text-align:right">lote_size</th></tr></thead>
    <tbody>{items_zero_rows or '<tr><td colspan=6 style="padding:14px;text-align:center;color:#15803d">✓ Ningún item en cero</td></tr>'}</tbody>
  </table>
</div>

<div class="card">
  <h2>🟠 3. Items con divergencia % vs g/lote (subestimados o sobreestimados)</h2>
  <p>Comparamos el valor declarado `cantidad_g_por_lote` contra el calculado (`% × lote_size × 1000`). Si el ratio difiere significativamente, hay typo en el seed (e.g., 0.6 cuando debería ser 6.0 · 10× subestimado).</p>
  <p style="color:#475569;font-size:11px">⚠ El cálculo usa <strong>cantidad_g_por_lote primero</strong> si > 0. Si ese valor está mal, el consumo proyectado queda mal.</p>
  <div class="kpi"><div class="kpi-val">{len(items_diverge)}</div><div class="kpi-lbl">Items divergentes &gt;2× o &lt;0.5×</div></div>
  <table>
    <thead><tr><th>Producto</th><th>MP</th><th>Nombre</th><th style="text-align:right">%</th><th style="text-align:right">lote_kg</th><th style="text-align:right">g/lote BD</th><th style="text-align:right">g/lote calc</th><th style="text-align:right">Ratio</th></tr></thead>
    <tbody>{diverge_rows or '<tr><td colspan=8 style="padding:14px;text-align:center;color:#15803d">✓ Todos los items son consistentes</td></tr>'}</tbody>
  </table>
  <p style="color:#475569;font-size:11px;margin-top:10px">📌 Si ratio &lt; 0.5× (rojo): cantidad_g_por_lote subestima · el sistema mostrará consumo bajo.<br>📌 Si ratio &gt; 2× (naranja): cantidad_g_por_lote sobreestima · el sistema mostrará consumo alto.</p>
</div>

</body></html>"""


@bp.route("/admin/diag-flujo-abast", methods=["GET"])
def admin_diag_flujo_abast():
    """Página standalone · auditoría del flujo de Abastecimiento.

    Sebastián 24-may-2026 noche: 'la logica es, si esta tomando las
    programaciones del calendario seria lo primero, segundo enlaza cada
    produccion a la formula adecuada, tercero suma adecuadamente cada
    produccion con sus materias primas, esta tomando todo bien?'

    Muestra los 3 pasos con datos REALES:
    Paso 1: Producciones del calendario (lista de 137 lotes futuros)
    Paso 2: Match producto↔fórmula (cuántos sí matchean, cuáles NO)
    Paso 3: Top 30 MPs con sus lotes contribuyentes
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin/compras</h2></body></html>", 403

    conn = get_db(); cur = conn.cursor()
    from datetime import date as _d, timedelta as _td
    hoy = _d.today()
    hoy_iso = hoy.isoformat()
    cutoff = (hoy + _td(days=365)).isoformat()

    def _norm(s):
        return ' '.join((s or '').strip().upper().split())

    # PASO 1: Producciones del calendario (futuras, no canceladas)
    prods = cur.execute(
        """SELECT id, producto, fecha_programada,
                  COALESCE(cantidad_kg, 0),
                  COALESCE(lotes, 1),
                  COALESCE(estado, ''),
                  COALESCE(origen, '')
           FROM produccion_programada
           WHERE LOWER(COALESCE(estado,'')) NOT IN
                 ('cancelado','completado','esperando_recurso')
             AND COALESCE(inventario_descontado_at,'') = ''
             AND fecha_programada >= ? AND fecha_programada <= ?
           ORDER BY fecha_programada ASC""",
        (hoy_iso, cutoff),
    ).fetchall()

    # PASO 2: Cargar fórmulas + lote_size con normalización
    formulas_dict = {}  # _norm(producto) -> [items]
    lote_size_dict = {}  # _norm(producto) -> lote_size_kg
    productos_en_formula = set()  # nombres canónicos en formula_headers
    for r in cur.execute(
        """SELECT fi.producto_nombre, fi.material_id, fi.material_nombre,
                  COALESCE(fi.porcentaje, 0),
                  COALESCE(fi.cantidad_g_por_lote, 0),
                  COALESCE(fh.lote_size_kg, 0)
           FROM formula_items fi
           JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
           WHERE fi.material_id IS NOT NULL AND TRIM(fi.material_id) != ''
             AND COALESCE(fh.activo, 1) = 1"""
    ).fetchall():
        k = _norm(r[0])
        productos_en_formula.add(r[0])
        formulas_dict.setdefault(k, []).append({
            'material_id': str(r[1] or '').strip().upper(),
            'material_nombre': r[2] or '',
            'pct': float(r[3] or 0),
            'g_por_lote': float(r[4] or 0),
        })
        if k not in lote_size_dict:
            lote_size_dict[k] = float(r[5] or 0)

    # PASO 3: Loop producciones · contar match/sin-match + sumar consumo
    lotes_con_formula = []
    lotes_sin_formula = []
    consumo_por_mp = {}  # codigo_mp -> {'nombre': X, 'total_g': Y, 'lotes': [...]}
    for pid, prod, fecha, ckg, lt, est, ori in prods:
        prod_norm = _norm(prod)
        items = formulas_dict.get(prod_norm)
        lote_size = lote_size_dict.get(prod_norm, 0)
        cant_kg = float(ckg or 0) or (int(lt or 1) * float(lote_size or 0))
        if not items:
            lotes_sin_formula.append({
                'id': pid, 'producto': prod, 'fecha': (fecha or '')[:10],
                'cant_kg': cant_kg, 'estado': est, 'origen': ori,
            })
            continue
        lotes_con_formula.append({
            'id': pid, 'producto': prod, 'fecha': (fecha or '')[:10],
            'cant_kg': cant_kg, 'estado': est, 'origen': ori,
            'n_mps': len(items),
        })
        if cant_kg <= 0:
            continue
        for it in items:
            if it['g_por_lote'] > 0 and lote_size > 0:
                g = it['g_por_lote'] * (cant_kg / lote_size)
            elif it['pct'] > 0:
                g = (it['pct'] / 100.0) * cant_kg * 1000.0
            else:
                continue
            mid = it['material_id']
            d = consumo_por_mp.setdefault(mid, {
                'nombre': it['material_nombre'], 'total_g': 0,
                'lotes': [], 'n_lotes': 0,
            })
            d['total_g'] += g
            d['n_lotes'] += 1
            if len(d['lotes']) < 10:
                d['lotes'].append({
                    'producto': prod,
                    'fecha': (fecha or '')[:10],
                    'cant_kg': cant_kg,
                    'gramos': round(g, 2),
                })

    # Ordenar MPs por total descendente
    mps_sorted = sorted(consumo_por_mp.items(), key=lambda x: -x[1]['total_g'])

    # Render HTML
    n_prods = len(prods)
    n_match = len(lotes_con_formula)
    n_huerf = len(lotes_sin_formula)
    pct_match = (100 * n_match / n_prods) if n_prods else 0
    n_mps_total = len(consumo_por_mp)

    paso1_rows = ''
    for p in prods[:20]:
        paso1_rows += f'<tr><td style="padding:4px 8px;font-family:monospace">{p[0]}</td><td style="padding:4px 8px">{p[1]}</td><td style="padding:4px 8px">{(p[2] or "")[:10]}</td><td style="padding:4px 8px;text-align:right">{p[3]:.1f} kg</td><td style="padding:4px 8px">{p[6]}</td></tr>'
    if n_prods > 20:
        paso1_rows += f'<tr><td colspan="5" style="padding:6px;text-align:center;color:#94a3b8">… y {n_prods - 20} producciones más</td></tr>'

    paso2_huerf_rows = ''
    huerfanos_unicos = sorted({l['producto'] for l in lotes_sin_formula})
    for p in huerfanos_unicos[:30]:
        n_l = sum(1 for l in lotes_sin_formula if l['producto'] == p)
        paso2_huerf_rows += f'<tr style="background:#fee2e2"><td style="padding:6px 10px;color:#991b1b">⚠ {p}</td><td style="padding:6px 10px;text-align:right;font-weight:700">{n_l}</td></tr>'
    if len(huerfanos_unicos) > 30:
        paso2_huerf_rows += f'<tr><td colspan="2" style="padding:6px;text-align:center;color:#94a3b8">… y {len(huerfanos_unicos) - 30} productos más</td></tr>'

    paso3_rows = ''
    for mid, d in mps_sorted[:30]:
        lotes_str = ' · '.join(f"{l['producto'][:30]} ({l['fecha'][-5:]}, {l['gramos']:.1f}g)" for l in d['lotes'][:3])
        if d['n_lotes'] > 3:
            lotes_str += f' … +{d["n_lotes"]-3} más'
        paso3_rows += f'<tr><td style="padding:6px 10px;font-family:monospace;font-weight:700">{mid}</td><td style="padding:6px 10px">{d["nombre"][:40]}</td><td style="padding:6px 10px;text-align:right;font-weight:700">{d["total_g"]:.1f} g</td><td style="padding:6px 10px;text-align:right">{d["n_lotes"]}</td><td style="padding:4px 8px;font-size:10px;color:#64748b">{lotes_str}</td></tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Diag flujo Abastecimiento</title>
<style>
  body{{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:30px}}
  .card{{max-width:1300px;margin:0 auto;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.08);margin-bottom:14px}}
  h1{{color:#1e293b;margin:0 0 8px;font-size:22px}}
  h2{{color:#0f766e;margin:18px 0 12px;font-size:16px;border-bottom:2px solid #0f766e;padding-bottom:6px}}
  .kpi{{display:inline-block;padding:14px 22px;background:#f0fdf4;border:1px solid #16a34a;border-radius:8px;margin:4px;text-align:center;min-width:160px}}
  .kpi-val{{font-size:24px;font-weight:800;color:#15803d}}
  .kpi-lbl{{font-size:10px;color:#64748b;text-transform:uppercase}}
  .kpi-warn{{background:#fef3c7;border-color:#f59e0b}}
  .kpi-warn .kpi-val{{color:#92400e}}
  .kpi-error{{background:#fee2e2;border-color:#dc2626}}
  .kpi-error .kpi-val{{color:#991b1b}}
  table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
  th{{background:#f1f5f9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569}}
  td{{border-bottom:1px solid #f1f5f9}}
  a{{color:#7c3aed;font-weight:700;text-decoration:none;display:inline-block;padding:8px 14px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin:6px 6px 0 0}}
  .alert{{background:#fef3c7;border-left:5px solid #f59e0b;padding:14px 18px;border-radius:8px;margin:12px 0;color:#92400e}}
  .alert-bad{{background:#fee2e2;border-left-color:#dc2626;color:#991b1b}}
</style></head><body>

<div class="card">
  <h1>🔍 Auditoría del flujo de Abastecimiento</h1>
  <p style="color:#475569;font-size:13px">Verificación paso a paso desde el calendario hasta la suma final por MP. Si los números no cuadran, acá vas a ver dónde se pierde la información.</p>
  <div>
    <a href="/admin/llenar-calendario">📅 Llenar calendario</a>
    <a href="/admin/limpiar-sols-ocs">🧹 Limpiar SOLs/OCs</a>
    <a href="/">← Dashboard</a>
  </div>
</div>

<div class="card">
  <h2>1️⃣ Producciones del Calendario · futuro 365d</h2>
  <p>Selecciona <code>produccion_programada</code> donde estado activo, no descontada, fecha en próximos 365d.</p>
  <div>
    <div class="kpi"><div class="kpi-val">{n_prods}</div><div class="kpi-lbl">Lotes futuros</div></div>
  </div>
  <table>
    <thead><tr><th>ID</th><th>Producto</th><th>Fecha</th><th>Cant kg</th><th>Origen</th></tr></thead>
    <tbody>{paso1_rows or '<tr><td colspan=5 style=padding:14px;text-align:center;color:#94a3b8>Sin lotes futuros</td></tr>'}</tbody>
  </table>
</div>

<div class="card">
  <h2>2️⃣ Match producto ↔ fórmula</h2>
  <p>Cada lote se busca en <code>formula_items</code> por nombre normalizado (sin diferencias de mayúsculas/espacios). Si NO matchea, el consumo de ese lote no se suma (bug).</p>
  <div>
    <div class="kpi"><div class="kpi-val">{n_match}</div><div class="kpi-lbl">Con fórmula ({pct_match:.0f}%)</div></div>
    <div class="kpi {('kpi-error' if n_huerf > 0 else '')}"><div class="kpi-val">{n_huerf}</div><div class="kpi-lbl">SIN fórmula (huérfanos)</div></div>
  </div>
  {'<div class="alert alert-bad">⚠ <strong>' + str(n_huerf) + ' lotes no tienen fórmula que matchee.</strong> El cálculo SUBESTIMA · cada lote huérfano contribuye 0g a Abastecimiento. Revisá los nombres en la tabla y compará contra formula_headers.</div>' if n_huerf > 0 else '<div style="background:#f0fdf4;border-left:5px solid #16a34a;padding:14px 18px;border-radius:8px;color:#15803d;margin-top:12px">✓ Todos los lotes matchean con una fórmula.</div>'}

  <h3 style="margin-top:16px;color:#991b1b;font-size:13px">Productos huérfanos (sin match)</h3>
  <table>
    <thead><tr><th>Producto en producción_programada</th><th style="text-align:right">N lotes</th></tr></thead>
    <tbody>{paso2_huerf_rows or '<tr><td colspan=2 style="padding:14px;text-align:center;color:#15803d">Ninguno · todos matchean</td></tr>'}</tbody>
  </table>
</div>

<div class="card">
  <h2>3️⃣ Suma de consumo por MP</h2>
  <p>Para cada lote con fórmula, se calcula <code>gramos = g_por_lote × (cant_kg / lote_size_kg)</code> o <code>(% / 100) × cant_kg × 1000</code> · se acumula por MP.</p>
  <div>
    <div class="kpi"><div class="kpi-val">{n_mps_total}</div><div class="kpi-lbl">MPs distintas consumidas</div></div>
  </div>
  <table>
    <thead><tr><th>Código MP</th><th>Nombre</th><th style="text-align:right">Total 365d</th><th style="text-align:right">N lotes</th><th>Sample (primeros 3 lotes)</th></tr></thead>
    <tbody>{paso3_rows or '<tr><td colspan=5 style="padding:14px;text-align:center;color:#94a3b8">Sin MPs consumidas</td></tr>'}</tbody>
  </table>
</div>

</body></html>"""


@bp.route("/admin/limpiar-sols-ocs", methods=["GET", "POST"])
def admin_limpiar_sols_ocs():
    """Página HTML standalone · limpiar SOLs y OCs fantasma.

    Sebastián 24-may-2026 noche: 'no hay nada en cola, elimina todas
    las solicitudes que aparezcan también de compras porque no son
    reales'. Las SOLs/OCs viejas/test contaminan el cálculo de la
    columna 'En cola' de Abastecimiento.

    GET: muestra preview con conteos por estado.
    POST: ejecuta la limpieza con audit_log.
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2><p>Logueate en <a href='/'>app.eossuite.com</a></p></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin / compras</h2></body></html>", 403
    conn = get_db(); cur = conn.cursor()

    if request.method == 'POST':
        modo = (request.form.get('modo') or 'safe').strip()
        sols_canceladas = 0
        sols_items_borrados = 0
        ocs_canceladas = 0
        ocs_items_borrados = 0
        try:
            if modo == 'safe':
                # MODO SEGURO · cancelar SOLs sin OC ni recepción
                # FK real: solicitudes_compra_items.numero = solicitudes_compra.numero
                cur.execute(
                    "SELECT numero FROM solicitudes_compra "
                    "WHERE estado IN ('Pendiente','Aprobada') "
                    "AND COALESCE(numero_oc,'')='' "
                    "AND COALESCE(numero,'') != ''"
                )
                sol_nums = [r[0] for r in cur.fetchall()]
                if sol_nums:
                    ph = ','.join(['?'] * len(sol_nums))
                    cur.execute(
                        f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})",
                        sol_nums,
                    )
                    sols_items_borrados = cur.rowcount or 0
                    cur.execute(
                        f"UPDATE solicitudes_compra SET estado='Cancelada' WHERE numero IN ({ph})",
                        sol_nums,
                    )
                    sols_canceladas = cur.rowcount or 0
                # Cancelar OCs en Borrador o Revisada sin recepción
                cur.execute(
                    "SELECT numero_oc FROM ordenes_compra "
                    "WHERE estado IN ('Borrador','Revisada')"
                )
                oc_nums = [r[0] for r in cur.fetchall()]
                if oc_nums:
                    ph2 = ','.join(['?'] * len(oc_nums))
                    cur.execute(
                        f"DELETE FROM ordenes_compra_items WHERE numero_oc IN ({ph2})",
                        oc_nums,
                    )
                    ocs_items_borrados = cur.rowcount or 0
                    cur.execute(
                        f"UPDATE ordenes_compra SET estado='Cancelada' WHERE numero_oc IN ({ph2})",
                        oc_nums,
                    )
                    ocs_canceladas = cur.rowcount or 0
            elif modo == 'all':
                # MODO BORRAR TODAS · TODAS las SOLs/OCs activas, incluso Autorizadas/Parciales.
                # Solo respeta las ya Recibidas/Cerradas (histórico).
                cur.execute(
                    "SELECT numero FROM solicitudes_compra "
                    "WHERE estado NOT IN ('Cancelada','Recibida','Cerrada') "
                    "AND COALESCE(numero,'') != ''"
                )
                sol_nums = [r[0] for r in cur.fetchall()]
                if sol_nums:
                    ph = ','.join(['?'] * len(sol_nums))
                    cur.execute(
                        f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})",
                        sol_nums,
                    )
                    sols_items_borrados = cur.rowcount or 0
                    cur.execute(
                        f"UPDATE solicitudes_compra SET estado='Cancelada' WHERE numero IN ({ph})",
                        sol_nums,
                    )
                    sols_canceladas = cur.rowcount or 0
                cur.execute(
                    "SELECT numero_oc FROM ordenes_compra "
                    "WHERE estado NOT IN ('Cancelada','Recibida','Cerrada')"
                )
                oc_nums = [r[0] for r in cur.fetchall()]
                if oc_nums:
                    ph2 = ','.join(['?'] * len(oc_nums))
                    cur.execute(
                        f"DELETE FROM ordenes_compra_items WHERE numero_oc IN ({ph2})",
                        oc_nums,
                    )
                    ocs_items_borrados = cur.rowcount or 0
                    cur.execute(
                        f"UPDATE ordenes_compra SET estado='Cancelada' WHERE numero_oc IN ({ph2})",
                        oc_nums,
                    )
                    ocs_canceladas = cur.rowcount or 0
            audit_log(cur, usuario=user, accion='LIMPIAR_SOLS_OCS_FANTASMA',
                      tabla='solicitudes_compra+ordenes_compra', registro_id='bulk',
                      despues={'modo': modo, 'sols': sols_canceladas,
                                'ocs': ocs_canceladas,
                                'sols_items': sols_items_borrados,
                                'ocs_items': ocs_items_borrados})
            conn.commit()
            return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Limpieza completada</title>
<style>body{{font-family:system-ui;background:#f8fafc;padding:40px}}
.card{{max-width:720px;margin:0 auto;background:#fff;border-radius:14px;padding:30px;box-shadow:0 10px 40px rgba(0,0,0,0.1)}}
h1{{color:#15803d}} .kpi{{display:inline-block;background:#f0fdf4;border:1px solid #16a34a;padding:14px 22px;border-radius:8px;margin:6px;text-align:center}}
.kpi-val{{font-size:32px;font-weight:800;color:#15803d}} .kpi-lbl{{font-size:11px;color:#64748b;text-transform:uppercase}}
a{{display:inline-block;background:#0f766e;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;margin-top:14px;font-weight:700}}</style></head><body>
<div class="card">
<h1>✓ Limpieza completada · modo {modo}</h1>
<div class="kpi"><div class="kpi-val">{sols_canceladas}</div><div class="kpi-lbl">SOLs canceladas</div></div>
<div class="kpi"><div class="kpi-val">{sols_items_borrados}</div><div class="kpi-lbl">Items SOL borrados</div></div>
<div class="kpi"><div class="kpi-val">{ocs_canceladas}</div><div class="kpi-lbl">OCs canceladas</div></div>
<div class="kpi"><div class="kpi-val">{ocs_items_borrados}</div><div class="kpi-lbl">Items OC borrados</div></div>
<p>La columna 'En cola' de Abastecimiento debería bajar a 0 o reflejar solo lo real ahora.</p>
<a href="/admin/limpiar-sols-ocs">↻ Volver a limpiar</a>
<a href="/" style="background:#475569;margin-left:8px">← Dashboard</a>
</div></body></html>"""
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return f"<html><body style='font-family:system-ui;padding:40px'><h1 style='color:#dc2626'>Error</h1><pre style='background:#fee2e2;padding:14px'>{str(e)[:500]}</pre><a href='/admin/limpiar-sols-ocs'>Reintentar</a></body></html>", 500

    # GET · preview
    counts = {}
    try:
        for r in cur.execute(
            "SELECT COALESCE(estado,'(vacío)'), COUNT(*) FROM solicitudes_compra GROUP BY estado"
        ).fetchall():
            counts[f'SOL · {r[0]}'] = r[1]
    except Exception:
        pass
    try:
        for r in cur.execute(
            "SELECT COALESCE(estado,'(vacío)'), COUNT(*) FROM ordenes_compra GROUP BY estado"
        ).fetchall():
            counts[f'OC · {r[0]}'] = r[1]
    except Exception:
        pass
    rows_html = ''
    for k, v in sorted(counts.items()):
        rows_html += f'<tr><td style="padding:6px 12px">{k}</td><td style="padding:6px 12px;text-align:right;font-weight:700">{v}</td></tr>'
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Limpiar SOLs/OCs</title>
<style>body{{font-family:system-ui;background:#f8fafc;padding:40px}}
.card{{max-width:720px;margin:0 auto;background:#fff;border-radius:14px;padding:30px;box-shadow:0 10px 40px rgba(0,0,0,0.1)}}
h1{{color:#1e293b;margin:0 0 14px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0}}
th{{background:#f1f5f9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569}}
tr{{border-bottom:1px solid #f1f5f9}}
.btn{{padding:14px 22px;border-radius:8px;border:none;font-size:14px;font-weight:800;cursor:pointer;margin-right:8px;margin-top:14px}}
.btn-safe{{background:#ea580c;color:#fff}} .btn-all{{background:#dc2626;color:#fff}}
.meta{{font-size:11px;color:#64748b;margin-top:14px}}</style></head><body>
<div class="card">
<h1>🧹 Limpiar SOLs / OCs fantasma</h1>
<p>Estado actual en BD:</p>
<table><thead><tr><th>Categoría</th><th style="text-align:right">Cantidad</th></tr></thead><tbody>{rows_html or '<tr><td colspan=2 style="padding:14px;text-align:center;color:#94a3b8">Sin registros</td></tr>'}</tbody></table>

<form method="POST" style="display:inline" onsubmit="return confirm('¿Cancelar SOLs/OCs sin recepción?\\n\\nMODO SEGURO: solo Pendiente/Aprobada/Borrador/Revisada · no toca lo recibido.');">
  <input type="hidden" name="modo" value="safe">
  <button type="submit" class="btn btn-safe">🟠 Limpieza SEGURA · solo no-recibidas</button>
</form>
<form method="POST" style="display:inline" onsubmit="return confirm('⚠ ATENCIÓN · MODO BORRAR TODAS las SOLs/OCs activas (incluye Autorizadas y Parciales).\\n\\nSolo se conservan las ya Recibidas y Cerradas. ¿Continuar?');">
  <input type="hidden" name="modo" value="all">
  <button type="submit" class="btn btn-all">🔴 Borrar TODAS las activas</button>
</form>

<p class="meta">Modo SEGURO cancela SOLs en estado Pendiente/Aprobada (sin OC) y OCs en Borrador/Revisada. Modo BORRAR TODAS también cancela Autorizadas y Parciales. Las Recibidas y Cerradas (histórico) NUNCA se tocan. Operación auditada en audit_log.</p>
<p><a href="/" style="color:#475569">← Volver al dashboard</a></p>
</div></body></html>"""


@bp.route("/admin/llenar-calendario", methods=["GET", "POST"])
def admin_llenar_calendario_pagina():
    """Página HTML standalone · sin dependencia del dashboard JS.

    Sebastián 24-may-2026 noche: "no veo nada de lo que dices · puedes
    resolverlo de manera real y sin errores que sea perfecto". El modal
    del dashboard puede estar cacheado o no aparecer · esta página vive
    en su propia URL, no necesita JS del dashboard, no necesita Modal
    Herramientas. Solo logueado, abrir URL, ver botón, click, listo.
    """
    if 'compras_user' not in session:
        return "<html><body><h2>No autorizado</h2><p>Logueate primero en <a href='/'>app.eossuite.com</a></p></body></html>", 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_ACCESS)):
        return "<html><body><h2>Solo admin / compras</h2></body></html>", 403

    if request.method == 'POST':
        # Ejecutar el llenado
        try:
            dh = int(request.form.get('dias_horizonte', 365))
            if dh < 7 or dh > 365:
                dh = 365
        except (ValueError, TypeError):
            dh = 365
        conn = get_db()
        try:
            resultado = _auto_programar_sugeridas(
                conn, dias_horizonte=dh, cob_critico=20, cob_alerta=25,
                cob_vigilar=45, usuario=user, producto_filtro=None,
                origen_nuevo='eos_canonico', lote_kg_override=None,
            )
            conn.commit()
            creados = resultado.get('creados', [])
            saltados = resultado.get('saltados', [])
            n_creados = len(creados)
            n_saltados = len(saltados)

            # Agrupar razones de salteado para diagnóstico claro
            razones_count = {}
            for s in saltados:
                r = s.get('razon', 'sin razón')
                # Normalizar razones técnicas a categorías humanas
                if 'sin velocidad' in r.lower():
                    cat = '⚠ Sin velocidad de venta · producto descontinuado o sin ventas Shopify'
                elif 'sin última producción' in r.lower():
                    cat = '⚠ Sin última producción registrada · no se puede calcular base'
                elif 'ya hay lote' in r.lower():
                    cat = '✓ Ya tiene lote programado ±7d (correcto · no duplica)'
                elif 'absurdo' in r.lower():
                    cat = '⚠ lote_size_kg absurdo (<1kg) · arreglar en admin'
                elif 'paso' in r.lower():
                    cat = '⚠ Paso de cadena <7d · vel o lote inválidos'
                elif 'fecha inválida' in r.lower():
                    cat = '⚠ Fecha sugerida inválida'
                else:
                    cat = f'Otro: {r[:60]}'
                razones_count[cat] = razones_count.get(cat, 0) + 1

            # Render lista detallada de razones
            razones_html = ''
            for razon, cnt in sorted(razones_count.items(), key=lambda x: -x[1]):
                color = '#15803d' if razon.startswith('✓') else '#ea580c'
                razones_html += (
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:8px 12px;border-bottom:1px solid #f1f5f9">'
                    f'<span style="color:{color};font-size:12px">{razon}</span>'
                    f'<strong style="color:#1e293b">{cnt}</strong></div>'
                )

            # Sample de creados (top 10) y saltados con razón principal
            creados_sample = ''
            for c in creados[:15]:
                creados_sample += (
                    f'<tr><td style="padding:4px 8px">{c.get("producto","")}</td>'
                    f'<td style="padding:4px 8px;font-family:monospace">{c.get("fecha","")}</td>'
                    f'<td style="padding:4px 8px;text-align:right">{c.get("cantidad_kg","")}kg</td>'
                    f'<td style="padding:4px 8px;font-size:11px;color:#64748b">{c.get("urgencia","")}</td></tr>'
                )
            if not creados_sample:
                creados_sample = '<tr><td colspan="4" style="padding:14px;color:#94a3b8;text-align:center">Ninguna Sugerida creada · revisá las razones abajo</td></tr>'

            # Sample de productos sin velocidad (los más problemáticos)
            sin_vel_sample = []
            for s in saltados:
                if 'sin velocidad' in s.get('razon', '').lower():
                    sin_vel_sample.append(s.get('producto', ''))
            sin_vel_html = ''
            if sin_vel_sample:
                sin_vel_html = (
                    f'<details style="margin-top:14px"><summary style="cursor:pointer;font-weight:700;color:#ea580c">'
                    f'⚠ {len(sin_vel_sample)} productos SIN velocidad de venta (click para ver)</summary>'
                    f'<div style="background:#fef3c7;padding:10px;border-radius:6px;margin-top:6px;font-size:11px;max-height:200px;overflow:auto">'
                    + ' · '.join(sin_vel_sample[:50])
                    + ('' if len(sin_vel_sample) <= 50 else f' · y {len(sin_vel_sample)-50} más')
                    + '</div></details>'
                )

            diagnostico = ''
            if n_creados == 0:
                diagnostico = (
                    '<div style="background:#fef3c7;border-left:5px solid #f59e0b;padding:14px 18px;'
                    'border-radius:8px;margin:14px 0">'
                    '<strong style="color:#92400e">Diagnóstico:</strong> el algoritmo NO creó Sugeridas. '
                    'Esto ocurre cuando todos los productos ya tienen lotes programados ±7d (correcto · '
                    'no duplica) O cuando los productos no tienen velocidad de venta en Shopify. '
                    'Revisá la tabla de razones abajo.</div>'
                )

            return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Calendario · resultado</title>
<style>
  body{{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:40px}}
  .card{{max-width:920px;margin:0 auto;background:#fff;border-radius:14px;padding:30px;box-shadow:0 10px 40px rgba(0,0,0,0.1)}}
  h1{{color:#1e293b;margin:0 0 14px}}
  .kpi{{display:inline-block;background:#f0fdf4;border:1px solid #16a34a;padding:14px 22px;border-radius:8px;margin:6px;text-align:center;min-width:140px}}
  .kpi-val{{font-size:32px;font-weight:800;color:#15803d}}
  .kpi-lbl{{font-size:11px;color:#64748b;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
  th{{text-align:left;padding:6px 8px;background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase}}
  td{{border-bottom:1px solid #f1f5f9}}
  a{{display:inline-block;background:#0f766e;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;margin-top:14px;font-weight:700}}
</style></head><body>
<div class="card">
  <h1>{'✓' if n_creados > 0 else '⚠'} Resultado · horizonte {dh} días</h1>
  <div>
    <div class="kpi"><div class="kpi-val">{n_creados}</div><div class="kpi-lbl">Sugeridas creadas</div></div>
    <div class="kpi" style="background:#fef3c7;border-color:#f59e0b"><div class="kpi-val" style="color:#92400e">{n_saltados}</div><div class="kpi-lbl">Saltadas</div></div>
  </div>
  {diagnostico}

  <h3 style="color:#1e293b;font-size:14px;margin-top:22px">Razones (agrupadas)</h3>
  <div style="border:1px solid #e2e8f0;border-radius:6px">{razones_html}</div>

  {sin_vel_html}

  <h3 style="color:#1e293b;font-size:14px;margin-top:22px">Primeras 15 Sugeridas creadas</h3>
  <table><thead><tr><th>Producto</th><th>Fecha</th><th>Cant kg</th><th>Urgencia</th></tr></thead>
  <tbody>{creados_sample}</tbody></table>

  <p style="margin-top:20px">Recargá <strong>Abastecimiento</strong> para ver el efecto.</p>
  <a href="/admin/llenar-calendario">↻ Volver a llenar</a>
  <a href="/" style="background:#475569;margin-left:8px">← Volver al dashboard</a>
</div></body></html>"""
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return f"""<!DOCTYPE html><html><body style="font-family:system-ui;padding:40px">
<h1 style="color:#dc2626">Error al llenar el calendario</h1>
<pre style="background:#fee2e2;padding:14px;border-radius:6px">{str(e)[:500]}</pre>
<a href="/admin/llenar-calendario">↻ Reintentar</a>
</body></html>""", 500

    # GET · mostrar formulario con resumen previo
    conn = get_db()
    cur = conn.cursor()
    from datetime import date, timedelta as _td
    hoy = date.today()
    hasta = (hoy + _td(days=365)).isoformat()
    try:
        row = cur.execute(
            """SELECT COUNT(*),
                      COALESCE(MAX(fecha_programada),''),
                      COALESCE(SUM(COALESCE(cantidad_kg,0)),0)
               FROM produccion_programada
               WHERE LOWER(COALESCE(estado,'')) NOT IN
                     ('cancelado','completado','esperando_recurso')
                 AND fecha_programada >= ? AND fecha_programada <= ?
                 AND COALESCE(inventario_descontado_at,'') = ''""",
            (hoy.isoformat(), hasta),
        ).fetchone()
        total = int(row[0] or 0)
        ult = (row[1] or '')[:10] or '—'
        kg_total = float(row[2] or 0)
    except Exception:
        total = 0; ult = '—'; kg_total = 0
    try:
        from datetime import date as _d
        cobertura = (_d.fromisoformat(ult) - hoy).days if ult and ult != '—' else 0
    except Exception:
        cobertura = 0
    boquete = max(0, 365 - cobertura)
    color_estado = '#15803d' if cobertura >= 360 else ('#ea580c' if cobertura >= 90 else '#dc2626')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Llenar calendario</title>
<style>
  body{{font-family:system-ui,-apple-system,Arial;background:#f8fafc;margin:0;padding:40px}}
  .card{{max-width:720px;margin:0 auto;background:#fff;border-radius:14px;padding:30px;box-shadow:0 10px 40px rgba(0,0,0,0.1)}}
  h1{{color:#1e293b;margin:0 0 14px;font-size:22px}}
  .estado{{background:#f1f5f9;border-left:5px solid {color_estado};padding:16px 22px;border-radius:8px;margin:18px 0}}
  .kpi{{display:inline-block;padding:8px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;margin:4px}}
  .kpi b{{color:#1e293b;font-size:18px;display:block}}
  .btn{{background:#7c3aed;color:#fff;border:none;padding:14px 30px;border-radius:8px;font-size:16px;font-weight:800;cursor:pointer;margin-top:14px}}
  .btn:hover{{background:#6d28d9}}
  .meta{{font-size:11px;color:#64748b;margin-top:12px}}
</style></head><body>
<div class="card">
  <h1>📅 Llenar calendario · Sugeridas a 365 días</h1>
  <p>Esta acción ejecuta el algoritmo <code>_auto_programar_sugeridas</code> con horizonte 365 días. Para cada producto con velocidad de venta, calcula la próxima producción y la programa como Sugerida (azul · editable · NO Fija).</p>

  <div class="estado">
    <strong style="color:{color_estado}">Cobertura actual: {cobertura} días</strong> de 365 · boquete {boquete} días<br>
    <div class="kpi"><b>{total}</b>lotes futuros</div>
    <div class="kpi"><b>{kg_total:.0f} kg</b>proyectados</div>
    <div class="kpi"><b>{ult}</b>último lote</div>
  </div>

  <form method="POST" onsubmit="return confirm('¿Llenar calendario? · Esto puede crear muchas Sugeridas si el calendario está corto.');">
    <label style="font-size:13px;color:#475569">Días horizonte:
      <select name="dias_horizonte" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;margin-left:8px">
        <option value="365" selected>365 (1 año · recomendado)</option>
        <option value="180">180 (6 meses)</option>
        <option value="120">120 (4 meses)</option>
        <option value="90">90 (3 meses)</option>
      </select>
    </label>
    <br>
    <button type="submit" class="btn">🚀 Llenar calendario ahora</button>
  </form>

  <p class="meta">Esta página no depende del dashboard JS · funciona aún si el modal de Herramientas no carga. Después de llenar, vé a Abastecimiento y deberías ver el consumo real.</p>
</div></body></html>"""


@bp.route("/api/admin/diag-cobertura-calendario", methods=["GET"])
def diag_cobertura_calendario():
    """FIX 24-may noche · Sebastián vio Abastecimiento 365d con cifras
    absurdamente bajas. Sospecha: el calendario no llega a 365d, solo
    hay ~90d de Sugeridas pese al endpoint mostrar 7 buckets hasta 365.

    Devuelve la realidad: por origen + por mes futuro, cuántos lotes
    activos hay desde HOY hasta hoy+365d. Permite confirmar dónde se
    corta el calendario y disparar el cron manual para llenarlo.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    conn = get_db()
    cur = conn.cursor()
    from datetime import date, timedelta as _td
    hoy = date.today()
    hasta = (hoy + _td(days=365)).isoformat()
    hoy_iso = hoy.isoformat()

    por_origen = {}
    por_mes = {}
    total = 0
    kg_total = 0.0
    fecha_ultimo_lote = None
    try:
        for r in cur.execute(
            """SELECT COALESCE(origen,'(sin_origen)'),
                      substr(fecha_programada, 1, 7) AS mes,
                      substr(fecha_programada, 1, 10) AS fecha_d,
                      COUNT(*),
                      COALESCE(SUM(COALESCE(cantidad_kg, 0)), 0)
               FROM produccion_programada
               WHERE LOWER(COALESCE(estado, '')) NOT IN
                     ('cancelado', 'completado', 'esperando_recurso')
                 AND fecha_programada >= ?
                 AND fecha_programada <= ?
                 AND COALESCE(inventario_descontado_at, '') = ''
               GROUP BY COALESCE(origen,'(sin_origen)'),
                        substr(fecha_programada, 1, 7),
                        substr(fecha_programada, 1, 10)""",
            (hoy_iso, hasta),
        ).fetchall():
            origen, mes, fecha_d, cnt, kg = r
            por_origen[origen] = por_origen.get(origen, 0) + int(cnt)
            por_mes[mes] = por_mes.get(mes, 0) + int(cnt)
            total += int(cnt)
            kg_total += float(kg or 0)
            if not fecha_ultimo_lote or (fecha_d or '') > fecha_ultimo_lote:
                fecha_ultimo_lote = fecha_d
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500

    cobertura_dias = 0
    if fecha_ultimo_lote:
        try:
            from datetime import date as _date
            cobertura_dias = (_date.fromisoformat(fecha_ultimo_lote) - hoy).days
        except Exception:
            pass

    # Calcular gap · si cobertura < 365 hay un "boquete"
    boquete_dias = max(0, 365 - cobertura_dias)
    return jsonify({
        'hoy': hoy_iso,
        'horizonte_pedido_dias': 365,
        'total_lotes_futuros': total,
        'kg_total_proyectado': round(kg_total, 1),
        'por_origen': por_origen,
        'por_mes': dict(sorted(por_mes.items())),
        'fecha_ultimo_lote': fecha_ultimo_lote,
        'cobertura_dias_real': cobertura_dias,
        'boquete_dias': boquete_dias,
        'recomendacion': (
            'Calendario completo hasta 1 año'
            if cobertura_dias >= 360
            else f'Calendario corto · faltan {boquete_dias}d. Ejecutá '
                  'POST /api/plan/auto-programar-sugeridas con '
                  '{"dias_horizonte": 365} para llenar el resto.'
        ),
    })


@bp.route("/api/plan/auto-programar-sugeridas", methods=["POST"])
def plan_auto_programar_sugeridas():
    """Endpoint manual para disparar auto-programación de Sugeridas.

    Body opcional: {dias_horizonte: 365, cob_critico: 20, cob_alerta: 25}
    Sebastián 23-may-2026 · cierra el bucle "el sistema calcula pero
    no programa".

    FIX 24-may noche · default subido de 90 a 365 alineado con el cron
    auto-sugerir y con Abastecimiento que muestra horizontes hasta 365d.
    Antes el default 90 dejaba el calendario corto y Abastecimiento
    reportaba "déficit casi 0" en buckets >90d.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    d = request.get_json(silent=True) or {}
    try:
        dh = max(7, min(int(d.get('dias_horizonte', 365)), 365))
    except Exception:
        dh = 365
    try:
        cc = int(d.get('cob_critico', 20))
        ca = int(d.get('cob_alerta', 25))
        cv = int(d.get('cob_vigilar', 45))
    except Exception:
        cc, ca, cv = 20, 25, 45
    producto = (d.get('producto') or '').strip() or None
    # Si el usuario está programando manualmente desde el modal por producto,
    # marca como Fijo (eos_plan) en lugar de Sugerida · entiende que el
    # usuario eligió hacerlo · queda intocable por regenerar_canonicos.
    # El cron diario sigue creando como 'eos_canonico' (sin parámetro 'producto').
    origen = 'eos_plan' if producto else 'eos_canonico'
    if d.get('origen_nuevo') in ('eos_plan', 'eos_canonico'):
        origen = d['origen_nuevo']
    # FIX 23-may PM · usuario puede editar Lote en modal y mandarlo
    lote_kg_ovr = None
    try:
        if d.get('lote_kg_override') is not None:
            _v = float(d.get('lote_kg_override'))
            if 1.0 <= _v <= 2000.0:
                lote_kg_ovr = _v
    except Exception:
        lote_kg_ovr = None
    conn = get_db()
    resultado = _auto_programar_sugeridas(
        conn, dias_horizonte=dh, cob_critico=cc, cob_alerta=ca,
        cob_vigilar=cv, usuario=user, producto_filtro=producto,
        origen_nuevo=origen, lote_kg_override=lote_kg_ovr,
    )
    return jsonify({'ok': True, **resultado})


@bp.route("/api/plan/limpiar-sugeridas-futuras", methods=["POST"])
def plan_limpiar_sugeridas_futuras():
    """Sebastián 23-may-2026 · "el calendario salen muchas cosas · limpiarlo
    dejando lo que ya puse yo en mayo y la primera semana de junio".

    Borra producciones SUGERIDAS (origen='eos_canonico' y 'auto_plan' y
    'sugerido' y 'manual' · NO Fijo) con fecha > parámetro `desde`.

    NUNCA toca Fijo (eos_plan, eos_b2b, eos_retroactivo). Soft-delete
    via estado='cancelado' para preservar audit trail. Audit_log por
    cada uno.

    Body: {desde: 'YYYY-MM-DD' (excluido), dry_run: true/false}
    Response: {ok, n_borradas, n_dry, items: [...]}
    """
    from datetime import date as _date2
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    d = request.get_json(silent=True) or {}
    desde = (d.get('desde') or '').strip()
    if not desde or not _valida_fecha_iso(desde):
        return jsonify({'error': 'desde formato YYYY-MM-DD requerido'}), 400
    dry = bool(d.get('dry_run'))
    conn = get_db()
    cur = conn.cursor()
    # Listar candidatas · solo Sugeridas · fecha estricta > desde
    rows = cur.execute(
        """SELECT id, producto, fecha_programada, cantidad_kg,
                  COALESCE(origen,''), COALESCE(estado,'')
           FROM produccion_programada
           WHERE substr(fecha_programada,1,10) > ?
             AND COALESCE(origen,'') IN ('eos_canonico','auto_plan','sugerido','manual','calendar')
             AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
             AND fin_real_at IS NULL
             AND inventario_descontado_at IS NULL
           ORDER BY fecha_programada""",
        (desde,),
    ).fetchall()
    items = [{
        'id': r[0], 'producto': r[1], 'fecha': r[2][:10] if r[2] else '',
        'kg': float(r[3] or 0), 'origen': r[4],
    } for r in rows]
    if dry:
        return jsonify({'ok': True, 'dry_run': True, 'n_dry': len(items),
                        'items': items})
    # Aplicar soft-cancel con audit_log
    n = 0
    for r in rows:
        try:
            cur.execute(
                """UPDATE produccion_programada
                   SET estado='cancelado',
                       observaciones = COALESCE(observaciones,'') || ' · cancelado limpieza Sebastián 23-may'
                   WHERE id = ? AND fin_real_at IS NULL""",
                (r[0],),
            )
            try:
                audit_log(cur, usuario=user, accion='LIMPIAR_SUGERIDA_FUTURA',
                          tabla='produccion_programada', registro_id=str(r[0]),
                          antes={'producto': r[1], 'fecha': r[2],
                                  'kg': float(r[3] or 0), 'origen': r[4], 'estado': r[5]},
                          despues={'estado': 'cancelado'})
            except Exception:
                pass
            n += 1
        except Exception:
            continue
    conn.commit()
    return jsonify({'ok': True, 'dry_run': False, 'n_borradas': n,
                    'items': items})


@bp.route("/api/plan/sugerir-preview", methods=["GET"])
def plan_sugerir_preview():
    """Sebastián 23-may-2026 · al abrir un producto en Necesidades,
    quiere ver 'cuántas producciones o en cuánto' se sugieren ANTES de
    programarlas. Acepta ?producto=NOMBRE o ?all=1 (todos).

    Devuelve por producto:
      - n_sugeridas_horizonte
      - fechas: [{fecha, kg, dur_lote_dias, dias_hasta}]
      - velocidad_kg_dia, lote_bulk_kg, dur_lote_dias, paso_dias
      - blocker: razón si no se puede sugerir nada
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code
    from datetime import date as _date2, timedelta as _td2
    producto_filtro = (request.args.get('producto') or '').strip().upper()
    try:
        dh = max(7, min(int(request.args.get('dias_horizonte', 90)), 365))
    except Exception:
        dh = 90
    try:
        ca = int(request.args.get('cob_alerta', 25))
    except Exception:
        ca = 25
    # FIX 23-may PM · permite override del lote para recalcular preview
    lote_ovr = None
    try:
        if request.args.get('lote_kg_override'):
            _v = float(request.args.get('lote_kg_override'))
            if 1.0 <= _v <= 2000.0:
                lote_ovr = _v
    except Exception:
        lote_ovr = None
    conn = get_db()
    cur = conn.cursor()
    productos = _calcular_animus_dtc(cur, ventana=60, cob_critico=20,
                                       cob_alerta=ca, cob_vigilar=45)
    fijo_prog_por_prod = {}
    try:
        for r in cur.execute(
            """SELECT UPPER(TRIM(producto)) AS prod,
                      MAX(substr(fecha_programada,1,10)) AS f,
                      cantidad_kg
               FROM produccion_programada
               WHERE COALESCE(origen,'') IN ('eos_plan','eos_b2b','eos_retroactivo')
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                 AND fin_real_at IS NULL
                 AND COALESCE(cantidad_kg,0) > 0
               GROUP BY UPPER(TRIM(producto))""",
        ).fetchall():
            fijo_prog_por_prod[r[0]] = {'fecha': r[1], 'kg': float(r[2] or 0)}
    except Exception:
        pass
    hoy = _hoy_colombia()
    out = []
    for p in (productos or []):
        prod = (p.get('producto_nombre') or '').strip()
        if not prod:
            continue
        if producto_filtro and prod.upper() != producto_filtro:
            continue
        vel = float(p.get('velocidad_kg_dia') or 0)
        lote_kg = float(p.get('lote_bulk_kg') or 0)
        # FIX 23-may PM · si caller pasó override (UI editable), usarlo
        if lote_ovr is not None and producto_filtro and prod.upper() == producto_filtro:
            lote_kg = lote_ovr
        psf = p.get('proxima_sugerida_fecha')
        if not psf and vel > 0 and lote_kg > 0:
            fp = fijo_prog_por_prod.get(prod.upper())
            if fp and fp['kg'] > 0:
                try:
                    f_base = _date2.fromisoformat(fp['fecha'])
                    dur = max(1, int(fp['kg'] / vel))
                    psf = (f_base + _td2(days=max(1, dur - ca))).isoformat()
                except Exception:
                    psf = None
        blocker = None
        if lote_kg <= 0:
            blocker = 'sin lote_bulk_kg en maestro_animus_dtc'
        elif vel <= 0:
            blocker = 'sin velocidad de venta (vender más para alimentar el cálculo)'
        elif not psf:
            blocker = 'sin última producción de referencia'
        fechas = []
        dur_lote = max(1, int(lote_kg / vel)) if (vel > 0 and lote_kg > 0) else 0
        paso = max(1, dur_lote - ca) if dur_lote else 0
        if not blocker and paso > 0:
            try:
                f_cursor = _date2.fromisoformat(str(psf)[:10])
            except Exception:
                f_cursor = None
                blocker = f'fecha inválida {psf}'
            while f_cursor and (f_cursor - hoy).days <= dh:
                dias_hasta = (f_cursor - hoy).days
                if dias_hasta < 0:
                    f_cursor = f_cursor + _td2(days=paso)
                    continue
                fdesde = (f_cursor - _td2(days=7)).isoformat()
                fhasta = (f_cursor + _td2(days=7)).isoformat()
                row = cur.execute(
                    """SELECT COUNT(*) FROM produccion_programada
                       WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))
                         AND substr(fecha_programada,1,10) BETWEEN ? AND ?
                         AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                         AND inventario_descontado_at IS NULL""",
                    (prod, fdesde, fhasta),
                ).fetchone()
                ya_hay = bool(row and int(row[0] or 0) > 0)
                fechas.append({
                    'fecha': f_cursor.isoformat(),
                    'kg': lote_kg,
                    'dias_hasta': dias_hasta,
                    'ya_programado': ya_hay,
                })
                f_cursor = f_cursor + _td2(days=paso)
        out.append({
            'producto': prod,
            'velocidad_kg_dia': vel,
            'lote_bulk_kg': lote_kg,
            'lote_bulk_kg_bd': float(p.get('lote_bulk_kg_bd') or 0),
            'lote_calculado': bool(p.get('lote_calculado')),
            'ml_inferido': bool(p.get('ml_inferido')),
            'dur_lote_dias': dur_lote,
            'paso_dias': paso,
            'cob_alerta_dias': ca,
            'horizonte_dias': dh,
            'n_sugeridas': len([f for f in fechas if not f['ya_programado']]),
            'n_ya_programadas': len([f for f in fechas if f['ya_programado']]),
            'fechas': fechas,
            'proxima_fecha_base': psf,
            'blocker': blocker,
        })
    if producto_filtro:
        if not out:
            return jsonify({'ok': False, 'error': 'producto no está en _calcular_animus_dtc',
                            'producto_buscado': producto_filtro}), 404
        return jsonify({'ok': True, **out[0]})
    return jsonify({'ok': True, 'productos': out})


@bp.route("/api/plan/regenerar-canonicos", methods=["POST"])
def regenerar_canonicos():
    """Lee producto_canonico_config y regenera lotes próximos 365d.
    Sebastián 14-may-2026: después de llenar la tabla, click 1 botón
    y el sistema arma todos los canónicos basados en esa config.

    Pasos:
    1. Cancela canónicos viejos (origen='eos_canonico') sin ejecutar
       cuyo producto está en config (mantiene los completados).
    2. Para cada producto en producto_canonico_config con kg_por_lote>0
       y frecuencia_dias>0 y activo=1:
       a. Calcula fecha_base = última producción real + frecuencia
          (o próximo lunes si no hay histórico)
       b. Genera lotes cada frecuencia_dias hasta hoy+365d
       c. Respeta festivos + L-V
    3. Audit log REGENERAR_CANONICOS
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    conn = get_db()
    c = conn.cursor()
    from datetime import date as _date, timedelta as _td

    # BUG-21 fix · 19-may-2026 audit Planta PERFECTA:
    # Antes 2 admins (o doble-click) podían ejecutar regenerar_canonicos en
    # paralelo · ambos cancelaban (idempotente, OK) y ambos insertaban
    # generando 2× 365 lotes por producto. Ahora lock vía cron_locks (mismo
    # patrón del multi-cron) con TTL 5 min, libera al final del request.
    _LOCK_NAME = 'plan_regenerar_canonicos'
    _lock_ok = False
    try:
        # 1ro: limpiar locks stale (>5min) por si alguien crasheó
        c.execute(
            "DELETE FROM cron_locks WHERE job_name = ? "
            "AND datetime(locked_at) < datetime('now','-5 minutes')",
            (_LOCK_NAME,),
        )
        # 2do: intentar tomar el lock (INSERT con UNIQUE)
        c.execute(
            "INSERT INTO cron_locks (job_name, locked_at, locked_by) "
            "VALUES (?, datetime('now'), ?)",
            (_LOCK_NAME, user),
        )
        _lock_ok = True
        conn.commit()
    except Exception:
        # Otro request ya tiene el lock
        try: conn.rollback()
        except Exception: pass
        return jsonify({
            'error': 'Otro regenerar-canonicos ya está corriendo · esperá '
                     'que termine (máximo 5 minutos) y reintentá.',
            'codigo': 'lock_busy',
        }), 409

    # 1) Productos con config válida
    configs = c.execute(
        """SELECT producto_nombre, kg_por_lote, ml_unidad, frecuencia_dias
           FROM producto_canonico_config
           WHERE COALESCE(activo, 1) = 1
             AND kg_por_lote > 0
             AND frecuencia_dias > 0""",
    ).fetchall()
    if not configs:
        return jsonify({
            "error": "Sin config válida · llená la tabla en /admin/configurar-canonicos primero",
        }), 400

    productos_a_regenerar = [r[0] for r in configs]

    # 2) Cancelar TODO lo viejo sin ejecutar de esos productos · Sebastián
    # 14-may-2026: "veo dos limpiadores h ambos de 80kg" · regenerar-simple
    # solo cancelaba eos_canonico · ahora también cancela calendar/manual
    # (igual que generar-plan-perfecto). NUNCA toca eos_plan ni eos_retroactivo
    # ni lotes con fin_real_at o inicio_real_at.
    placeholders = ",".join(["?"] * len(productos_a_regenerar))
    # Sebastián 16-may-2026: incluir 'propuesto' en los estados a cancelar.
    # Un lote 'propuesto' (sin confirmar, sin iniciar) que sobreviviera a
    # la regeneración quedaría duplicado con el nuevo lote generado.
    # BUG-24 fix · 19-may-2026 audit Planta PERFECTA: capturar los IDs
    # ANTES del UPDATE y auditar cada uno · misma trampa del 19-may
    # ("desapareció sin rastro"). Sin audit por id, si después aparece un
    # lote perdido no hay cómo saber cuándo/por qué se canceló.
    ids_a_cancelar = [r[0] for r in c.execute(
        f"""SELECT id, producto, fecha_programada, COALESCE(cantidad_kg,0), origen
            FROM produccion_programada
            WHERE origen IN ('eos_canonico','calendar','manual')
              AND estado IN ('pendiente','programado','esperando_recurso','propuesto')
              AND fin_real_at IS NULL
              AND inicio_real_at IS NULL
              AND (bloqueado_at IS NULL OR bloqueado_at = '')
              AND producto IN ({placeholders})""",
        productos_a_regenerar,
    ).fetchall()]
    # FIX P1 audit 24-may-2026 · respetar bloqueado_at (semana workflow
    # bloqueada por cron Lunes 7am). Antes este UPDATE cancelaba lotes
    # bloqueados por el cron de planeación semanal · ahora se preservan
    # para que el flujo "lunes a sábado lo planeé el lunes y no se mueve"
    # quede sólido.
    # FIX P2 audit 24-may-2026 · cap observaciones a últimos 1500 chars al
    # concatenar (sin esto, después de meses de crons, la fila acumulaba
    # kilobytes de basura y la UI mostraba un wall of text ilegible).
    n_cancelados = c.execute(
        f"""UPDATE produccion_programada
            SET estado = 'cancelado',
                observaciones = SUBSTR(
                  COALESCE(observaciones,'') || ' · CANCELADO_REGEN_CANON_' || {SQLITE_NOW_COL},
                  -1500
                )
            WHERE origen IN ('eos_canonico','calendar','manual')
              AND estado IN ('pendiente','programado','esperando_recurso','propuesto')
              AND fin_real_at IS NULL
              AND inicio_real_at IS NULL
              AND (bloqueado_at IS NULL OR bloqueado_at = '')
              AND producto IN ({placeholders})""",
        productos_a_regenerar,
    ).rowcount
    # Audit log por cada id cancelado (no romper si la lista es larga ·
    # cap a 500 para no explotar audit_log en regenerados masivos).
    for _pid in ids_a_cancelar[:500]:
        try:
            audit_log(c, usuario=user, accion='CANCELAR_REGEN_CANON',
                      tabla='produccion_programada', registro_id=_pid,
                      despues={'razon': 'regenerar_canonicos · cancelado bulk'})
        except Exception:
            pass
        # Refactor observaciones · evento estructurado · si volvemos a este
        # producto vemos historia limpia en timeline.
        _registrar_evento_prod(c, _pid, 'CANCELADO_REGEN_CANON',
            'Cancelado por regenerar plan canónico', user)

    # 3) Última producción real por producto (para calcular base)
    ultima_real = {}
    for r in c.execute(
        f"""SELECT producto, MAX(fin_real_at)
            FROM produccion_programada
            WHERE fin_real_at IS NOT NULL
              AND producto IN ({placeholders})
            GROUP BY producto""",
        productos_a_regenerar,
    ).fetchall():
        ultima_real[r[0]] = (r[1] or "")[:10]

    # 3b) Velocidad de ventas por producto (kg/día · ventana 60d)
    # Sebastián 14-may-2026: "la producción es 20 días antes de que se
    # acabe el producto". Aplicamos regla 20d con velocidad REAL.
    necs_canon = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)

    # Sebastián 15-may-2026: "me sugiere contorno de cafeína en mayo
    # cuando tiene stock para 86 días". El primer lote DEBE salir de la
    # cobertura real del stock (regla 20d). PERO los nombres de producto
    # difieren entre producto_canonico_config y _calcular_animus_dtc
    # (orden de palabras, español/inglés, plurales). Match difuso por
    # palabras-prefijo para que SIEMPRE se encuentre la cobertura.
    import unicodedata as _ud
    def _palabras(s):
        t = _ud.normalize('NFD', str(s or '').upper())
        t = ''.join(ch for ch in t if _ud.category(ch) != 'Mn')
        t = t.replace('+', ' ').replace('%', ' ').replace('.', ' ')
        return [w for w in t.split() if len(w) >= 3]

    # Palabras genéricas · NO sirven para distinguir productos (casi
    # todos las comparten) · se excluyen del scoring para evitar que
    # "CREMA X" matchee "CREMA Y" solo por compartir "CREMA".
    _GENERICAS = {'SUERO','CREMA','GEL','LIMPIADOR','EMULSION','ESENCIA',
                  'CONTORNO','SERUM','FORMULA','NUEVA','NUEVO','DE','DEL',
                  'CORPORAL','FACIAL','FACIALES','HIDRATANTE'}

    def _buscar_nec(prod_config):
        """Devuelve la entrada de necs_canon que matchea prod_config.
        1) match exacto de conjunto de palabras · 2) match difuso por
        prefijos de palabras SIGNIFICATIVAS (>=70%). Rechaza empates
        para no asignar la cobertura de un producto equivocado."""
        objetivo = _palabras(prod_config)
        if not objetivo:
            return None
        obj_set = set(objetivo)
        # palabras significativas (no genéricas) para el scoring
        obj_sig = [w for w in objetivo if w not in _GENERICAS] or objetivo
        candidatos = []  # (score, nec)
        for n in necs_canon:
            cand = _palabras(n.get("producto_nombre"))
            if not cand:
                continue
            if obj_set == set(cand):
                return n  # match exacto de palabras
            cand_sig = [w for w in cand if w not in _GENERICAS] or cand
            aciertos = 0
            for ow in obj_sig:
                for cw in cand_sig:
                    p = min(len(ow), len(cw), 5)
                    if p >= 4 and ow[:p] == cw[:p]:
                        aciertos += 1
                        break
            # divisor = palabras significativas del objetivo (config)
            score = aciertos / max(len(obj_sig), 1)
            candidatos.append((score, n))
        if not candidatos:
            return None
        candidatos.sort(key=lambda x: x[0], reverse=True)
        mejor_score = candidatos[0][0]
        if mejor_score < 0.7:
            return None  # ningún candidato suficientemente parecido
        # Rechazar empate · si 2+ candidatos casi igual de buenos, es
        # ambiguo · mejor None que arriesgar el match equivocado.
        empatados = [x for x in candidatos if x[0] >= mejor_score - 0.01]
        if len(empatados) > 1:
            return None
        return candidatos[0][1]

    # Pre-resolver cobertura + velocidad por cada producto de config
    cob_por_cfg = {}
    vel_por_cfg = {}
    for cfg in configs:
        prod_cfg = cfg[0]
        nec = _buscar_nec(prod_cfg)
        if nec:
            cob_por_cfg[prod_cfg] = nec.get("dias_cobertura")
            vel_por_cfg[prod_cfg] = nec.get("velocidad_kg_dia") or 0
        else:
            cob_por_cfg[prod_cfg] = None
            vel_por_cfg[prod_cfg] = 0
    cobertura_por_prod = cob_por_cfg
    vel_kg_dia_por_prod = vel_por_cfg

    # 4) Generar lotes nuevos
    hoy = _hoy_colombia()
    horizon_end = hoy + _td(days=365)
    n_generados = 0
    detalles_por_producto = {}

    # Ordenar configs por cobertura ASC · los productos más urgentes
    # (menos días de stock) toman primero los slots tempranos del
    # calendario · evita que un producto holgado le quite el lugar a
    # uno crítico cuando _proxima_fecha_habil escalona.
    def _cob_orden(cfg):
        cob = cobertura_por_prod.get(cfg[0])
        return cob if cob is not None else 99999
    configs = sorted(configs, key=_cob_orden)

    productos_saltados = []  # productos con datos inválidos · se reportan
    for cfg in configs:
        # Parseo defensivo · un dato sucio NO debe abortar todo el plan
        try:
            prod = cfg[0]
            kg = float(cfg[1])
            ml = int(cfg[2] or 30)
            freq = int(cfg[3])
        except (ValueError, TypeError):
            productos_saltados.append({
                "producto": (cfg[0] if cfg else "?"), "razon": "datos inválidos"})
            continue
        # Rangos · kg/freq absurdos rompen el calendario (lote 99999kg
        # monopoliza días, freq=1 genera 365 lotes de un solo producto)
        if not (1 <= freq <= 365):
            productos_saltados.append({
                "producto": prod, "razon": f"frecuencia {freq} fuera de rango 1-365"})
            continue
        if not (0 < kg <= 1000):
            productos_saltados.append({
                "producto": prod, "razon": f"kg {kg} fuera de rango 0-1000"})
            continue
        vel = vel_kg_dia_por_prod.get(prod, 0)

        # Primer lote · Sebastián 15-may-2026: SIEMPRE desde la cobertura
        # real del stock. Regla "producir 20 días antes de agotar":
        #   base = hoy + dias_cobertura - 20
        # Cobertura negativa (ya agotado) = más urgente → base = hoy.
        # Sin cobertura (sin ventas) → histórico o próximo día hábil.
        cob = cobertura_por_prod.get(prod)
        if cob is not None:
            base = hoy + _td(days=max(int(cob) - BUFFER_REORDEN_DIAS, 0))
        elif prod in ultima_real:
            try:
                base = _date.fromisoformat(ultima_real[prod]) + _td(days=freq)
            except Exception:
                base = hoy + _td(days=(7 - hoy.weekday()) % 7 or 7)
        else:
            base = hoy + _td(days=(7 - hoy.weekday()) % 7 or 7)
        if base < hoy:
            base = hoy

        cur = _proxima_fecha_habil(c, base, prefer_mwf=False,
                                    lote_kg=kg, producto_nombre=prod)
        if cur is None:
            # Sin slot hábil en 400 días · saltar (NO forzar fecha cruda
            # que podría caer sábado/festivo)
            productos_saltados.append({
                "producto": prod, "razon": "sin slot hábil disponible"})
            continue
        # BUG-25 fix · 19-may-2026 audit Planta PERFECTA: si la fecha base
        # ya supera el horizonte 365d (cobertura altísima · stock holgado),
        # antes el `while cur <= horizon_end` no entraba y el producto
        # quedaba saltado SIN avisar. Ahora lo reportamos explícito.
        if cur > horizon_end:
            productos_saltados.append({
                "producto": prod,
                "razon": (f"cobertura empuja primer lote a {cur.isoformat()} "
                          f"(después del horizonte 365d) · stock holgado"),
            })
            continue

        lotes_de_este = []
        slot = 1
        # Tope 400 iteraciones · salvaguarda anti loop infinito
        while cur and cur <= horizon_end and slot <= 400:
            c.execute(
                f"""INSERT INTO produccion_programada
                    (producto, fecha_programada, cantidad_kg, estado, origen,
                     lotes, observaciones)
                    VALUES (?, ?, ?, 'programado', 'eos_canonico', 1, ?)""",
                (prod, cur.isoformat(), kg,
                 f"Canónico auto-regenerado · {kg}kg cada {freq}d · slot {slot}"),
            )
            lotes_de_este.append(cur.isoformat())
            n_generados += 1
            slot += 1
            # Próximo en cur + freq
            siguiente = _proxima_fecha_habil(c, cur + _td(days=freq),
                                              prefer_mwf=False,
                                              lote_kg=kg, producto_nombre=prod)
            if siguiente is None or siguiente <= cur:
                break
            cur = siguiente

        detalles_por_producto[prod] = lotes_de_este

    conn.commit()

    audit_log(c, usuario=user, accion="REGENERAR_CANONICOS",
              tabla="produccion_programada", registro_id=None,
              antes={"n_cancelados": n_cancelados},
              despues={"n_generados": n_generados,
                       "n_productos": len(configs)})
    conn.commit()

    # BUG-21 fix · liberar lock antes del return (en caso de crash, el TTL
    # de 5 min en cron_locks lo libera automáticamente).
    if _lock_ok:
        try:
            c.execute("DELETE FROM cron_locks WHERE job_name = ?", (_LOCK_NAME,))
            conn.commit()
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "n_productos_config": len(configs),
        "n_productos_generados": len(detalles_por_producto),
        "n_lotes_cancelados_viejos": n_cancelados,
        "n_lotes_generados_nuevos": n_generados,
        "productos_saltados": productos_saltados,
        "detalle_por_producto": {
            p: {"n_lotes": len(fechas), "primer_lote": fechas[0] if fechas else None,
                "ultimo_lote": fechas[-1] if fechas else None}
            for p, fechas in detalles_por_producto.items()
        },
    })


@bp.route("/admin/calculo-frecuencias", methods=["GET"])
def calculo_frecuencias_page():
    """Calcula frecuencias óptimas para productos clave con datos reales.
    Sebastián 14-may-2026: "cuanto vendemos al mes, y si incluye a
    fernando mesa, asi hacemos calculo reales".
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/calculo-frecuencias")
    from flask import Response
    return Response(_CALC_FRECUENCIAS_HTML, mimetype="text/html")


@bp.route("/api/plan/calculo-frecuencias", methods=["GET"])
def calculo_frecuencias_api():
    """Datos para cálculo manual de frecuencias.
    Combina Shopify (animus DTC) + pedidos B2B (Fernando + futuros).
    Query: ?productos=A,B,C  (default: top 5 por velocidad)
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()

    # Productos pedidos (default top 5 confirmados con Sebastián)
    productos_query = request.args.get("productos", "").strip()
    if productos_query:
        productos_solicitados = [p.strip() for p in productos_query.split(",") if p.strip()]
    else:
        productos_solicitados = [
            "LIMPIADOR FACIAL BHA 2%",
            "SUERO ILUMINADOR TRX",
            "SUERO HIDRATANTE AH 1.5%",
            "LIMPIADOR ILUMINADOR ACIDO KOJICO",
            "GEL HIDRATANTE",
        ]

    # 1) Necesidades DTC (Shopify)
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)
    nec_map = {n["producto_nombre"]: n for n in necesidades}

    # 2) Pedidos B2B (próximos 12 meses · todos no cancelados/despachados)
    b2b_por_producto = {}
    for r in c.execute(
        """SELECT producto_nombre, cliente_nombre,
                  SUM(cantidad_uds * COALESCE(ml_unidad, 30)) / 1000.0 AS kg_total,
                  COUNT(*) AS n_pedidos,
                  MIN(fecha_estimada) AS proxima_fecha
           FROM pedidos_b2b
           WHERE estado NOT IN ('despachado','cancelado')
           GROUP BY producto_nombre, cliente_nombre""",
    ).fetchall():
        b2b_por_producto.setdefault(r[0] or "", []).append({
            "cliente": r[1], "kg_total_pendiente": round(float(r[2] or 0), 2),
            "n_pedidos": int(r[3] or 0),
            "proxima_fecha": r[4],
        })

    # 3) Producciones reales últ 180d · para detectar frecuencia histórica
    rows_real = c.execute(
        """SELECT producto, fin_real_at, COALESCE(kg_real, cantidad_kg, 0)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= date('now','-5 hours','-180 day')
             AND COALESCE(kg_real, cantidad_kg, 0) > 0
           ORDER BY fin_real_at DESC""",
    ).fetchall()
    historico_por_prod = {}
    for r in rows_real:
        historico_por_prod.setdefault(r[0] or "", []).append({
            "fecha": (r[1] or "")[:10],
            "kg": float(r[2] or 0),
        })

    # 4) Lote_size_kg del Excel
    lote_excel = {}
    for r in c.execute(
        """SELECT producto_nombre, lote_size_kg
           FROM formula_headers WHERE COALESCE(activo, 1) = 1""",
    ).fetchall():
        lote_excel[r[0]] = float(r[1] or 0)

    # 5) Componer respuesta por producto
    items = []
    for prod in productos_solicitados:
        nec = nec_map.get(prod, {})
        vel_uds_dia_shopify = nec.get("velocidad_uds_dia", 0)
        ml = nec.get("ml_unidad", 30)
        kg_mes_shopify = round((vel_uds_dia_shopify * 30 * ml) / 1000.0, 2)

        b2b_list = b2b_por_producto.get(prod, [])
        kg_b2b_pendiente = sum(b["kg_total_pendiente"] for b in b2b_list)
        # Asumir B2B pendiente se distribuye en 3 meses · kg/mes b2b
        kg_mes_b2b = round(kg_b2b_pendiente / 3.0, 2)

        kg_mes_total = round(kg_mes_shopify + kg_mes_b2b, 2)

        # Frecuencia óptima · cuánto dura un lote
        lote = lote_excel.get(prod, 0)
        if kg_mes_total > 0.001 and lote > 0:
            dias_dura_lote = round((lote / kg_mes_total) * 30)
            # Producir 20 días antes de agotar
            frecuencia_optima = max(dias_dura_lote - BUFFER_REORDEN_DIAS, 15)
            # Lotes/año
            lotes_anuales = round(365 / frecuencia_optima, 1)
        else:
            dias_dura_lote = None
            frecuencia_optima = None
            lotes_anuales = None

        # Historial real · frecuencia histórica observada
        historial = historico_por_prod.get(prod, [])
        frecuencia_observada = None
        if len(historial) >= 2:
            from datetime import date as _date
            try:
                fechas = [_date.fromisoformat(h["fecha"][:10]) for h in historial]
                # Diferencia promedio entre producciones consecutivas
                diffs = [(fechas[i] - fechas[i+1]).days for i in range(len(fechas)-1)]
                frecuencia_observada = round(sum(diffs) / len(diffs))
            except Exception:
                pass

        items.append({
            "producto": prod,
            "ml_unidad": ml,
            "lote_excel_kg": lote,
            "shopify": {
                "velocidad_uds_dia": round(vel_uds_dia_shopify, 2),
                "velocidad_uds_mes": int(vel_uds_dia_shopify * 30),
                "kg_mes": kg_mes_shopify,
            },
            "b2b": {
                "kg_pendiente_total": round(kg_b2b_pendiente, 2),
                "kg_mes_estimado": kg_mes_b2b,
                "pedidos": b2b_list,
            },
            "consumo": {
                "kg_mes_total": kg_mes_total,
                "kg_anual_estimado": round(kg_mes_total * 12, 2),
            },
            "frecuencia": {
                "dias_dura_un_lote": dias_dura_lote,
                "frecuencia_optima_dias": frecuencia_optima,
                "lotes_anuales": lotes_anuales,
            },
            "historial_180d": {
                "n_producciones": len(historial),
                "frecuencia_observada_dias": frecuencia_observada,
                "ultima_fecha": historial[0]["fecha"] if historial else None,
                "ultima_kg": historial[0]["kg"] if historial else None,
                "producciones": historial[:5],
            },
            "stock_actual_kg": nec.get("stock_kg_total", 0),
            "dias_cobertura_actual": nec.get("dias_cobertura"),
        })

    return jsonify({
        "fecha": _hoy_colombia().isoformat(),
        "items": items,
        "n_productos": len(items),
    })


_CONFIG_CANONICOS_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Configurar canónicos · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:16px}
.wrap{max-width:1600px;margin:0 auto}
.card{background:white;border-radius:12px;padding:16px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:12px}
button{background:#0f766e;color:white;border:none;padding:9px 18px;border-radius:7px;font-size:13px;font-weight:700;cursor:pointer}
button.big{font-size:15px;padding:12px 28px}
button.secondary{background:#475569}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;padding:8px 6px;background:#f1f5f9;color:#475569;font-weight:700;position:sticky;top:0;border-bottom:2px solid #cbd5e1}
td{padding:6px;border-bottom:1px solid #f1f5f9;vertical-align:top}
tr:hover{background:#fafbff}
tr.modified{background:#fef9c3}
input.cell{width:100%;padding:5px 7px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;font-family:ui-monospace,monospace}
input.cell:focus{outline:none;border-color:#0f766e;background:#f0fdfa}
input.cell.dirty{background:#fef3c7;border-color:#ca8a04}
.urg-CRITICO{background:#fee2e2;color:#991b1b;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.urg-URGENTE{background:#fed7aa;color:#9a3412;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.urg-VIGILAR{background:#fef3c7;color:#854d0e;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.urg-OK{background:#dcfce7;color:#166534;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.urg-SIN_VENTAS{background:#f1f5f9;color:#64748b;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;margin-right:8px;text-align:center;min-width:90px}
.kpi-val{font-size:18px;font-weight:800}
.kpi-lbl{font-size:9px;color:#64748b;text-transform:uppercase}
.actions-bar{position:sticky;top:0;background:white;padding:10px 0;border-bottom:1px solid #e2e8f0;z-index:10;display:flex;gap:10px;justify-content:space-between;align-items:center}
.btn-sug{background:#0891b2;color:white;border:none;padding:2px 6px;border-radius:3px;font-size:10px;cursor:pointer;margin-left:4px}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>⚙ Configurar canónicos · todos los productos</h1>
  <div class="muted">Llená kg/lote, ml de presentación y frecuencia para cada producto. El sistema calcula sugerencia con ventas reales (Shopify + B2B) · podés aceptarla con click en el chip 💡.</div>
  <div id="kpis" style="margin-top:12px"></div>
</div>

<div class="card">
  <div class="actions-bar">
    <div>
      <button onclick="cargar()" class="secondary">↻ Recargar</button>
      <button onclick="aplicarSugeridos()" class="secondary">💡 Aplicar TODOS los sugeridos</button>
      <button onclick="limpiarDuplicados()" style="background:#dc2626;color:white;font-size:12px;padding:9px 18px;border:none;border-radius:7px;font-weight:700;cursor:pointer">🧹 Limpiar duplicados</button>
    </div>
    <div>
      <span id="modif-count" style="margin-right:10px;color:#ca8a04;font-weight:700"></span>
      <button onclick="guardar()" class="big" id="btn-guardar" disabled>💾 Guardar cambios</button>
      <button onclick="regenerarCanonicos()" style="background:#16a34a;color:white;font-size:15px;padding:12px 28px;border:none;border-radius:7px;font-weight:700;cursor:pointer;margin-left:10px">🔄 Regenerar simple</button>
      <button onclick="planPerfecto()" style="background:linear-gradient(135deg,#0f766e,#0891b2);color:white;font-size:15px;padding:12px 28px;border:none;border-radius:7px;font-weight:700;cursor:pointer;margin-left:10px;box-shadow:0 3px 10px rgba(8,145,178,.35)">🎯 Generar Plan PERFECTO</button>
    </div>
  </div>

  <div style="overflow-x:auto;margin-top:8px">
    <table id="tabla">
      <thead><tr>
        <th>Producto</th>
        <th>Urgencia</th>
        <th>Histórico<br>kg/lote</th>
        <th style="background:#dcfce7">kg/lote<br>REAL</th>
        <th style="background:#dcfce7">ml<br>presentación</th>
        <th>Sugerida<br>freq d</th>
        <th style="background:#dcfce7">Frecuencia<br>días</th>
        <th>Shopify<br>kg/mes</th>
        <th>B2B<br>kg/mes</th>
        <th>Total<br>kg/mes</th>
        <th>Stock<br>actual kg</th>
        <th>Cob<br>días</th>
        <th>Notas</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</div>

</div>
<script>
let DATA = null;
let DIRTY = new Set();

function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function getCSRF(){return document.cookie.split(';').find(c=>c.trim().startsWith('csrf_token='))?.split('=')[1] || '';}

async function cargar(){
  document.getElementById('tbody').innerHTML = '<tr><td colspan="13" style="text-align:center;padding:30px;color:#64748b">Cargando…</td></tr>';
  try {
    const r = await fetch('/api/plan/configurar-canonicos');
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    DATA = d;
    DIRTY.clear();
    render();
    actualizarBtnGuardar();
  } catch(e){ alert('Error: ' + e.message); }
}

function render(){
  const items = (DATA.items || []).sort((a,b) => {
    const ORD = {CRITICO:0, URGENTE:1, VIGILAR:2, OK:3, SIN_VENTAS:4};
    return (ORD[a.urgencia] || 9) - (ORD[b.urgencia] || 9);
  });
  // KPIs
  let kpis = '';
  kpis += '<span class="kpi"><div class="kpi-lbl">Total productos</div><div class="kpi-val">' + items.length + '</div></span>';
  const conConfig = items.filter(it => it.kg_lote_actual > 0).length;
  kpis += '<span class="kpi"><div class="kpi-lbl">✅ Configurados</div><div class="kpi-val" style="color:#16a34a">' + conConfig + '</div></span>';
  kpis += '<span class="kpi"><div class="kpi-lbl">⚠ Por configurar</div><div class="kpi-val" style="color:#ca8a04">' + (items.length - conConfig) + '</div></span>';
  const conB2B = items.filter(it => it.b2b_n_pedidos > 0).length;
  kpis += '<span class="kpi"><div class="kpi-lbl">🤝 Con B2B</div><div class="kpi-val" style="color:#7c3aed">' + conB2B + '</div></span>';
  document.getElementById('kpis').innerHTML = kpis;

  // Tabla
  let html = '';
  items.forEach((it, idx) => {
    const cls = DIRTY.has(it.producto) ? 'modified' : '';
    html += '<tr class="' + cls + '" data-prod="' + esc(it.producto) + '" data-idx="' + idx + '">';
    html += '<td><strong>' + esc(it.producto) + '</strong>';
    if (it.actualizado_por) html += '<br><span class="muted" style="font-size:9px">✓ ' + (it.actualizado_at || '').slice(0,16) + '</span>';
    html += '</td>';
    html += '<td><span class="urg-' + it.urgencia + '">' + it.urgencia + '</span></td>';
    html += '<td style="text-align:right">' + (it.histor_kg_prom || '—') + (it.histor_n > 0 ? '<br><span class="muted" style="font-size:9px">' + it.histor_n + ' lotes</span>' : '') + '</td>';
    html += '<td><input class="cell" type="number" step="0.1" min="0" value="' + (it.kg_lote_actual || it.histor_kg_prom || it.lote_excel_kg || 0) + '" data-field="kg" oninput="onChange(this)"></td>';
    html += '<td><input class="cell" type="number" min="1" value="' + it.ml_actual + '" data-field="ml" oninput="onChange(this)"></td>';
    html += '<td style="text-align:right;color:#0891b2;font-weight:700">' + (it.frecuencia_sugerida || '—') + (it.frecuencia_sugerida ? ' <button class="btn-sug" onclick="aplicarSug(this)">💡</button>' : '') + '</td>';
    html += '<td><input class="cell" type="number" min="0" value="' + (it.frecuencia_actual || '') + '" data-field="freq" oninput="onChange(this)" placeholder="días"></td>';
    html += '<td style="text-align:right">' + it.kg_mes_shopify + '</td>';
    html += '<td style="text-align:right;color:' + (it.b2b_n_pedidos > 0 ? '#7c3aed' : '#94a3b8') + '">' + it.kg_mes_b2b + (it.b2b_n_pedidos > 0 ? '<br><span class="muted" style="font-size:9px">' + it.b2b_n_pedidos + ' ped</span>' : '') + '</td>';
    html += '<td style="text-align:right;font-weight:700;color:#16a34a">' + it.kg_mes_total + '</td>';
    html += '<td style="text-align:right">' + (it.stock_kg || 0) + '</td>';
    html += '<td style="text-align:right">' + (it.dias_cobertura !== null ? it.dias_cobertura + 'd' : '—') + '</td>';
    html += '<td><input class="cell" type="text" value="' + esc(it.notas || '') + '" data-field="notas" oninput="onChange(this)" placeholder="opcional" style="min-width:120px"></td>';
    html += '</tr>';
  });
  document.getElementById('tbody').innerHTML = html;
}

function onChange(input){
  const tr = input.closest('tr');
  const prod = tr.dataset.prod;
  DIRTY.add(prod);
  tr.classList.add('modified');
  input.classList.add('dirty');
  actualizarBtnGuardar();
}

function aplicarSug(btn){
  const tr = btn.closest('tr');
  const idx = parseInt(tr.dataset.idx);
  const it = DATA.items.sort((a,b) => {
    const ORD = {CRITICO:0, URGENTE:1, VIGILAR:2, OK:3, SIN_VENTAS:4};
    return (ORD[a.urgencia] || 9) - (ORD[b.urgencia] || 9);
  })[idx];
  if (!it) return;
  const inp = tr.querySelector('input[data-field="freq"]');
  inp.value = it.frecuencia_sugerida;
  onChange(inp);
}

function aplicarSugeridos(){
  if (!confirm('¿Aplicar frecuencia sugerida a TODOS los productos con cálculo válido?')) return;
  document.querySelectorAll('tbody tr').forEach(tr => {
    const idx = parseInt(tr.dataset.idx);
    const it = (DATA.items.sort((a,b) => {
      const ORD = {CRITICO:0, URGENTE:1, VIGILAR:2, OK:3, SIN_VENTAS:4};
      return (ORD[a.urgencia] || 9) - (ORD[b.urgencia] || 9);
    }))[idx];
    if (it && it.frecuencia_sugerida > 0){
      const inp = tr.querySelector('input[data-field="freq"]');
      if (inp.value != it.frecuencia_sugerida){
        inp.value = it.frecuencia_sugerida;
        onChange(inp);
      }
    }
  });
}

function actualizarBtnGuardar(){
  const n = DIRTY.size;
  document.getElementById('btn-guardar').disabled = n === 0;
  document.getElementById('modif-count').textContent = n > 0 ? n + ' productos modificados' : '';
}

async function limpiarDuplicados(){
  if (!confirm('🧹 Limpiar duplicados\\n\\nDetecta lotes activos del mismo producto a ±21 días.\\nConserva el de mayor prioridad (eos_plan > canónico > calendar > manual)\\ny cancela el resto.\\n\\n¿Continuar?')) return;
  // Fix B-6 · disable propio + finally
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/plan/limpiar-duplicados', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: '{}',
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    let msg = '🧹 Limpieza completa\\n\\n';
    msg += '• Duplicados detectados: ' + d.duplicados_detectados + '\\n';
    msg += '• Canceladas: ' + d.canceladas + '\\n';
    if (d.detalle && d.detalle.length){
      msg += '\\nPrimeros casos:\\n';
      d.detalle.slice(0, 10).forEach(c => {
        msg += '• ' + c.producto + ': cancelar ' + c.cancela.origen + ' (' + c.cancela.fecha + ') · conserva ' + c.conserva.origen + ' (' + c.conserva.fecha + ')\\n';
      });
    }
    alert(msg);
  } catch(e){ alert('Error: ' + e.message); }
  finally { btns.forEach(b => b.disabled = false); actualizarBtnGuardar(); }
}

async function planPerfecto(){
  if (DIRTY.size > 0){
    if (!confirm('Tenés ' + DIRTY.size + ' cambios sin guardar · ¿guardar ANTES?')) return;
    await guardar();
  }
  if (!confirm('\\u26a0\\ufe0f GENERAR PLAN PERFECTO\\n\\nEsto CANCELA todas las producciones SUGERIDAS no iniciadas (canonicas / calendar) y arma el plan de cero para 12 meses.\\n\\nLo que vos FIJASTE (arrastraste o editaste en el calendario) NO se toca.\\n\\n¿Continuar?')) return;
  // Fix B-5 · disable todos los botones + finally
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/plan/generar-plan-perfecto', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({usar_ia: true, horizonte_dias: 365}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    let msg = '✅ Plan PERFECTO generado\\n\\n';
    msg += '• Productos config: ' + d.n_productos_config + '\\n';
    msg += '• Lotes viejos cancelados: ' + d.n_lotes_cancelados_viejos + '\\n';
    msg += '• Lotes nuevos: ' + d.n_lotes_generados_nuevos + '\\n';
    msg += '• Ajustes por velocidad: ' + d.n_ajustes_velocidad + '\\n';
    msg += '• Conflictos: ' + d.n_conflictos + '\\n\\n';
    if (d.reporte_ia){
      msg += '🤖 REPORTE IA:\\n\\n' + d.reporte_ia;
    } else if (d.ia_error){
      msg += '⚠ IA: ' + d.ia_error;
    }
    alert(msg);
  } catch(e){ alert('Error: ' + e.message); }
  finally { btns.forEach(b => b.disabled = false); actualizarBtnGuardar(); }
}

async function regenerarCanonicos(){
  if (DIRTY.size > 0){
    if (!confirm('Tenés ' + DIRTY.size + ' cambios sin guardar · ¿guardar ANTES de regenerar?')) return;
    await guardar();
  }
  if (!confirm('\\u26a0\\ufe0f REGENERAR CANONICOS\\n\\nEsto CANCELA todas las producciones canonicas SUGERIDAS no iniciadas y genera lotes nuevos para 12 meses.\\n\\nLo que vos FIJASTE (arrastraste o editaste en el calendario) NO se toca.\\n\\n¿Continuar?')) return;
  // Fix B-5 · disable todos los botones durante fetch
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/plan/regenerar-canonicos', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: '{}',
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    let msg = '✅ Canónicos regenerados\\n\\n';
    msg += '• Productos config: ' + d.n_productos_config + '\\n';
    msg += '• Lotes viejos cancelados: ' + d.n_lotes_cancelados_viejos + '\\n';
    msg += '• Lotes nuevos generados: ' + d.n_lotes_generados_nuevos + '\\n\\n';
    msg += 'Ver detalle en /admin/dashboard-plan';
    alert(msg);
  } catch(e){ alert('Error: ' + e.message); }
  finally { btns.forEach(b => b.disabled = false); actualizarBtnGuardar(); }
}

async function guardar(){
  if (DIRTY.size === 0) return;
  if (!confirm('¿Guardar ' + DIRTY.size + ' productos modificados?')) return;
  const items = [];
  document.querySelectorAll('tbody tr.modified').forEach(tr => {
    const prod = tr.dataset.prod;
    items.push({
      producto: prod,
      kg_por_lote: parseFloat(tr.querySelector('input[data-field="kg"]').value || 0),
      ml_unidad: parseInt(tr.querySelector('input[data-field="ml"]').value || 30),
      frecuencia_dias: parseInt(tr.querySelector('input[data-field="freq"]').value || 0),
      notas: tr.querySelector('input[data-field="notas"]').value || '',
      activo: true,
    });
  });
  try {
    const r = await fetch('/api/plan/configurar-canonicos', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({items: items}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    alert('✓ Guardados ' + d.saved + ' productos');
    cargar();
  } catch(e){ alert('Error: ' + e.message); }
}

cargar();
</script>
</body></html>"""


_CALC_FRECUENCIAS_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Cálculo de frecuencias · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1400px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
h2{margin:0 0 10px;color:#1e293b;font-size:16px}
.muted{color:#64748b;font-size:12px}
button{background:#0f766e;color:white;border:none;padding:8px 14px;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer}
.prod-card{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:10px}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin:10px 0}
.metric{background:#f8fafc;border-radius:6px;padding:10px;border-left:3px solid #cbd5e1}
.metric.shopify{border-left-color:#0891b2}
.metric.b2b{border-left-color:#7c3aed}
.metric.total{border-left-color:#16a34a;background:#f0fdf4}
.metric.freq{border-left-color:#ca8a04;background:#fefce8}
.metric-lbl{font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700}
.metric-val{font-size:18px;font-weight:800;color:#1e293b;margin-top:2px}
.metric-sub{font-size:10px;color:#64748b;margin-top:2px}
textarea{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;font-family:ui-monospace,monospace;min-height:80px}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>📐 Cálculo de frecuencias con datos reales</h1>
  <div class="muted">Combina ventas Shopify (Animus DTC) + pedidos B2B (Fernando Mesa, etc) para calcular cuánto vende cada producto/mes y derivar frecuencia óptima de producción.</div>
  <div style="margin-top:14px">
    <label class="muted">Productos (una línea por nombre · vacío = top 5 default):</label>
    <textarea id="productos">LIMPIADOR FACIAL BHA 2%
SUERO ILUMINADOR TRX
SUERO HIDRATANTE AH 1.5%
LIMPIADOR ILUMINADOR ACIDO KOJICO
GEL HIDRATANTE</textarea>
    <button onclick="cargar()" style="margin-top:8px">📊 Calcular</button>
  </div>
</div>

<div id="resultado"></div>

</div>
<script>
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function cargar(){
  const txt = document.getElementById('productos').value || '';
  const productos = txt.split('\n').map(s => s.trim()).filter(s => s).join(',');
  document.getElementById('resultado').innerHTML = '<div class="card">⏳ Calculando…</div>';
  try {
    const r = await fetch('/api/plan/calculo-frecuencias?productos=' + encodeURIComponent(productos));
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    render(d);
  } catch(e){ alert('Error: ' + e.message); }
}
function render(d){
  let html = '';
  (d.items || []).forEach(it => {
    const s = it.shopify, b = it.b2b, c = it.consumo, f = it.frecuencia, h = it.historial_180d;
    html += '<div class="prod-card">';
    html += '<h2>' + esc(it.producto) + ' <span class="muted">· ' + it.ml_unidad + 'ml · lote ' + it.lote_excel_kg + 'kg</span></h2>';
    html += '<div class="metric-grid">';
    html += '<div class="metric shopify"><div class="metric-lbl">🛍 Shopify Animus DTC</div><div class="metric-val">' + s.kg_mes + ' kg/mes</div><div class="metric-sub">' + s.velocidad_uds_dia + ' uds/día · ' + s.velocidad_uds_mes + ' uds/mes</div></div>';
    html += '<div class="metric b2b"><div class="metric-lbl">🤝 B2B (Fernando + futuros)</div><div class="metric-val">' + b.kg_mes_estimado + ' kg/mes</div><div class="metric-sub">' + b.kg_pendiente_total + ' kg pendiente / 3 meses</div></div>';
    html += '<div class="metric total"><div class="metric-lbl">📦 TOTAL consumo</div><div class="metric-val">' + c.kg_mes_total + ' kg/mes</div><div class="metric-sub">' + c.kg_anual_estimado + ' kg/año</div></div>';
    html += '<div class="metric freq"><div class="metric-lbl">🎯 Frecuencia óptima</div><div class="metric-val">' + (f.frecuencia_optima_dias ? 'cada ' + f.frecuencia_optima_dias + 'd' : '—') + '</div><div class="metric-sub">' + (f.lotes_anuales ? f.lotes_anuales + ' lotes/año' : '') + (f.dias_dura_un_lote ? ' · 1 lote dura ' + f.dias_dura_un_lote + 'd' : '') + '</div></div>';
    html += '</div>';

    // Histórico
    if (h.n_producciones > 0) {
      html += '<div style="background:#f1f5f9;border-radius:6px;padding:10px;margin-top:6px;font-size:11px"><strong>📜 Histórico últ 180d:</strong> ' + h.n_producciones + ' producciones';
      if (h.frecuencia_observada_dias) html += ' · frecuencia observada: cada ' + h.frecuencia_observada_dias + ' días';
      html += '<br>Producciones: ' + h.producciones.map(p => p.fecha + ' (' + p.kg + 'kg)').join(', ');
      html += '</div>';
    }

    // B2B detail
    if (b.pedidos && b.pedidos.length) {
      html += '<div style="background:#faf5ff;border-radius:6px;padding:10px;margin-top:6px;font-size:11px"><strong>🤝 Pedidos B2B activos:</strong><br>';
      b.pedidos.forEach(p => {
        html += '• ' + esc(p.cliente) + ' · ' + p.n_pedidos + ' pedido(s) · ' + p.kg_total_pendiente + 'kg pendiente · próx ' + (p.proxima_fecha || '—') + '<br>';
      });
      html += '</div>';
    } else {
      html += '<div class="muted" style="font-size:11px;margin-top:4px">🤝 Sin pedidos B2B activos para este producto</div>';
    }

    // Stock + cobertura
    html += '<div style="margin-top:6px;font-size:11px;color:#475569">Stock actual: <strong>' + it.stock_actual_kg + ' kg</strong> · Cobertura: <strong>' + (it.dias_cobertura_actual || '—') + ' días</strong></div>';

    html += '</div>';
  });
  document.getElementById('resultado').innerHTML = html;
}
cargar();
</script>
</body></html>"""


@bp.route("/admin/dashboard-plan", methods=["GET"])
def dashboard_plan_page():
    """Dashboard ejecutivo · vista 1 página con todo el plan + alertas.

    Sebastián 14-may-2026: paso 4/6.
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/dashboard-plan")
    from flask import Response
    return Response(_DASHBOARD_PLAN_HTML, mimetype="text/html")


@bp.route("/api/plan/dashboard", methods=["GET"])
def plan_dashboard_api():
    """Dashboard ejecutivo · datos agregados para 1 vista."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()

    # 1) Plan próximas 4 semanas · agrupado por semana
    rows_sem = c.execute(
        """SELECT date(fecha_programada,'weekday 1','-7 day') AS semana_lunes,
                  COUNT(*) AS n_lotes,
                  COALESCE(SUM(cantidad_kg),0) AS total_kg,
                  GROUP_CONCAT(producto || '|' || cantidad_kg || '|' || fecha_programada || '|' || origen, '~~')
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','en_curso','esperando_recurso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
             AND date(fecha_programada) <= date('now','-5 hours','+28 day')
           GROUP BY semana_lunes
           ORDER BY semana_lunes""",
    ).fetchall()
    semanas = []
    for r in rows_sem:
        lotes_detalle = []
        for entry in (r[3] or "").split("~~"):
            parts = entry.split("|")
            if len(parts) == 4:
                lotes_detalle.append({
                    "producto": parts[0],
                    "kg": float(parts[1] or 0),
                    "fecha": parts[2][:10],
                    "origen": parts[3],
                })
        semanas.append({
            "semana_lunes": r[0],
            "n_lotes": int(r[1] or 0),
            "total_kg": round(float(r[2] or 0), 2),
            "lotes": sorted(lotes_detalle, key=lambda x: x["fecha"]),
        })

    # 2) Resumen 12 meses · canónicos + Calendar + eos_plan activos
    row_12m = c.execute(
        """SELECT COUNT(*) AS n,
                  COALESCE(SUM(cantidad_kg),0) AS total_kg
           FROM produccion_programada
           WHERE estado IN ('pendiente','programado','en_curso','esperando_recurso')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now','-5 hours')
             AND date(fecha_programada) <= date('now','-5 hours','+365 day')""",
    ).fetchone()

    # 3) Producciones reales últimas 4 semanas (back-fills + completados)
    rows_real = c.execute(
        """SELECT producto, fin_real_at, COALESCE(kg_real, cantidad_kg, 0), origen
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND date(fin_real_at) >= date('now','-5 hours','-28 day')
           ORDER BY fin_real_at DESC""",
    ).fetchall()
    reales = [{
        "producto": r[0], "fecha": (r[1] or "")[:10],
        "kg": float(r[2] or 0), "origen": r[3],
    } for r in rows_real]

    # 4) Alertas · productos críticos
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)
    criticos = [n for n in necesidades if n["urgencia"] in ("CRITICO", "URGENTE")]
    alertas = []
    for n in criticos[:15]:
        alertas.append({
            "producto": n["producto_nombre"],
            "urgencia": n["urgencia"],
            "dias_cobertura": n["dias_cobertura"],
            "stock_kg": n["stock_kg_total"],
            "tiene_lote_agendado": n.get("tiene_plan_activo", False),
            "tiene_pausa": n.get("tiene_pausa", False),
        })

    # 5b) Últimas sugerencias IA (no obsoletas) + última corrida
    rows_ia = c.execute(
        """SELECT producto_nombre, sugerencia_kg, sugerencia_fecha,
                  motivo_ia, confianza_ia, accion_usuario, fecha_decision
           FROM autoplan_decisiones
           WHERE fecha_decision >= datetime('now','-5 hours','-7 day')
             AND COALESCE(accion_usuario, '') NOT IN ('obsoleta_mig131', 'cancelada', 'ignorada')
           ORDER BY fecha_decision DESC, confianza_ia DESC
           LIMIT 10""",
    ).fetchall()
    ia_sugerencias = [{
        "producto": r[0], "kg": float(r[1] or 0), "fecha": r[2],
        "motivo": r[3], "confianza": float(r[4] or 0) if r[4] else None,
        "accion": r[5], "fecha_decision": (r[6] or "")[:16],
    } for r in rows_ia]

    # 5c) Estadísticas de la IA (aprendizaje)
    row_stats = c.execute(
        """SELECT
             COUNT(CASE WHEN accion_usuario='aceptada' THEN 1 END) AS aceptadas,
             COUNT(CASE WHEN accion_usuario='movida' THEN 1 END) AS movidas,
             COUNT(CASE WHEN accion_usuario='cancelada' THEN 1 END) AS canceladas,
             COUNT(CASE WHEN accion_usuario='ignorada' THEN 1 END) AS ignoradas,
             COUNT(CASE WHEN accion_usuario IS NULL THEN 1 END) AS pendientes
           FROM autoplan_decisiones""",
    ).fetchone()
    ia_stats = {
        "aceptadas": int(row_stats[0] or 0),
        "movidas": int(row_stats[1] or 0),
        "canceladas": int(row_stats[2] or 0),
        "ignoradas": int(row_stats[3] or 0),
        "pendientes": int(row_stats[4] or 0),
    }

    # 5) KPIs
    n_canonicos = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE origen = 'eos_canonico'
             AND estado IN ('pendiente','programado')
             AND fin_real_at IS NULL"""
    ).fetchone()[0]
    n_calendar_legacy = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE origen IN ('calendar','manual')
             AND estado IN ('pendiente','programado')
             AND fin_real_at IS NULL"""
    ).fetchone()[0]
    n_pausados = c.execute(
        """SELECT COUNT(*) FROM produccion_programada
           WHERE estado = 'esperando_recurso'"""
    ).fetchone()[0]

    # 6) Alertas de ventas que aumentaron (paso 6/6 · IA-alerta inline)
    alertas_ventas_data = []
    try:
        nec_rec = _calcular_animus_dtc(c, ventana=14, cob_critico=20,
                                         cob_alerta=25, cob_vigilar=45)
        rec_map = {n["producto_nombre"]: n for n in nec_rec}
        for n_bl in necesidades:
            prod = n_bl["producto_nombre"]
            n_rc = rec_map.get(prod, {})
            vel_bl = n_bl.get("velocidad_kg_dia", 0) or 0
            vel_rc = n_rc.get("velocidad_kg_dia", 0) or 0
            if vel_bl < 0.01 or vel_rc < 0.01:
                continue
            delta_pct = ((vel_rc - vel_bl) / vel_bl) * 100.0
            if delta_pct < 30:
                continue
            stock_kg = n_bl.get("stock_kg_total", 0) or 0
            cob_rec = stock_kg / vel_rc if vel_rc > 0 else None
            severidad = (
                "CRITICO" if cob_rec and cob_rec < 15
                else "URGENTE" if cob_rec and cob_rec < 25
                else "BOOM" if delta_pct > 100
                else "ACELERACION"
            )
            alertas_ventas_data.append({
                "producto": prod,
                "delta_pct": round(delta_pct, 1),
                "cob_ajustada_dias": round(cob_rec, 1) if cob_rec is not None else None,
                "severidad": severidad,
            })
        alertas_ventas_data.sort(key=lambda x: (
            {"CRITICO": 0, "URGENTE": 1, "BOOM": 2, "ACELERACION": 3}.get(x["severidad"], 9),
            x.get("cob_ajustada_dias") or 99999,
        ))
    except Exception:
        pass  # silencioso · si falla, no rompe el dashboard

    return jsonify({
        "fecha": _hoy_colombia().isoformat(),
        "kpis": {
            "lotes_proximas_4_sem": sum(s["n_lotes"] for s in semanas),
            "kg_proximas_4_sem": round(sum(s["total_kg"] for s in semanas), 2),
            "lotes_proximos_12_meses": int(row_12m[0] or 0),
            "kg_proximos_12_meses": round(float(row_12m[1] or 0), 2),
            "canonicos_activos": int(n_canonicos or 0),
            "calendar_legacy_pendientes": int(n_calendar_legacy or 0),
            "pausados": int(n_pausados or 0),
            "criticos": len(criticos),
            "alertas_ventas_aumento": len(alertas_ventas_data),
        },
        "semanas": semanas,
        "producciones_reales_28d": reales,
        "alertas_criticos": alertas,
        "alertas_ventas_aumento": alertas_ventas_data[:10],
        "ia_sugerencias_recientes": ia_sugerencias,
        "ia_stats": ia_stats,
    })


_DASHBOARD_PLAN_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Dashboard ejecutivo · Plan EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:18px}
.wrap{max-width:1500px;margin:0 auto}
.card{background:white;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 4px;color:#0f766e;font-size:22px}
h2{margin:0 0 10px;color:#475569;font-size:15px}
.muted{color:#64748b;font-size:12px}
button{background:#0f766e;color:white;border:none;padding:8px 14px;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}
.kpi{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px;text-align:center}
.kpi.urgent{border-color:#dc2626;background:#fef2f2}
.kpi.warn{border-color:#ca8a04;background:#fefce8}
.kpi.good{border-color:#16a34a;background:#f0fdf4}
.kpi-lbl{font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700}
.kpi-val{font-size:26px;font-weight:800;margin-top:4px}
.semana-card{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:12px;margin-bottom:8px}
.semana-head{display:flex;justify-content:space-between;align-items:center;padding-bottom:8px;border-bottom:1px solid #f1f5f9;margin-bottom:8px}
.lote-row{display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px dashed #f1f5f9}
.lote-row:last-child{border:none}
.tag{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;font-weight:700}
.tag-canonico{background:#e0e7ff;color:#3730a3}
.tag-eos_plan{background:#dcfce7;color:#166534}
.tag-calendar{background:#fef9c3;color:#854d0e}
.tag-manual{background:#fef3c7;color:#854d0e}
.tag-eos_retroactivo{background:#f1f5f9;color:#475569}
.urgencia-CRITICO{background:#fee2e2;color:#991b1b}
.urgencia-URGENTE{background:#fed7aa;color:#9a3412}
.alerta-row{display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:6px;margin-bottom:4px;background:#f8fafc;border-left:3px solid #dc2626}
.alerta-row.con-plan{border-left-color:#16a34a;background:#f0fdf4}
.cols-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.cols-2{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>📊 Dashboard ejecutivo · Plan EOS</h1>
  <div class="muted">Vista única · plan + alertas + producciones reales · actualizado en vivo</div>
  <div style="margin-top:10px"><button onclick="cargar()">↻ Recargar</button></div>
  <div id="kpis" class="kpi-grid"></div>
</div>

<div id="alertas-ventas-wrap"></div>

<div class="card" style="background:linear-gradient(135deg,#fef3c7,#fef9c3);border:2px solid #ca8a04">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
    <div>
      <h2 style="margin:0;color:#854d0e">🤖 Autoplan con IA · Claude Sonnet 4.6</h2>
      <div class="muted">Cruza ventas Shopify + fórmulas Excel + Calendar + tu feedback histórico</div>
    </div>
    <div>
      <a href="/admin/plan-calendario" target="_blank" style="background:#ca8a04;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">▶ Ir al Calendario IA</a>
    </div>
  </div>
  <div id="ia-stats" style="margin-top:10px"></div>
  <div id="ia-sugerencias" style="margin-top:10px"></div>
</div>

<div class="cols-2">
  <div>
    <div class="card">
      <h2>📅 Próximas 4 semanas</h2>
      <div id="semanas"></div>
    </div>
  </div>
  <div>
    <div class="card">
      <h2>🚨 Productos críticos (≤25 días cobertura)</h2>
      <div id="alertas"></div>
    </div>
    <div class="card">
      <h2>✅ Producciones reales últimas 4 semanas</h2>
      <div id="reales"></div>
    </div>
  </div>
</div>

</div>
<script>
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function cargar(){
  try {
    const r = await fetch('/api/plan/dashboard');
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    render(d);
  } catch(e){ alert('Error: ' + e.message); }
}
function render(d){
  const k = d.kpis;
  let html = '';
  html += '<div class="kpi"><div class="kpi-lbl">Próximas 4 sem</div><div class="kpi-val" style="color:#0f766e">' + k.lotes_proximas_4_sem + '</div><div class="muted">' + k.kg_proximas_4_sem + ' kg</div></div>';
  html += '<div class="kpi"><div class="kpi-lbl">Próximos 12 m</div><div class="kpi-val" style="color:#0891b2">' + k.lotes_proximos_12_meses + '</div><div class="muted">' + k.kg_proximos_12_meses + ' kg</div></div>';
  html += '<div class="kpi good"><div class="kpi-lbl">🔁 Canónicos</div><div class="kpi-val" style="color:#16a34a">' + k.canonicos_activos + '</div></div>';
  html += '<div class="kpi warn"><div class="kpi-lbl">📆 Calendar legacy</div><div class="kpi-val" style="color:#ca8a04">' + k.calendar_legacy_pendientes + '</div></div>';
  html += '<div class="kpi warn"><div class="kpi-lbl">⏸ Pausados</div><div class="kpi-val" style="color:#ca8a04">' + k.pausados + '</div></div>';
  const urg = k.criticos > 0;
  html += '<div class="kpi ' + (urg ? 'urgent' : 'good') + '"><div class="kpi-lbl">🚨 Críticos</div><div class="kpi-val" style="color:' + (urg ? '#dc2626' : '#16a34a') + '">' + k.criticos + '</div></div>';
  const ventasAlerts = k.alertas_ventas_aumento || 0;
  html += '<div class="kpi ' + (ventasAlerts > 0 ? 'urgent' : 'good') + '"><div class="kpi-lbl">📈 Ventas ↑</div><div class="kpi-val" style="color:' + (ventasAlerts > 0 ? '#dc2626' : '#16a34a') + '">' + ventasAlerts + '</div></div>';
  document.getElementById('kpis').innerHTML = html;

  // Alertas ventas que aumentaron
  const ventasArr = d.alertas_ventas_aumento || [];
  if (ventasArr.length) {
    let hv = '<div class="card" style="background:linear-gradient(135deg,#fef2f2,#fefce8);border:2px solid #ea580c"><h2 style="margin:0 0 6px;color:#9a3412">📈 Ventas en aumento · ' + ventasArr.length + ' producto(s) · adelantar producción</h2>';
    hv += '<div class="muted">Velocidad últ 14d supera baseline 60d en ≥30%. Si la cobertura ajustada cae <25d, hay riesgo de stockout antes del próximo canónico.</div>';
    ventasArr.forEach(a => {
      const sev = a.severidad;
      const col = sev === 'CRITICO' ? '#dc2626' : (sev === 'URGENTE' ? '#ea580c' : (sev === 'BOOM' ? '#7c3aed' : '#ca8a04'));
      hv += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:6px;margin-top:6px;background:white;border-left:4px solid ' + col + '">';
      hv += '<div><strong>' + esc(a.producto) + '</strong> <span style="background:' + col + ';color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700">' + sev + '</span></div>';
      hv += '<div style="font-size:12px;text-align:right"><span style="color:' + col + ';font-weight:800">+' + a.delta_pct + '%</span> ventas<br><span class="muted">cobertura ajustada: ' + (a.cob_ajustada_dias || '—') + 'd</span></div>';
      hv += '</div>';
    });
    hv += '</div>';
    // Insertar antes de la sección semanas
    const existente = document.getElementById('alertas-ventas-wrap');
    if (existente) existente.innerHTML = hv;
  } else {
    const existente = document.getElementById('alertas-ventas-wrap');
    if (existente) existente.innerHTML = '';
  }

  // Semanas
  let hs = '';
  (d.semanas || []).forEach(s => {
    hs += '<div class="semana-card"><div class="semana-head"><strong>Semana del ' + s.semana_lunes + '</strong><span class="muted">' + s.n_lotes + ' lotes · ' + s.total_kg + ' kg</span></div>';
    s.lotes.forEach(lt => {
      hs += '<div class="lote-row"><span><span class="tag tag-' + lt.origen + '">' + lt.origen + '</span> ' + esc(lt.producto) + '</span><span>' + lt.fecha.slice(5) + ' · ' + lt.kg + 'kg</span></div>';
    });
    hs += '</div>';
  });
  if (!d.semanas.length) hs = '<div class="muted">Sin lotes programados próximas 4 semanas</div>';
  document.getElementById('semanas').innerHTML = hs;

  // Alertas críticos
  let ha = '';
  (d.alertas_criticos || []).forEach(a => {
    const cls = a.tiene_lote_agendado ? 'con-plan' : '';
    const planTxt = a.tiene_lote_agendado ? '✅ con plan' : '⚠ sin plan';
    const pausa = a.tiene_pausa ? ' ⏸' : '';
    ha += '<div class="alerta-row ' + cls + '">';
    ha += '<div><span class="tag urgencia-' + a.urgencia + '">' + a.urgencia + '</span> <strong>' + esc(a.producto) + '</strong>' + pausa + '<br><span class="muted">' + a.dias_cobertura + 'd cobertura · ' + a.stock_kg + 'kg stock</span></div>';
    ha += '<div style="font-size:11px;color:' + (a.tiene_lote_agendado ? '#16a34a' : '#dc2626') + ';font-weight:700">' + planTxt + '</div>';
    ha += '</div>';
  });
  if (!d.alertas_criticos.length) ha = '<div class="muted" style="text-align:center;padding:20px;color:#16a34a">✅ Sin críticos</div>';
  document.getElementById('alertas').innerHTML = ha;

  // Producciones reales
  let hr = '';
  (d.producciones_reales_28d || []).forEach(p => {
    hr += '<div class="lote-row"><span><span class="tag tag-' + p.origen + '">' + p.origen + '</span> ' + esc(p.producto) + '</span><span>' + p.fecha + ' · ' + p.kg + 'kg</span></div>';
  });
  if (!d.producciones_reales_28d.length) hr = '<div class="muted">Sin producciones reales últimos 28 días</div>';
  document.getElementById('reales').innerHTML = hr;

  // IA stats + sugerencias
  const s = d.ia_stats || {};
  const totalAcciones = (s.aceptadas || 0) + (s.movidas || 0) + (s.canceladas || 0) + (s.ignoradas || 0);
  let hs2 = '<div style="display:flex;gap:8px;flex-wrap:wrap;font-size:12px">';
  hs2 += '<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:6px"><strong>' + (s.aceptadas || 0) + '</strong> aceptadas</span>';
  hs2 += '<span style="background:#fef3c7;color:#854d0e;padding:4px 10px;border-radius:6px"><strong>' + (s.movidas || 0) + '</strong> movidas</span>';
  hs2 += '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:6px"><strong>' + (s.canceladas || 0) + '</strong> canceladas</span>';
  hs2 += '<span style="background:#f1f5f9;color:#475569;padding:4px 10px;border-radius:6px"><strong>' + (s.ignoradas || 0) + '</strong> ignoradas</span>';
  hs2 += '<span style="background:#dbeafe;color:#1e40af;padding:4px 10px;border-radius:6px"><strong>' + (s.pendientes || 0) + '</strong> pendientes</span>';
  if (totalAcciones > 0) {
    const aceptPct = Math.round(((s.aceptadas || 0) / totalAcciones) * 100);
    hs2 += '<span style="margin-left:8px;color:#475569;font-style:italic">IA aprendizaje: ' + aceptPct + '% de sugerencias aceptadas</span>';
  }
  hs2 += '</div>';
  document.getElementById('ia-stats').innerHTML = hs2;

  const sugs = d.ia_sugerencias_recientes || [];
  if (sugs.length) {
    let hi = '<div style="font-weight:700;font-size:12px;margin-bottom:6px;color:#854d0e">Últimas sugerencias IA · click "Ir al Calendario IA" para confirmarlas:</div>';
    sugs.forEach(s => {
      const conf = s.confianza ? Math.round(s.confianza * 100) + '%' : '?';
      hi += '<div style="display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px dashed rgba(202,138,4,.3)"><span>' + esc(s.producto) + ' · ' + s.fecha + ' · ' + s.kg + 'kg</span><span style="color:#854d0e">conf ' + conf + ' · ' + (s.motivo || '') + '</span></div>';
    });
    document.getElementById('ia-sugerencias').innerHTML = hi;
  } else {
    document.getElementById('ia-sugerencias').innerHTML = '<div class="muted" style="font-size:11px;color:#854d0e">Sin sugerencias IA recientes · click "Ir al Calendario IA" y apretá "🤖 Autoplan con IA" para generar</div>';
  }
}
cargar();
</script>
</body></html>"""


@bp.route("/admin/validar-formulas", methods=["GET"])
def validar_formulas_page():
    """Auditoría de fórmulas · Sebastián 14-may-2026: "quiero que
    revisemos los frentes, que las formulas esten bien con la nueva
    logica que te puse" (Excel % puros sobre 100% · escala al lote real).
    """
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/validar-formulas")
    from flask import Response
    return Response(_VALIDAR_FORMULAS_HTML, mimetype="text/html")


@bp.route("/api/plan/validar-formulas", methods=["GET"])
def validar_formulas_api():
    """Para cada fórmula activa, verifica:
      - suma_gramos vs lote_size_kg × 1000 (debe sumar 100%)
      - items con cantidad_g_por_lote = 0
      - lote real promedio (de producciones_programadas con fin_real_at)
        vs lote_size_kg del Excel
      - score de salud: OK / WARNING / ERROR
    """
    err = _require_login()
    if err:
        return err

    conn = get_db()
    c = conn.cursor()

    # 1) Lista de fórmulas activas + datos clave
    rows_fh = c.execute(
        """SELECT producto_nombre, COALESCE(lote_size_kg, 0),
                  COALESCE(unidad_base_g, 0), COALESCE(activo, 1)
           FROM formula_headers
           ORDER BY producto_nombre""",
    ).fetchall()

    # 2) Suma de gramos + count items por producto
    sumas_items = {}
    for r in c.execute(
        """SELECT producto_nombre,
                  COALESCE(SUM(cantidad_g_por_lote), 0) as suma_g,
                  COUNT(*) as n_items,
                  COALESCE(SUM(CASE WHEN COALESCE(cantidad_g_por_lote,0)=0 THEN 1 ELSE 0 END), 0) as n_vacios,
                  COALESCE(SUM(CASE WHEN material_id IS NULL OR TRIM(material_id)='' THEN 1 ELSE 0 END), 0) as n_sin_codigo
           FROM formula_items
           GROUP BY producto_nombre""",
    ).fetchall():
        sumas_items[r[0]] = {
            "suma_g": float(r[1] or 0),
            "n_items": int(r[2] or 0),
            "n_vacios": int(r[3] or 0),
            "n_sin_codigo": int(r[4] or 0),
        }

    # 3) Lote real promedio · producciones completadas últ 180d
    lote_real_por_prod = {}
    for r in c.execute(
        """SELECT producto,
                  AVG(COALESCE(kg_real, cantidad_kg, 0)) as kg_promedio,
                  COUNT(*) as n_lotes,
                  MAX(fin_real_at) as ultima_fecha
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND COALESCE(kg_real, cantidad_kg, 0) > 0
             AND date(fin_real_at) >= date('now','-5 hours','-180 day')
           GROUP BY producto""",
    ).fetchall():
        lote_real_por_prod[r[0]] = {
            "kg_promedio": round(float(r[1] or 0), 2),
            "n_lotes": int(r[2] or 0),
            "ultima_fecha": (r[3] or "")[:10] if r[3] else None,
        }

    # 4) Componer reporte por producto
    items = []
    for fh in rows_fh:
        producto = fh[0]
        lote_excel = float(fh[1] or 0)
        activo = bool(fh[3])
        s = sumas_items.get(producto, {"suma_g": 0, "n_items": 0,
                                       "n_vacios": 0, "n_sin_codigo": 0})
        suma_kg = s["suma_g"] / 1000.0
        # Si lote_excel > 0, suma debería ser cercana
        # cobertura_% = (suma_kg / lote_excel) × 100
        if lote_excel > 0.001:
            cobertura_pct = (suma_kg / lote_excel) * 100.0
        else:
            cobertura_pct = 0

        real = lote_real_por_prod.get(producto, {})
        kg_real = real.get("kg_promedio", 0)

        # Score salud
        problemas = []
        if not activo:
            problemas.append("⚪ INACTIVO")
        if s["n_items"] == 0:
            problemas.append("❌ Sin items (fórmula vacía)")
        if s["n_vacios"] > 0:
            problemas.append(f"⚠ {s['n_vacios']} items con cantidad=0")
        if s["n_sin_codigo"] > 0:
            problemas.append(f"⚠ {s['n_sin_codigo']} items sin código MP")
        if lote_excel < 1:
            problemas.append(f"⚠ Lote Excel piloto ({lote_excel}kg < 1kg)")
        if lote_excel > 0 and abs(cobertura_pct - 100) > 5 and s["n_items"] > 0:
            problemas.append(f"⚠ Suma items = {round(cobertura_pct, 1)}% del lote (debería ser ~100%)")
        if kg_real > 0 and lote_excel > 0 and abs(kg_real - lote_excel) / lote_excel > 0.3:
            problemas.append(f"⚠ Lote real ({kg_real}kg) difiere >30% del Excel ({lote_excel}kg)")

        if not activo:
            score = "INACTIVO"
        elif any("❌" in p for p in problemas):
            score = "ERROR"
        elif problemas:
            score = "WARNING"
        else:
            score = "OK"

        items.append({
            "producto": producto,
            "activo": activo,
            "lote_size_kg_excel": lote_excel,
            "n_items": s["n_items"],
            "n_vacios": s["n_vacios"],
            "n_sin_codigo": s["n_sin_codigo"],
            "suma_kg_items": round(suma_kg, 2),
            "cobertura_pct": round(cobertura_pct, 1),
            "lote_real_kg_promedio": kg_real,
            "lote_real_n_producciones": real.get("n_lotes", 0),
            "lote_real_ultima_fecha": real.get("ultima_fecha"),
            "score": score,
            "problemas": problemas,
        })

    # Resumen
    by_score = {}
    for it in items:
        by_score[it["score"]] = by_score.get(it["score"], 0) + 1

    return jsonify({
        "total_formulas": len(items),
        "resumen_por_score": by_score,
        "items": items,
    })


_VALIDAR_FORMULAS_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Validar fórmulas · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1500px;margin:0 auto}
.card{background:white;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:12px}
button{background:#0f766e;color:white;border:none;padding:8px 14px;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:10px 8px;background:#f1f5f9;color:#475569;font-weight:700;position:sticky;top:0}
td{padding:8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:8px;margin-bottom:8px;text-align:center;min-width:120px;vertical-align:top}
.kpi-lbl{font-size:10px;color:#64748b;text-transform:uppercase}
.kpi-val{font-size:22px;font-weight:800}
.score-OK{background:#dcfce7;color:#166534;padding:3px 8px;border-radius:6px;font-weight:700;font-size:11px}
.score-WARNING{background:#fef3c7;color:#854d0e;padding:3px 8px;border-radius:6px;font-weight:700;font-size:11px}
.score-ERROR{background:#fee2e2;color:#991b1b;padding:3px 8px;border-radius:6px;font-weight:700;font-size:11px}
.score-INACTIVO{background:#f1f5f9;color:#64748b;padding:3px 8px;border-radius:6px;font-weight:700;font-size:11px}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;margin-right:3px}
.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,monospace}
.filter{display:inline-block;margin-right:14px;font-size:12px}
.filter input{margin-right:4px;vertical-align:middle}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>🧪 Auditoría de fórmulas · nueva lógica (% sobre 100%)</h1>
  <div class="muted">Verifica que las fórmulas del Excel mig 121 estén completas y que los lotes piloto coincidan con producciones reales · Sebastián 14-may-2026</div>
  <div style="margin-top:14px">
    <button onclick="cargar()">↻ Recargar</button>
  </div>
  <div id="kpis" style="margin-top:14px"></div>
  <div style="margin-top:8px">
    <span class="filter"><label><input type="checkbox" class="flt" value="OK" checked> ✅ OK</label></span>
    <span class="filter"><label><input type="checkbox" class="flt" value="WARNING" checked> ⚠ Warning</label></span>
    <span class="filter"><label><input type="checkbox" class="flt" value="ERROR" checked> ❌ Error</label></span>
    <span class="filter"><label><input type="checkbox" class="flt" value="INACTIVO"> ⚪ Inactivo</label></span>
  </div>
</div>

<div id="resultado"></div>

</div>
<script>
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let DATA = null;

async function cargar(){
  document.getElementById('resultado').innerHTML = '<div class="card">⏳ Analizando…</div>';
  try {
    const r = await fetch('/api/plan/validar-formulas');
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    DATA = d;
    render();
  } catch(e){ alert('Error: ' + e.message); }
}

document.addEventListener('change', e => {
  if (e.target.classList.contains('flt')) render();
});

function render(){
  if (!DATA) return;

  // KPIs
  const r = DATA.resumen_por_score || {};
  let k = '';
  k += '<span class="kpi"><div class="kpi-lbl">Total fórmulas</div><div class="kpi-val">' + DATA.total_formulas + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">✅ OK</div><div class="kpi-val" style="color:#16a34a">' + (r.OK || 0) + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">⚠ Warning</div><div class="kpi-val" style="color:#ca8a04">' + (r.WARNING || 0) + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">❌ Error</div><div class="kpi-val" style="color:#dc2626">' + (r.ERROR || 0) + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">⚪ Inactivo</div><div class="kpi-val" style="color:#64748b">' + (r.INACTIVO || 0) + '</div></span>';
  document.getElementById('kpis').innerHTML = k;

  // Filtros
  const activos = new Set(Array.from(document.querySelectorAll('.flt:checked')).map(x => x.value));

  // Ordenar: ERROR → WARNING → INACTIVO → OK
  const ORDEN = {ERROR: 0, WARNING: 1, INACTIVO: 2, OK: 3};
  const items = (DATA.items || []).filter(it => activos.has(it.score));
  items.sort((a, b) => (ORDEN[a.score] || 9) - (ORDEN[b.score] || 9));

  let html = '<div class="card">';
  html += '<table><thead><tr>';
  html += '<th>Producto</th>';
  html += '<th>Score</th>';
  html += '<th class="num">Lote Excel<br>(kg)</th>';
  html += '<th class="num">Lote real<br>histórico (kg)</th>';
  html += '<th class="num">N° items</th>';
  html += '<th class="num">Suma items<br>kg (=100%?)</th>';
  html += '<th class="num">Cobertura %</th>';
  html += '<th>Problemas detectados</th>';
  html += '</tr></thead><tbody>';

  items.forEach(it => {
    const cobertura = it.cobertura_pct || 0;
    const covColor = Math.abs(cobertura - 100) <= 5 ? '#166534' : '#dc2626';
    html += '<tr>';
    html += '<td><strong>' + escapeHtml(it.producto) + '</strong>';
    if (it.lote_real_ultima_fecha) html += '<br><span class="muted" style="font-size:10px">última real: ' + it.lote_real_ultima_fecha + ' · ' + it.lote_real_n_producciones + ' lote(s)</span>';
    html += '</td>';
    html += '<td><span class="score-' + it.score + '">' + it.score + '</span></td>';
    html += '<td class="num">' + it.lote_size_kg_excel.toFixed(2) + '</td>';
    html += '<td class="num">' + (it.lote_real_kg_promedio || '—') + '</td>';
    html += '<td class="num">' + it.n_items + (it.n_vacios > 0 ? ' <span style="color:#dc2626">(' + it.n_vacios + ' vacíos)</span>' : '') + '</td>';
    html += '<td class="num">' + it.suma_kg_items.toFixed(2) + ' kg</td>';
    html += '<td class="num" style="color:' + covColor + ';font-weight:700">' + cobertura + '%</td>';
    html += '<td style="font-size:11px;color:#7f1d1d">' + (it.problemas || []).map(p => escapeHtml(p)).join('<br>') + '</td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  html += '<div class="muted" style="margin-top:8px;font-size:11px">📝 Cobertura % = (suma kg items / lote Excel) × 100. Debería estar ~100% si la fórmula es completa.</div>';
  html += '</div>';
  document.getElementById('resultado').innerHTML = html;
}

cargar();
</script>
</body></html>"""


@bp.route("/api/plan/diagnostico-mp", methods=["GET"])
def diagnostico_mp():
    """Diagnóstico completo de por qué una MP "no se rastrea" en el sistema.

    Sebastián 14-may-2026: "me decia que habia dos materias primas que no
    rastrea: COCAMIDOPROPYL BETAINE · PHENYL TRIMETHICONE".

    Query: ?q=cocamidopropyl  (uno solo · busca fuzzy en INCI y comercial)

    Devuelve checklist completa:
      1. ¿Existe en maestro_mps? · todas las variantes que matchean
      2. ¿Está activa?
      3. ¿Aparece en formula_items? · qué productos la usan
      4. Esos productos · ¿activos? ¿velocidad>0?
      5. Movimientos · entradas vs salidas últ 180d
      6. Stock actual
      7. ¿Por qué no se rastrea? · diagnóstico textual
    """
    err = _require_login()
    if err:
        return err
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "pasá ?q=<nombre_mp>"}), 400

    conn = get_db()
    c = conn.cursor()

    import unicodedata
    def _norm(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().lower())
        return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

    q_norm = _norm(q)

    # 1) Buscar en maestro_mps
    rows = c.execute(
        """SELECT codigo_mp, nombre_comercial, nombre_inci,
                  COALESCE(activo, 1), COALESCE(stock_minimo, 0),
                  COALESCE(proveedor, '')
           FROM maestro_mps""",
    ).fetchall()
    candidatos = []
    for r in rows:
        nc = r[1] or ""; ni = r[2] or ""
        if q_norm in _norm(nc + " " + ni):
            candidatos.append({
                "codigo_mp": r[0],
                "nombre_comercial": nc,
                "nombre_inci": ni,
                "activo": bool(r[3]),
                "stock_minimo": float(r[4] or 0),
                "proveedor": r[5] or "",
            })

    if not candidatos:
        return jsonify({
            "query": q,
            "encontrado_en_maestro": False,
            "diagnostico": f"❌ NO existe ninguna MP en maestro_mps cuyo nombre o INCI contenga '{q}'. Tal vez está con otra denominación · busca variantes en /admin/mps-buscar.",
            "candidatos": [],
        })

    # 2) Para cada candidato, analizar más profundo
    items = []
    for cand in candidatos:
        cod = cand["codigo_mp"]

        # Stock actual
        row_stock = c.execute(
            """SELECT
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('entrada')
                                    THEN cantidad ELSE 0 END), 0) as entradas,
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('salida','consumo')
                                    THEN cantidad ELSE 0 END), 0) as salidas,
                  COUNT(*) as n_total
               FROM movimientos WHERE material_id = ?""",
            (cod,),
        ).fetchone()
        entradas_g = float(row_stock[0] or 0)
        salidas_g = float(row_stock[1] or 0)
        n_total = int(row_stock[2] or 0)
        stock_actual_g = entradas_g - salidas_g

        # Últimos 180d
        row_180 = c.execute(
            """SELECT
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('entrada') THEN cantidad ELSE 0 END), 0),
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('salida','consumo') THEN cantidad ELSE 0 END), 0),
                  COUNT(*)
               FROM movimientos
               WHERE material_id = ?
                 AND date(fecha) >= date('now','-5 hours','-180 day')""",
            (cod,),
        ).fetchone()
        entradas_180_g = float(row_180[0] or 0)
        salidas_180_g = float(row_180[1] or 0)
        n_mov_180 = int(row_180[2] or 0)

        # Productos que la usan (formula_items)
        rows_uso = c.execute(
            """SELECT fi.producto_nombre,
                      COALESCE(fi.cantidad_g_por_lote, 0),
                      COALESCE(fh.lote_size_kg, 0),
                      COALESCE(fh.activo, 1)
               FROM formula_items fi
               LEFT JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
               WHERE fi.material_id = ?""",
            (cod,),
        ).fetchall()

        productos_que_la_usan = []
        n_productos_activos = 0
        for ru in rows_uso:
            productos_que_la_usan.append({
                "producto": ru[0],
                "gramos_por_lote": float(ru[1] or 0),
                "lote_kg": float(ru[2] or 0),
                "producto_activo": bool(ru[3]),
            })
            if ru[3]:
                n_productos_activos += 1

        # ── Diagnóstico textual ──
        problemas = []
        if not cand["activo"]:
            problemas.append("❌ MP marcada como INACTIVA en maestro_mps")
        if not rows_uso:
            problemas.append("❌ NO aparece en formula_items · ningún producto la tiene en su fórmula")
        elif n_productos_activos == 0:
            problemas.append(f"❌ Aparece en {len(rows_uso)} fórmulas pero TODAS son de productos inactivos")
        if n_total == 0:
            problemas.append("⚠ NUNCA tuvo movimientos (entradas ni salidas) · ¿se compró pero no se registró?")
        elif entradas_g > 0 and salidas_g == 0:
            problemas.append(f"⚠ Tiene {entradas_g}g de entradas pero CERO salidas registradas · se compró pero nunca se descontó (¿producción no descuenta esta MP?)")
        elif n_mov_180 == 0:
            problemas.append("⚠ Sin movimientos en últimos 180 días")

        if not problemas:
            diagnostico = "✅ Rastreo OK · tiene movimientos + fórmulas activas"
        else:
            diagnostico = " · ".join(problemas)

        items.append({
            **cand,
            "stock_actual_g": round(stock_actual_g, 2),
            "stock_actual_kg": round(stock_actual_g / 1000.0, 3),
            "movimientos_total": {
                "n_total": n_total,
                "entradas_kg_total": round(entradas_g / 1000.0, 2),
                "salidas_kg_total": round(salidas_g / 1000.0, 2),
            },
            "movimientos_ult_180d": {
                "n": n_mov_180,
                "entradas_kg": round(entradas_180_g / 1000.0, 2),
                "salidas_kg": round(salidas_180_g / 1000.0, 2),
            },
            "productos_que_la_usan": productos_que_la_usan,
            "n_productos_totales": len(rows_uso),
            "n_productos_activos": n_productos_activos,
            "diagnostico": diagnostico,
            "problemas": problemas,
        })

    return jsonify({
        "query": q,
        "n_candidatos": len(items),
        "items": items,
    })


@bp.route("/admin/gasto-mps", methods=["GET"])
def gasto_mps_page():
    """Página visual · consumo y gasto anual de MPs · Alejandro 14-may-2026"""
    if not session.get("compras_user"):
        from flask import redirect
        return redirect("/login?next=/admin/gasto-mps")
    from flask import Response
    return Response(_GASTO_MPS_HTML, mimetype="text/html")


_GASTO_MPS_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Gasto anual MPs · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1200px;margin:0 auto}
.card{background:white;border-radius:12px;padding:20px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e;font-size:22px}
.muted{color:#64748b;font-size:13px}
button{background:#0f766e;color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
button:hover{background:#0d635c}
textarea{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:ui-monospace,monospace;min-height:100px;resize:vertical}
select{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:10px 8px;background:#f1f5f9;color:#475569;font-weight:700}
td{padding:8px;border-bottom:1px solid #f1f5f9}
.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 18px;margin-right:10px;margin-bottom:8px;text-align:center;min-width:130px;vertical-align:top}
.kpi-lbl{font-size:11px;color:#64748b}
.kpi-val{font-size:22px;font-weight:800}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700}
.tag-warn{background:#fef3c7;color:#854d0e}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:#1e40af}
.num{text-align:right;font-variant-numeric:tabular-nums}
</style></head><body>
<div class="wrap">
<a href="/modulos" style="color:#0f766e;font-weight:700;font-size:13px">&larr; Volver</a>

<div class="card">
  <h1>📦 Necesidad anual de materias primas</h1>
  <div class="muted">Calcula cuánto se va a NECESITAR de cada MP en 12 meses · cruza fórmulas activas con velocidad de ventas Shopify. Para Alejandro · 14-may-2026.</div>
  <div style="margin-top:14px">
    <label style="display:block;font-size:12px;color:#475569;margin-bottom:4px">Materias primas (una por línea · busca por nombre):</label>
    <textarea id="queries" placeholder="Cetiol AB
Phenyl trimeticone
PEG-12 dimethicone
CAPB">Cetiol AB
Phenyl trimeticone
PEG-12 dimethicone
CAPB</textarea>
  </div>
  <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <label style="font-size:12px;color:#475569">Ventana:
      <select id="dias">
        <option value="90">3 meses</option>
        <option value="180">6 meses</option>
        <option value="365" selected>12 meses</option>
        <option value="730">24 meses</option>
      </select>
    </label>
    <button onclick="calcular()">📊 Calcular gasto</button>
  </div>
  <div id="kpis" style="margin-top:14px"></div>
</div>

<div id="resultado"></div>

</div>
<script>
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtCOP(n){
  if (n == null) return '—';
  return '$ ' + Math.round(n).toLocaleString('es-CO');
}
function fmtKg(n){
  if (n == null) return '—';
  return n.toLocaleString('es-CO', {maximumFractionDigits: 2}) + ' kg';
}

async function calcular(){
  const txt = document.getElementById('queries').value || '';
  const queries = txt.split('\n').map(s => s.trim()).filter(s => s);
  if (!queries.length){ alert('Pegá al menos 1 MP'); return; }
  const dias = parseInt(document.getElementById('dias').value);
  document.getElementById('resultado').innerHTML = '<div class="card">⏳ Calculando…</div>';
  document.getElementById('kpis').innerHTML = '';

  const params = new URLSearchParams();
  queries.forEach(q => params.append('q', q));
  params.append('dias', dias);
  try {
    const r = await fetch('/api/plan/gasto-mps?' + params.toString());
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); document.getElementById('resultado').innerHTML = ''; return; }
    render(d, queries);
  } catch(e){ alert('Error: ' + e.message); }
}

function render(d, queries){
  // KPIs
  let k = '';
  k += '<span class="kpi"><div class="kpi-lbl">Buscadas</div><div class="kpi-val">' + queries.length + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">Encontradas</div><div class="kpi-val">' + d.n_mps_encontradas + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">📊 Consumo histórico</div><div class="kpi-val" style="color:#0891b2">' + fmtKg(d.total_kg_consumido_anual_historico) + '</div></span>';
  k += '<span class="kpi"><div class="kpi-lbl">📅 Calendar 12m</div><div class="kpi-val" style="color:#7c3aed">' + fmtKg(d.total_kg_necesidad_calendar_12m) + '</div></span>';
  k += '<span class="kpi" style="border-color:#16a34a;background:#f0fdf4"><div class="kpi-lbl">🛒 COMPRAR 12m</div><div class="kpi-val" style="color:#16a34a">' + fmtKg(d.total_kg_a_comprar_12m) + '</div></span>';
  document.getElementById('kpis').innerHTML = k;

  let html = '<div class="card">';

  if (d.no_encontrados && d.no_encontrados.length){
    html += '<div style="background:#fef3c7;border:1px solid #fde68a;color:#854d0e;padding:10px;border-radius:8px;margin-bottom:12px">';
    html += '⚠ <strong>NO encontradas en maestro_mps:</strong> ' + d.no_encontrados.map(q => '<code>' + escapeHtml(q) + '</code>').join(', ');
    html += '<br><span style="font-size:11px">Probá variaciones de nombre · busca en <a href="/admin/mps-buscar" target="_blank">/admin/mps-buscar</a></span></div>';
  }

  if (!d.items || !d.items.length){
    html += '<div class="muted" style="padding:20px;text-align:center">No hay items para mostrar</div>';
    html += '</div>';
    document.getElementById('resultado').innerHTML = html;
    return;
  }

  // Ordenar por kg_a_comprar descendente
  d.items.sort((a, b) => (b.kg_a_comprar_para_cubrir_12m || 0) - (a.kg_a_comprar_para_cubrir_12m || 0));

  html += '<table>';
  html += '<thead><tr>';
  html += '<th>Cód MP</th>';
  html += '<th>Nombre comercial / INCI</th>';
  html += '<th class="num">Stock<br>actual</th>';
  html += '<th class="num">📊 Consumo<br>histórico 12m</th>';
  html += '<th class="num">📅 Necesidad<br>Calendar 12m</th>';
  html += '<th class="num" style="background:#dcfce7">🛒 Comprar<br>12m</th>';
  html += '<th>Productos que la usan (Calendar vs Ventas)</th>';
  html += '</tr></thead><tbody>';

  d.items.forEach((it, idx) => {
    const aComprar = it.kg_a_comprar_para_cubrir_12m || 0;
    const inactivo = !it.activo;
    let badges = '';
    if (inactivo) badges += ' <span class="tag tag-warn">inactivo</span>';
    if (aComprar === 0 && it.kg_necesidad_calendar_12m === 0 && !inactivo) badges += ' <span class="tag tag-warn">sin uso programado</span>';

    const productos = it.productos_que_la_usan || [];
    const productosActivos = productos.filter(p => !p.inactivo);

    html += '<tr>';
    html += '<td class="mono">' + escapeHtml(it.codigo_mp) + '</td>';
    html += '<td><strong>' + escapeHtml(it.nombre_comercial) + '</strong>' + badges + '<br><span style="color:#94a3b8;font-size:10px">' + escapeHtml(it.nombre_inci) + '</span><br><span style="color:#475569;font-size:10px">' + escapeHtml(it.proveedor || '—') + ' · match: ' + escapeHtml(it.matched_query) + '</span></td>';
    html += '<td class="num" style="color:#475569">' + fmtKg(it.stock_actual_kg) + '</td>';
    html += '<td class="num" style="color:#0891b2">' + fmtKg(it.kg_consumido_anual_historico) + '<br><span style="font-size:10px;color:#94a3b8">' + (it.n_movimientos || 0) + ' mov</span></td>';
    html += '<td class="num" style="color:#7c3aed">' + fmtKg(it.kg_necesidad_calendar_12m) + '<br><span style="font-size:10px;color:#94a3b8">ventas: ' + fmtKg(it.kg_necesidad_ventas_12m) + '</span></td>';
    html += '<td class="num" style="background:#dcfce7;color:#16a34a;font-size:18px;font-weight:800">' + fmtKg(aComprar) + '</td>';
    html += '<td style="font-size:11px">';
    if (productosActivos.length){
      html += '<details><summary style="cursor:pointer;color:#0f766e;font-weight:700">▾ Ver ' + productosActivos.length + '</summary>';
      html += '<table style="margin-top:5px;font-size:10px"><thead><tr><th>Producto</th><th class="num">g/lote</th><th class="num">📅 Lotes<br>Calendar</th><th class="num">📅 kg MP<br>Calendar</th><th class="num">🛍 Lotes<br>Ventas est</th><th class="num">Fuente</th></tr></thead><tbody>';
      productosActivos.forEach(p => {
        const fuenteTag = p.fuente_calculo === 'calendar' ?
          '<span style="background:#e0e7ff;color:#3730a3;padding:1px 4px;border-radius:3px">Calendar</span>' :
          '<span style="background:#fef3c7;color:#854d0e;padding:1px 4px;border-radius:3px">Ventas</span>';
        html += '<tr><td>' + escapeHtml(p.producto) + '</td>';
        html += '<td class="num">' + (p.gramos_mp_por_lote || 0) + 'g</td>';
        html += '<td class="num">' + (p.calendar_n_lotes || 0) + '</td>';
        html += '<td class="num" style="font-weight:700">' + fmtKg(p.calendar_kg_mp) + '</td>';
        html += '<td class="num">' + (p.ventas_n_lotes_estimados || 0) + '</td>';
        html += '<td class="num">' + fuenteTag + '</td></tr>';
      });
      html += '</tbody></table></details>';
    } else {
      html += '<span class="muted">—</span>';
    }
    html += '</td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  html += '<div class="muted" style="margin-top:10px;font-size:11px">📝 ' + escapeHtml(d.metodologia || '') + '</div>';
  html += '</div>';
  document.getElementById('resultado').innerHTML = html;
}

// Auto-calcular al cargar
calcular();
</script>
</body></html>"""


@bp.route("/api/plan/gasto-mps", methods=["GET"])
def gasto_anual_mps():
    """Calcula necesidad anual de MPs proyectada según ventas Shopify
    y fórmulas activas. Sebastián 14-may-2026: "necesito saber cuanta
    cantidad de esas materias primas necesitamos para el año".

    Combina 3 fuentes:
      a) consumo_historico_kg = movimientos tipo Salida últ N días
         (extrapolado a 365d) · lo que ya gastamos
      b) necesidad_proyectada_kg = sum(formula_items.gramos × lotes_anuales
         por cada producto activo que usa la MP) · lo que SE VA a necesitar
      c) productos_que_la_usan[] · debug · ver qué productos consumen
         la MP y en qué cantidad

    Query: ?q=cetiol&q=phenyl  ?dias=365
    """
    err = _require_login()
    if err:
        return err
    queries = [q.strip() for q in request.args.getlist("q") if q.strip()]
    if not queries:
        return jsonify({"error": "pasá al menos un ?q=<nombre_mp>"}), 400
    try:
        dias = max(30, min(730, int(request.args.get("dias") or 365)))
    except ValueError:
        dias = 365

    conn = get_db()
    c = conn.cursor()

    # Normalizador básico para matching (sin acentos, lowercase)
    import unicodedata
    def _norm(s):
        if not s: return ""
        s = unicodedata.normalize('NFD', str(s).strip().lower())
        return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

    # Buscar MPs que matcheen cualquier query (nombre_inci o nombre_comercial)
    rows_mps = c.execute(
        """SELECT codigo_mp,
                  COALESCE(nombre_comercial,'') AS nc,
                  COALESCE(nombre_inci,'') AS ni,
                  COALESCE(precio_referencia, 0) AS precio,
                  COALESCE(proveedor, '') AS prov,
                  COALESCE(activo, 1) AS act
           FROM maestro_mps""",
    ).fetchall()

    matched = []
    for r in rows_mps:
        cod = (r[0] or "").strip()
        nc = r[1] or ""
        ni = r[2] or ""
        n_all = _norm(nc + " " + ni)
        for q in queries:
            if _norm(q) in n_all:
                matched.append({
                    "codigo_mp": cod,
                    "nombre_comercial": nc,
                    "nombre_inci": ni,
                    "precio_referencia": float(r[3] or 0),
                    "proveedor": r[4] or "",
                    "activo": bool(r[5]),
                    "matched_query": q,
                })
                break

    # ── Necesidades proyectadas · Sebastián 14-may-2026:
    # "para esos calculos usa google calendar que tiene la programacion
    # de todo el año asi cruzas producciones pensadas vs formulas
    # maestras vs estas materias primas"
    #
    # Combina 2 fuentes para máxima precisión:
    #  (A) producciones_programadas próximos 365d · de produccion_programada
    #      con origen IN (calendar, manual, eos_plan, eos_canonico) ·
    #      estado != cancelado · esto es lo que se "PLANEÓ producir"
    #  (B) velocidad_kg_dia de Animus DTC (Shopify ventas) · fallback si
    #      el producto no tiene programación en Calendar
    necesidades_dtc = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                            cob_alerta=25, cob_vigilar=45)
    nec_por_prod = {n["producto_nombre"]: n for n in necesidades_dtc}

    # Producciones programadas (Calendar + EOS Plan + Canónico) próx 365d
    # por producto · sumar n_lotes y kg_planificado
    prog_por_producto = {}
    for r in c.execute(
        """SELECT producto,
                  COUNT(*) AS n_lotes,
                  COALESCE(SUM(cantidad_kg), 0) AS kg_total_planificado
           FROM produccion_programada
           WHERE estado NOT IN ('cancelado')
             AND fin_real_at IS NULL
             AND date(fecha_programada) >= date('now', '-5 hours')
             AND date(fecha_programada) <= date('now', '-5 hours', '+365 day')
             AND origen IN ('calendar','manual','eos_plan','eos_canonico')
           GROUP BY producto""",
    ).fetchall():
        prog_por_producto[r[0] or ""] = {
            "n_lotes": int(r[1] or 0),
            "kg_planificado_12m": float(r[2] or 0),
        }

    # Para cada MP matched, buscar en qué fórmulas se usa y proyectar
    items = []
    total_kg_consumido = 0.0
    total_kg_proyectado = 0.0
    for mp in matched:
        cod = mp["codigo_mp"]
        # 1) Consumo histórico real (movimientos tipo Salida)
        row = c.execute(
            """SELECT
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('salida','consumo')
                                    THEN cantidad ELSE 0 END), 0) AS gramos_salida,
                  COUNT(*) AS n_movimientos
               FROM movimientos
               WHERE material_id = ?
                 AND date(fecha) >= date('now','-5 hours','-' || ? || ' day')""",
            (cod, dias),
        ).fetchone()
        gramos_consumo = float(row[0] or 0)
        n_mov = int(row[1] or 0)
        kg_consumo_ventana = gramos_consumo / 1000.0
        kg_consumo_anual = kg_consumo_ventana * (365.0 / max(dias, 1))

        # 2) Necesidad proyectada · sumar usos en fórmulas activas
        rows_uso = c.execute(
            """SELECT fi.producto_nombre,
                      COALESCE(fi.cantidad_g_por_lote, 0) AS gramos_por_lote,
                      COALESCE(fh.lote_size_kg, 0) AS lote_kg,
                      COALESCE(fh.activo, 1) AS act
               FROM formula_items fi
               LEFT JOIN formula_headers fh ON fh.producto_nombre = fi.producto_nombre
               WHERE fi.material_id = ?""",
            (cod,),
        ).fetchall()
        productos_usan = []
        kg_proyectado_anual = 0.0     # según Calendar (preferido)
        kg_estimado_ventas = 0.0      # según Shopify (fallback)
        for ru in rows_uso:
            prod = ru[0] or ""
            gramos_por_lote_excel = float(ru[1] or 0)
            lote_kg_excel = float(ru[2] or 0)
            es_activo = bool(ru[3])
            nec = nec_por_prod.get(prod, {})
            vel_kg_dia = float(nec.get("velocidad_kg_dia", 0) or 0)
            prog = prog_por_producto.get(prod, {})
            n_lotes_calendar = prog.get("n_lotes", 0)
            kg_calendar_total = prog.get("kg_planificado_12m", 0)

            # Sebastián 14-may-2026: "en el excel todos los % estan
            # calculados sobre 100% · son formulas puras". Es decir, la
            # fórmula del Excel describe % del lote piloto. Cuando se
            # produce un lote real DE DIFERENTE TAMAÑO, hay que escalar
            # manteniendo el porcentaje.
            # pct_mp_sobre_lote = gramos_excel / (lote_kg_excel × 1000)
            # kg_mp_por_lote_real = pct × lote_real_kg
            if lote_kg_excel > 0.001:
                pct_mp = gramos_por_lote_excel / (lote_kg_excel * 1000.0)
            else:
                pct_mp = 0.0

            # Cálculo A · CALENDAR · kg MP = % × kg_planificado_total
            kg_mp_calendar = kg_calendar_total * pct_mp

            # Cálculo B · VENTAS Shopify · kg MP = % × kg vendidos al año
            kg_producto_anual_ventas = vel_kg_dia * 365.0
            kg_mp_ventas = kg_producto_anual_ventas * pct_mp
            n_lotes_ventas = (kg_producto_anual_ventas / lote_kg_excel) if lote_kg_excel > 0.001 else 0

            if not es_activo:
                productos_usan.append({
                    "producto": prod,
                    "inactivo": True,
                    "gramos_mp_por_lote": gramos_por_lote_excel,
                })
                continue

            # Sumar al total proyectado · Calendar manda si tiene lotes,
            # sino fallback a ventas
            if n_lotes_calendar > 0:
                fuente = "calendar"
                kg_mp_de_este_producto = kg_mp_calendar
            else:
                fuente = "ventas_shopify"
                kg_mp_de_este_producto = kg_mp_ventas
            kg_proyectado_anual += kg_mp_de_este_producto
            kg_estimado_ventas += kg_mp_ventas

            productos_usan.append({
                "producto": prod,
                "lote_kg_excel": lote_kg_excel,
                "gramos_mp_por_lote_excel": gramos_por_lote_excel,
                "pct_mp_en_formula": round(pct_mp * 100, 3),  # como %
                "fuente_calculo": fuente,
                "calendar_n_lotes": n_lotes_calendar,
                "calendar_kg_planificado": round(kg_calendar_total, 1),
                "calendar_kg_mp": round(kg_mp_calendar, 2),
                "ventas_vel_kg_dia": round(vel_kg_dia, 3),
                "ventas_kg_producto_anual": round(kg_producto_anual_ventas, 1),
                "ventas_n_lotes_estimados": round(n_lotes_ventas, 1),
                "ventas_kg_mp": round(kg_mp_ventas, 2),
                "kg_mp_anual": round(kg_mp_de_este_producto, 2),
            })

        # Ordenar productos que más consumen primero
        productos_usan.sort(key=lambda x: -(x.get("kg_mp_anual") or 0))

        # Stock actual (entradas - salidas, todo histórico en gramos)
        row_stock = c.execute(
            """SELECT
                  COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad ELSE 0 END),0) -
                  COALESCE(SUM(CASE WHEN LOWER(tipo) IN ('salida','consumo') THEN cantidad ELSE 0 END),0)
               FROM movimientos WHERE material_id = ?""",
            (cod,),
        ).fetchone()
        stock_kg = round(float(row_stock[0] or 0) / 1000.0, 2)

        # Necesidad neta de compra = proyectado anual - stock actual
        kg_a_comprar = round(max(0, kg_proyectado_anual - stock_kg), 2)

        items.append({
            **mp,
            "ventana_dias": dias,
            "stock_actual_kg": stock_kg,
            "kg_consumido_ventana": round(kg_consumo_ventana, 2),
            "kg_consumido_anual_historico": round(kg_consumo_anual, 2),
            "n_movimientos": n_mov,
            "kg_necesidad_calendar_12m": round(kg_proyectado_anual, 2),
            "kg_necesidad_ventas_12m": round(kg_estimado_ventas, 2),
            "kg_a_comprar_para_cubrir_12m": kg_a_comprar,
            "productos_que_la_usan": productos_usan,
            "n_productos_activos_que_la_usan": sum(1 for p in productos_usan if not p.get("inactivo")),
        })
        total_kg_consumido += kg_consumo_anual
        total_kg_proyectado += kg_proyectado_anual

    total_a_comprar = sum(it["kg_a_comprar_para_cubrir_12m"] for it in items)
    return jsonify({
        "ventana_dias": dias,
        "queries": queries,
        "items": items,
        "n_mps_encontradas": len(items),
        "total_kg_consumido_anual_historico": round(total_kg_consumido, 2),
        "total_kg_necesidad_calendar_12m": round(total_kg_proyectado, 2),
        "total_kg_a_comprar_12m": round(total_a_comprar, 2),
        "no_encontrados": [q for q in queries if not any(
            _norm(q) in _norm(it["nombre_comercial"] + " " + it["nombre_inci"]) for it in items
        )],
        "metodologia": (
            "kg_necesidad_calendar_12m: gramos_mp_por_lote × N_lotes_programados "
            "(produccion_programada próx 365d · estado!=cancelado · origen "
            "Calendar/EOS/Canónico). Fallback a velocidad_ventas si producto "
            "no tiene programación. kg_a_comprar = max(0, necesidad - stock_actual). "
            "kg_consumido_anual_historico: movimientos Salida extrapolados a 365d."
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
        # Sebastián 14-may-2026: si lote Excel <3kg es fórmula piloto ·
        # buscar promedio real · si no hay historial, excluir.
        if lote_kg < 3:
            # Promedio real últimos 180d
            real_kgs = []
            for r in c.execute(
                """SELECT COALESCE(kg_real, cantidad_kg, 0)
                   FROM produccion_programada
                   WHERE producto = ?
                     AND fin_real_at IS NOT NULL
                     AND COALESCE(kg_real, cantidad_kg, 0) >= 3
                     AND date(fin_real_at) >= date('now','-5 hours','-180 day')""",
                (prod,),
            ).fetchall():
                real_kgs.append(float(r[0] or 0))
            if real_kgs:
                lote_kg = round(sum(real_kgs) / len(real_kgs), 1)
            else:
                # Sin historial real · es piloto · no programar automáticamente
                sin_formula.append({
                    "producto": prod,
                    "stock_kg": round(stock_efectivo, 2),
                    "cob_dias": round(cob_dias, 1),
                    "razon": f"lote_excel_piloto_{lote_kg}kg_sin_historial_real",
                })
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
.lote.eos_b2b{background:#fce7f3;border-left-color:#db2777;color:#9d174d}
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

<!-- Banner alertas IA · Sebastián 19-may-2026 · proactivas y accionables -->
<div id="alertas-ia-wrap" style="display:none;margin-bottom:14px"></div>

<div class="card">
  <h1>📅 Calendario EOS · Plan autónomo</h1>
  <div class="muted">Calendario propio · reemplaza Google Calendar · genera autoplan según ventas Shopify + lote_size del Excel + reglas operativas (festivos · lun-vie · max 2/día · grandes solos · Vit C/Triactive lun-mié)</div>
  <div class="actions-bar" style="margin-top:10px">
    <div>
      <span class="muted" style="margin-right:8px">Horizonte autoplan:</span>
      <button class="horiz-btn" data-h="30" onclick="setHoriz(30)">30 días</button>
      <button class="horiz-btn" data-h="60" onclick="setHoriz(60)">60 días</button>
      <button class="horiz-btn" data-h="90" onclick="setHoriz(90)">90 días</button>
      <button class="horiz-btn" data-h="180" onclick="setHoriz(180)">180 días</button>
      <button class="horiz-btn active" data-h="365" onclick="setHoriz(365)">365 días</button>
    </div>
    <div>
      <label style="margin-right:10px;font-size:12px;color:#475569;cursor:pointer">
        <input type="checkbox" id="filtro-solo-ia" onchange="render()" style="vertical-align:middle">
        Solo sugerencias IA
      </label>
      <button onclick="cargar()" class="secondary">↻ Recargar</button>
      <button onclick="generarPlanIA()" class="success" id="btn-generar-ia">🤖 Generar plan IA</button>
      <button onclick="autoplanIA()" class="warn" id="btn-ia" style="display:none">🤖 Autoplan con IA</button>
      <button onclick="aplicarIAanual()" class="success" id="btn-ia-anual" style="display:none">🎯 Aplicar plan IA</button>
      <button onclick="diagCalendar()" class="secondary">🔍 Diag</button>
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
      <button onclick="generarPlanIA()" class="success" id="btn-generar-ia-2"
        style="font-size:14px;padding:10px 18px">🤖 Generar plan IA</button>
      <button onclick="confirmarAplicar()" class="success" id="btn-aplicar" style="display:none" disabled>✅ Confirmar y programar TODO</button>
    </div>
  </div>
  <div class="legend">
    <span><span class="legend-dot" style="background:#6366f1"></span>🔁 Canónico (el plan real)</span>
    <span><span class="legend-dot" style="background:#16a34a"></span>🟢 Plan / ajustado a mano</span>
    <span><span class="legend-dot" style="background:#db2777"></span>📦 Pedido B2B (Fernando Mesa)</span>
    <span><span class="legend-dot" style="background:#fca5a5"></span>Festivo colombiano</span>
  </div>
  <!-- Panel diag visible · Sebastián 14-may-2026 "no sale nada" -->
  <div id="cal-diag" style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:11px;color:#854d0e;font-family:monospace"></div>
  <div id="cal-grid-wrap"></div>
</div>

<!-- Lista TODOS los lotes · fallback siempre visible si grid falla -->
<div class="card">
  <h2 style="margin:0 0 8px;color:#475569;font-size:15px">📋 Todos los lotes agendados (fallback · siempre visible)</h2>
  <div style="color:#64748b;font-size:11px;margin-bottom:8px">Si el calendario visual aparece vacío, abajo ves lista textual de los mismos lotes desde el backend.</div>
  <div id="lista-completa"></div>
</div>

<div class="card">
  <h2 id="lista-titulo" style="margin:0 0 8px;color:#475569;font-size:15px">📋 Lista del autoplan</h2>
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
      <div style="display:flex;align-items:center;gap:6px">
        <button onclick="navLoteModal(-1)" id="lote-nav-prev" title="Lote anterior (por fecha)" style="background:rgba(255,255,255,.2);border:none;color:white;font-size:18px;font-weight:800;cursor:pointer;line-height:1;border-radius:6px;padding:3px 11px">‹</button>
        <button onclick="navLoteModal(1)" id="lote-nav-next" title="Lote siguiente (por fecha)" style="background:rgba(255,255,255,.2);border:none;color:white;font-size:18px;font-weight:800;cursor:pointer;line-height:1;border-radius:6px;padding:3px 11px">›</button>
        <button onclick="cerrarLoteModal()" style="background:transparent;border:none;color:white;font-size:22px;cursor:pointer;line-height:1;margin-left:4px">✕</button>
      </div>
    </div>
    <div class="modal-body" id="lote-body"></div>
  </div>
</div>

</div>
<script>
let HORIZONTE = 365;  // Sebastián 15-may-2026: default 365 · "elegi 365 pero solo programa mayo"
let MES_OFFSET = 0;  // 0 = mes actual · -1/+1 navegar
let PLAN_DATA = null;
let _MES_NAVEGADO = false;  // FIX 24-may PM · true después de primer cargar() · cargar() preserva MES_OFFSET
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
  document.getElementById('cal-grid-wrap').innerHTML = '<div class="muted" style="padding:30px;text-align:center">Cargando calendario…</div>';
  try {
    // Sebastián 14-may-2026: "siento que canónico era el perfecto · muy
    // en la realidad". Por default solo mostramos lotes AGENDADOS en BD
    // (eos_canonico es el principal · eos_plan si Sebastián agregó manual).
    // Las sugerencias del algoritmo NO se cargan inicialmente · solo si
    // aprieta "🤖 Autoplan con IA".
    // Sebastián 14-may-2026: bust cache · "solo sale el gel hidratante"
    // Posible cache del browser sirviendo respuesta vieja con 1 producto.
    const _ts = Date.now();
    const rAgendadas = await fetch('/api/programacion/produccion-programada/listado?_t=' + _ts, {cache: 'no-store'});
    const dAgendadas = await rAgendadas.json();
    if (!rAgendadas.ok){ alert('Error agendadas: ' + rAgendadas.status); return; }
    // Diag · cuántos llegaron y qué productos únicos hay en la respuesta
    try {
      const _set = new Set();
      (dAgendadas.producciones || []).forEach(p => _set.add(p.producto));
      console.log('[CAL.cargar] respuesta listado:',
        'total_lotes=' + (dAgendadas.producciones||[]).length,
        'productos_unicos=' + _set.size,
        'productos=' + [..._set].join('|'));
    } catch(e){}

    // Festivos colombianos del rango · Sebastián 16-may-2026: pedir
    // year-1, year y year+1 · cubre bordes de año y el plan a 365d sin
    // depender de la zona horaria exacta del navegador.
    const year = new Date().getFullYear();
    const rFest = await fetch('/api/plan/festivos?year=' + (year - 1) + ',' + year + ',' + (year + 1));
    const dFest = await rFest.json();
    const festivosSet = new Set();
    Object.values(dFest.festivos_por_year || {}).forEach(arr => arr.forEach(f => festivosSet.add(f.fecha)));

    PLAN_DATA = {
      plan: {plan_items: [], cancelables_calendar: [], sin_formula: [], total_producciones: 0},
      agendadas: dAgendadas.producciones || [],
      festivos: festivosSet,
    };
    document.getElementById('btn-aplicar').disabled = true;  // no hay sugerencias hasta apretar IA
    // Sebastián 15-may-2026: "no veo nada en calendario". Causa: el
    // calendario abría en el mes actual (mayo) que está vacío · el plan
    // arranca meses adelante. Auto-saltar al primer mes con lotes.
    // FIX 24-may PM Sebastián · "estoy en junio muevo algo y me devuelve
    // a mayo" · cargar() corre tras toda mutación · respetar mes visible
    // si ya navegó. Solo auto-saltar al primer mes con lotes en LOAD
    // INICIAL · después _MES_NAVEGADO=true y respetamos lo que el
    // usuario eligió.
    if (!_MES_NAVEGADO) {
      MES_OFFSET = _primerMesConLotesOffset();
      _MES_NAVEGADO = true;
    }
    render();
    // Sebastián 19-may-2026: cargar alertas IA en paralelo (no bloqueante).
    if (typeof cargarAlertasIA === 'function') { cargarAlertasIA(); }
    // 30-may-2026: aviso de ventas sin mapear (no entran a la velocidad).
    if (typeof cargarAlertasVentas === 'function') { cargarAlertasVentas(); }
  } catch(e){
    // Sebastián 16-may-2026: error visible en el grid + botón reintentar
    // (antes solo alert · el grid quedaba en "Cargando…" para siempre).
    const _w = document.getElementById('cal-grid-wrap');
    if (_w){
      _w.innerHTML = '<div style="padding:30px;text-align:center;color:#dc2626">' +
        '<div style="font-weight:700;margin-bottom:8px">⚠ No se pudo cargar el calendario</div>' +
        '<div style="font-size:12px;color:#64748b;margin-bottom:12px">' + escapeHtml(e.message) + '</div>' +
        '<button onclick="cargar()" class="secondary">↻ Reintentar</button></div>';
    }
  }
}

// Sebastián 15-may-2026: devuelve el MES_OFFSET del primer mes que
// tiene lotes agendados. Si el mes actual ya tiene lotes → 0.
function _primerMesConLotesOffset(){
  if (!PLAN_DATA || !PLAN_DATA.agendadas || !PLAN_DATA.agendadas.length) return 0;
  // Sebastián 16-may-2026: tomar la fecha más temprana SOLO entre lotes
  // de hoy en adelante. Antes tomaba el mínimo absoluto · si había un
  // lote viejo sin completar (el listado trae desde hoy-7d), el offset
  // salía negativo → 0 → mes actual vacío → volvía el "no sale nada".
  const hoyStr = fechaLocalStr(new Date());
  let minFecha = null;
  PLAN_DATA.agendadas.forEach(a => {
    const f = (a.fecha_programada || '').slice(0, 10);
    if (f && f >= hoyStr && (!minFecha || f < minFecha)) minFecha = f;
  });
  if (!minFecha) return 0;  // todo es pasado · quedarse en mes actual
  const partes = minFecha.split('-');
  const y = parseInt(partes[0]), m = parseInt(partes[1]);
  if (isNaN(y) || isNaN(m)) return 0;
  const hoy = new Date();
  const offset = (y - hoy.getFullYear()) * 12 + (m - 1 - hoy.getMonth());
  return offset > 0 ? offset : 0;
}

// Sebastián 14-may-2026: helper local · evita bug toISOString() que
// desplaza días según zona horaria. Devuelve YYYY-MM-DD en hora local.
function fechaLocalStr(d){
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const dd = String(d.getDate()).padStart(2,'0');
  return y + '-' + m + '-' + dd;
}

function render(){
  if (!PLAN_DATA){
    document.getElementById('cal-diag').textContent = '⚠ PLAN_DATA null · llamá a cargar()';
    return;
  }

  // Diagnóstico Sebastián 14-may-2026: "solo me salen 3 productos" / "no sale nada"
  // Loguear conteo de productos únicos para depurar bug visual
  try {
    const _prodSet = new Set();
    (PLAN_DATA.agendadas || []).forEach(a => _prodSet.add(a.producto));
    console.log('[CAL] agendadas=' + (PLAN_DATA.agendadas || []).length +
                ' productos_unicos=' + _prodSet.size +
                ' lista=' + [..._prodSet].join('|'));
  } catch(e){ console.warn('diag err', e); }

  // Fallback lista textual · SIEMPRE rellena ANTES del grid, así si el
  // grid falla, Sebastián igual ve los lotes.
  try {
    const ag = PLAN_DATA.agendadas || [];
    if (ag.length === 0){
      document.getElementById('lista-completa').innerHTML = '<div class="muted" style="padding:20px;text-align:center">No hay lotes agendados · backend devolvió 0</div>';
    } else {
      // Agrupar por mes
      const porMes = {};
      ag.forEach(a => {
        const f = (a.fecha_programada || '').slice(0,10);
        if (!f) return;
        const mes = f.slice(0,7);
        (porMes[mes] = porMes[mes] || []).push(a);
      });
      let html = '<div style="font-size:11px;color:#64748b;margin-bottom:6px">Total: <strong>'+ag.length+' lotes · '+(new Set(ag.map(x=>x.producto))).size+' productos únicos</strong></div>';
      // Sebastián 15-may-2026: "que aparezca todo". Tabla resumen de
      // TODOS los productos del plan · próximo lote + cuántos lotes ·
      // siempre visible, sin clics. Es la vista "ver todo".
      const porProd = {};
      ag.forEach(a => {
        const p = a.producto || '—';
        (porProd[p] = porProd[p] || []).push((a.fecha_programada||'').slice(0,10));
      });
      html += '<div style="font-weight:700;color:#0f766e;margin:8px 0 4px">📦 Los ' +
        Object.keys(porProd).length + ' productos del plan</div>';
      html += '<table style="width:100%;font-size:11px;margin-bottom:10px">' +
        '<tr style="color:#64748b;text-align:left"><th>Producto</th><th>Próximo lote</th><th>Lotes/año</th></tr>';
      // Sebastián 16-may-2026: "próximo lote" = primera fecha de HOY en
      // adelante (antes mostraba fechas pasadas como si fueran próximas).
      const _hoyP = fechaLocalStr(new Date());
      Object.keys(porProd).sort().forEach(p => {
        const fechas = porProd[p].filter(Boolean).sort();
        const prox = fechas.find(f => f >= _hoyP) || fechas[fechas.length - 1] || '—';
        html += '<tr style="border-top:1px solid #f1f5f9"><td>' + escapeHtml(p) +
          '</td><td>' + escapeHtml(prox) +
          '</td><td style="text-align:right">' + porProd[p].length + '</td></tr>';
      });
      html += '</table>';
      // Detalle por mes · abierto por defecto
      Object.keys(porMes).sort().forEach(mes => {
        html += '<details style="margin:4px 0;border:1px solid #e2e8f0;border-radius:6px;padding:6px 10px"><summary style="cursor:pointer;font-weight:700;color:#0f766e">'+mes+' · '+porMes[mes].length+' lotes</summary>';
        html += '<table style="width:100%;font-size:11px;margin-top:6px"><tr style="color:#64748b;text-align:left"><th>Fecha</th><th>Producto</th><th>kg</th><th>Origen</th></tr>';
        porMes[mes].sort((a,b)=>(a.fecha_programada||'').localeCompare(b.fecha_programada||'')).forEach(l => {
          html += '<tr style="border-top:1px solid #f1f5f9"><td>'+escapeHtml((l.fecha_programada||'').slice(0,10))+'</td><td>'+escapeHtml(l.producto||'')+'</td><td style="text-align:right">'+(l.kg||0)+'</td><td>'+escapeHtml(l.origen||'')+'</td></tr>';
        });
        html += '</table></details>';
      });
      document.getElementById('lista-completa').innerHTML = html;
    }
  } catch(e){
    document.getElementById('lista-completa').innerHTML = '<div style="color:#dc2626;padding:10px">Error rellenando lista fallback: ' + e.message + '</div>';
  }

  // KPIs
  const k = PLAN_DATA.plan;
  let html = '';
  html += '<span class="kpi"><div class="kpi-lbl">📅 Sugeridas</div><div class="kpi-val" style="color:#16a34a">' + (k.total_producciones || 0) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">🗑 Cancelables</div><div class="kpi-val" style="color:#dc2626">' + ((k.cancelables_calendar || []).length) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">⚠ Sin fórmula</div><div class="kpi-val" style="color:#ca8a04">' + ((k.sin_formula || []).length) + '</div></span>';
  html += '<span class="kpi"><div class="kpi-lbl">📅 Ya agendadas</div><div class="kpi-val" style="color:#475569">' + (PLAN_DATA.agendadas.length || 0) + '</div></span>';
  // KPI productos únicos detectados (diag visual del bug)
  try {
    const _ps = new Set();
    (PLAN_DATA.agendadas || []).forEach(a => _ps.add(a.producto));
    html += '<span class="kpi"><div class="kpi-lbl">🎯 Productos únicos</div><div class="kpi-val" style="color:#0f766e">' + _ps.size + '</div></span>';
  } catch(e){}
  document.getElementById('kpis').innerHTML = html;

  // Calcular mes a mostrar
  const hoy = new Date();
  const ref = new Date(hoy.getFullYear(), hoy.getMonth() + MES_OFFSET, 1);
  document.getElementById('mesActual').textContent = MESES[ref.getMonth()] + ' ' + ref.getFullYear();

  // Filtro · Sebastián 14-may-2026: "quiero que aparezcan solo las de
  // la IA · las otras olvídalas así tenemos algo más preciso"
  const filtroSoloIA = document.getElementById('filtro-solo-ia')?.checked || false;

  // Agrupar lotes por fecha
  const lotesPorFecha = {};
  if (!filtroSoloIA){
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
  }
  // Lotes sugeridos del autoplan (no agendados aún) · siempre visibles
  (k.plan_items || []).forEach(it => {
    const f = it.fecha;
    if (!f) return;
    // Si filtroSoloIA · solo mostrar items que vinieron de la IA (from_ia)
    if (filtroSoloIA && !it.from_ia) return;
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
  // Sebastián 14-may-2026 "no sale nada" · usar fecha local en vez de
  // toISOString para evitar bug de zona horaria que desplazaba días.
  const hoyStr = fechaLocalStr(hoy);

  let grid = '<div class="cal-grid">';
  DIAS.forEach(d => grid += '<div class="cal-head">' + d + '</div>');
  for (let sem = 0; sem < 6; sem++){
    for (let d = 0; d < 7; d++){
      const fecha = new Date(inicio);
      fecha.setDate(inicio.getDate() + sem * 7 + d);
      const fStr = fechaLocalStr(fecha);
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
          // Sugerencia IA · NO está en BD · click abre modal especial
          grid += '<div class="' + ltCls + esGrande + '" draggable="true" data-key="' + dragKey + '" data-prod="' + escapeHtml(lt.producto) + '" data-kg="' + lt.kg + '" data-from="' + fStr + '" ondragstart="onDragStart(event)" ondragend="onDragEnd(event)" onclick="abrirSugerenciaModal(&quot;' + escapeHtml(lt.producto) + '&quot;,&quot;' + fStr + '&quot;,' + lt.kg + ',&quot;' + escapeHtml(lt.motivo || '') + '&quot;)" title="✨ Sugerencia IA · click para detalles · arrastrá para mover">';
          grid += '<span>✨ ' + escapeHtml(prodCorto) + '<br><span style="opacity:.7">' + lt.kg + 'kg</span></span>';
          grid += '</div>';
        } else {
          // Sebastián 19-may-2026: lo Fijo (eos_plan / eos_b2b / eos_retroactivo)
          // se ve con candado · los procesos automáticos no lo tocan.
          const esFijo = ['eos_plan','eos_b2b','eos_retroactivo'].indexOf(lt.origen) >= 0;
          const candado = esFijo ? '🔒 ' : '';
          const fijoTip = esFijo ? ' · 🔒 FIJO (los automáticos no lo tocan)' : '';
          // Sebastián 25-may-2026 PM · desglose DTC vs B2B en celda.
          // lt.desglose_b2b viene del backend · array de {cliente, kg, ...}.
          // Si hay B2B atribuido: muestra "12kg · 8 DTC + 4 Fer" (cliente corto).
          // Si no hay desglose: muestra solo "12kg" (asumido DTC).
          // split_inconsistente: más B2B atribuido que el total · marca ⚠.
          let lineaKg = lt.kg + 'kg';
          let tipSplit = '';
          const desg = lt.desglose_b2b || [];
          if (desg.length > 0){
            const kgB2B = lt.kg_b2b_total || 0;
            const kgDTC = lt.kg_dtc || 0;
            const partes = [];
            if (kgDTC > 0.05) partes.push(kgDTC + ' DTC');
            desg.forEach(d => {
              const clCorto = (d.cliente || 'B2B').split(/\s+/)[0].slice(0, 8);
              partes.push(d.kg + ' ' + clCorto);
            });
            lineaKg = lt.kg + 'kg · ' + partes.join('+');
            tipSplit = ' · desglose: ' +
              (kgDTC > 0.05 ? kgDTC + 'kg DTC + ' : '') +
              desg.map(d => d.kg + 'kg ' + d.cliente).join(' + ');
            if (lt.split_inconsistente) lineaKg = '⚠ ' + lineaKg;
          }
          grid += '<div class="' + ltCls + esGrande + '" draggable="true" data-key="' + dragKey + '" data-prod="' + escapeHtml(lt.producto) + '" data-kg="' + lt.kg + '" data-from="' + fStr + '" ondragstart="onDragStart(event)" ondragend="onDragEnd(event)" onclick="abrirLoteModal(' + lt.id + ',&quot;' + escapeHtml(lt.producto) + '&quot;,&quot;' + fStr + '&quot;,' + lt.kg + ')" title="' + escapeHtml(lt.producto + ' · ' + lt.kg + 'kg · click detalle · arrastrá para mover' + fijoTip + tipSplit) + '">';
          grid += '<span>' + candado + escapeHtml(prodCorto) + '<br><span style="opacity:.7;font-size:9.5px">' + escapeHtml(lineaKg) + '</span></span>';
          grid += '</div>';
        }
      });

      grid += '</div>';
    }
  }
  grid += '</div>';

  document.getElementById('cal-grid-wrap').innerHTML = grid;
  // Sebastián 14-may-2026: diag pintado en DOM · "no sale nada"
  // Mostrar VISIBLE en pantalla (no solo consola)
  try {
    const _pintados = document.querySelectorAll('#cal-grid-wrap .lote');
    const _prodPintados = new Set();
    _pintados.forEach(el => _prodPintados.add(el.dataset.prod));
    // Sebastián 16-may-2026: contar días con lote SOLO del mes navegado
    // (antes contaba lotesPorFecha global · mezclaba todos los meses).
    const _mesRef = ref.getFullYear() + '-' + String(ref.getMonth()+1).padStart(2,'0');
    const _fechasConLotes = Object.keys(lotesPorFecha).filter(
      f => f.slice(0,7) === _mesRef && lotesPorFecha[f].length > 0);
    const ag = PLAN_DATA.agendadas || [];
    const _prodBackend = new Set(); ag.forEach(a => _prodBackend.add(a.producto));
    const mesMostrado = MESES[ref.getMonth()] + ' ' + ref.getFullYear();
    let diagMsg = '📊 ' + mesMostrado +
      ' · Backend devolvió <strong>' + ag.length + ' lotes</strong> en <strong>' + _prodBackend.size + ' productos</strong>' +
      ' · Pintados en grid: <strong>' + _pintados.length + ' div.lote</strong>' +
      ' · ' + _prodPintados.size + ' productos únicos visibles' +
      ' · ' + _fechasConLotes.length + ' días con lote en ' + mesMostrado;
    if (ag.length > 0 && _pintados.length === 0){
      // El mes navegado no tiene lotes · ver en qué meses SÍ hay
      const _meses = {};
      ag.forEach(a => {
        const mm = (a.fecha_programada || '').slice(0, 7);
        if (mm) _meses[mm] = (_meses[mm] || 0) + 1;
      });
      const _listaMeses = Object.keys(_meses).sort()
        .map(mm => mm + ' (' + _meses[mm] + ')').join(' · ');
      diagMsg = '📭 <strong>' + mesMostrado + ' no tiene lotes.</strong> ' +
        'Hay ' + ag.length + ' lotes en otros meses · usá <strong>Siguiente →</strong> ' +
        'para verlos.<br><span style="font-size:10px">Meses con lotes: ' +
        escapeHtml(_listaMeses) + '</span>';
    }
    if (ag.length === 0){
      diagMsg = '<span style="color:#dc2626;font-weight:700">⚠ Backend devolvió 0 lotes</span> · el plan está vacío · apretá "🤖 Generar plan IA"';
    }
    document.getElementById('cal-diag').innerHTML = diagMsg;
    console.log('[CAL.render] mes=' + mesMostrado + ' pintados=' + _pintados.length + ' productos_pintados=[' + [..._prodPintados].join('|') + '] fechas_con_lote=' + _fechasConLotes.length);
  } catch(e){
    document.getElementById('cal-diag').textContent = '⚠ diag error: ' + e.message;
    console.warn('diag pintado err', e);
  }
  // Activar drop en cada cal-day
  document.querySelectorAll('.cal-day').forEach(cell => {
    cell.addEventListener('dragover', onDragOver);
    cell.addEventListener('dragleave', onDragLeave);
    cell.addEventListener('drop', onDrop);
  });

  // Lista sugeridas con acciones
  renderListaSugerencias();
}

// ═══════ ALERTAS IA · Sebastián 19-may-2026 ═══════
// Banner proactivo arriba del calendario · cobertura crítica, adelantar
// lotes, pedidos B2B con MP faltante.
async function cargarAlertasVentas(){
  // 30-may-2026 · audit Plan · ventas de SKUs NO mapeados a producto NO entran
  // al cálculo de velocidad → necesidades subestimadas. Banner visible + acción.
  const wrap = document.getElementById('alertas-ventas-wrap');
  if (!wrap) return;
  try{
    const r = await fetch('/api/admin/skus-huerfanos-top?limit=10', {cache:'no-store'});
    if(!r.ok){ wrap.innerHTML=''; return; }
    const d = await r.json();
    const uds = d.uds_huerfanas_total_60d || 0;
    const n = d.n_huerfanos_total || 0;
    if(!uds || uds <= 0){ wrap.innerHTML=''; return; }
    const top = (d.huerfanos_top || []).slice(0,6)
      .map(h => escapeHtml(h.sku) + ' (' + Math.round(h.uds_60d) + ')').join(' · ');
    wrap.innerHTML =
      '<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
      + '<div style="font-size:1.4em">⚠️</div>'
      + '<div style="flex:1;min-width:240px;font-size:13px;color:#92400e">'
      + '<b>' + Math.round(uds).toLocaleString('es-CO') + ' uds vendidas en 60d SIN mapear a producto</b> (' + n + ' SKUs). '
      + 'Estas ventas NO cuentan en la velocidad → las necesidades de esos productos salen subestimadas.'
      + (top ? '<div style="font-size:11px;margin-top:4px;opacity:.85">Top: ' + top + '</div>' : '')
      + '</div>'
      + '<a href="/herramientas#skus-huerfanos" style="background:#f59e0b;color:#fff;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:700">Mapear SKUs</a>'
      + '</div>';
  }catch(e){ wrap.innerHTML=''; }
}

async function cargarAlertasIA(){
  const wrap = document.getElementById('alertas-ia-wrap');
  if (!wrap) return;
  try {
    const r = await fetch('/api/plan/alertas-ia', {cache: 'no-store'});
    if (!r.ok){ wrap.style.display = 'none'; return; }
    const d = await r.json();
    const al = d.alertas || [];
    if (al.length === 0){
      wrap.style.display = 'none';
      return;
    }
    const SEV_STYLE = {
      critica: {bg:'#fee2e2', border:'#dc2626', txt:'#991b1b'},
      advertencia: {bg:'#fef3c7', border:'#ca8a04', txt:'#854d0e'},
      info: {bg:'#dbeafe', border:'#1e40af', txt:'#1e40af'},
    };
    const totals = d.por_severidad || {};
    let html = '<div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:12px;padding:12px 14px;color:#fff;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
    html += '<div><span style="font-size:14px;font-weight:800">🤖 Alertas IA del Plan</span> <span style="font-size:11px;opacity:.85;margin-left:8px">' +
      (totals.critica || 0) + ' crítica(s) · ' +
      (totals.advertencia || 0) + ' advertencia(s) · ' +
      (totals.info || 0) + ' info</span></div>';
    html += '<button onclick="cargarAlertasIA()" style="background:rgba(255,255,255,.12);border:1px solid #fff;color:#fff;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer">↻ Refrescar</button>';
    html += '</div>';
    al.forEach((a, idx) => {
      const sev = SEV_STYLE[a.severidad] || SEV_STYLE.info;
      const accionBtn = _alertaAccionBtn(a, idx);
      html += '<div style="background:' + sev.bg + ';border-left:4px solid ' + sev.border +
        ';border-radius:6px;padding:10px 14px;margin-bottom:6px;color:' + sev.txt +
        ';display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">';
      html += '<div style="flex:1;min-width:240px"><div style="font-weight:700;font-size:13px">' +
        escapeHtml(a.titulo) + '</div>';
      html += '<div style="font-size:11px;margin-top:2px;opacity:.95">' + escapeHtml(a.detalle) + '</div></div>';
      html += '<div style="display:flex;gap:5px">';
      if (accionBtn) html += accionBtn;
      html += '<button onclick="this.parentElement.parentElement.style.display=&quot;none&quot;" style="background:transparent;border:1px solid currentColor;color:inherit;padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer" title="Ocultar esta alerta">✕</button>';
      html += '</div></div>';
    });
    wrap.innerHTML = html;
    wrap.style.display = 'block';
  } catch(e){
    console.warn('cargarAlertasIA falló:', e);
    wrap.style.display = 'none';
  }
}

function _alertaAccionBtn(a, idx){
  if (a.accion === 'generar_lote' && a.payload){
    const p = a.payload;
    const onClick = 'abrirGenerarDesdeAlerta(&quot;' + escapeHtml(p.producto || '') +
                    '&quot;,' + (p.kg_sugerido || 0) +
                    ',&quot;' + escapeHtml(p.fecha_sugerida || '') + '&quot;)';
    return '<button onclick="' + onClick +
           '" style="background:#0f766e;color:#fff;border:none;padding:5px 12px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">⚡ Programar</button>';
  }
  if (a.accion === 'ver_abastecimiento'){
    return '<button onclick="window.parent && window.parent.switchProgTab ? window.parent.switchProgTab(&quot;abastecimiento&quot;) : window.open(&quot;/dashboard&quot;,&quot;_top&quot;)" style="background:#7c3aed;color:#fff;border:none;padding:5px 12px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">📦 Abastecimiento</button>';
  }
  return '';
}

function abrirGenerarDesdeAlerta(producto, kg, fecha){
  // Reusa el modal generar producción si existe en parent · sino fallback
  if (window.parent && typeof window.parent.abrirGenerarProduccion === 'function'){
    try { window.parent.abrirGenerarProduccion(producto, kg, fecha); return; } catch(e){}
  }
  // Fallback · abrir cargar lote vía endpoint admin lote-manual
  const ok = confirm('¿Programar lote de ' + producto + '?\\n\\n' +
                     kg + 'kg · fecha sugerida ' + fecha +
                     '\\n\\nSe creará como FIJO (eos_plan).');
  if (!ok) return;
  fetch('/api/plan/lote-manual', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': (document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)||['',''])[1] || ''},
    body: JSON.stringify({producto_nombre: producto, kg: kg, fecha: fecha}),
  }).then(r => r.json()).then(d => {
    if (d.ok || d.id) {
      alert('✓ Lote programado · ID ' + (d.id || '?'));
      cargar();
    } else {
      alert('No se pudo programar · ' + (d.error || 'usá Necesidades para crearlo manual'));
    }
  }).catch(e => alert('Error: ' + e.message));
}

function renderListaSugerencias(){
  const filtroSoloIA = document.getElementById('filtro-solo-ia')?.checked || false;
  const itemsAll = (PLAN_DATA.plan.plan_items || []);
  const items = filtroSoloIA ? itemsAll.filter(it => it.from_ia) : itemsAll;
  if (!items.length){
    const msg = filtroSoloIA ? 'No hay sugerencias de IA cargadas · apretá "🤖 Autoplan con IA"' : 'No hay sugerencias para este horizonte · todo cubierto';
    document.getElementById('sugerencias-lista').innerHTML = '<div class="muted" style="padding:20px;text-align:center">' + msg + '</div>';
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

// Sebastián 30-may-2026 · navegar al lote anterior/siguiente (por fecha) sin
// cerrar el modal. dir = -1 (anterior) | +1 (siguiente).
function navLoteModal(dir){
  const cur = window._LOTE_MODAL_ACTUAL;
  if(!cur){ return; }
  // Lista de lotes agendados ordenada por fecha · luego producto · luego id
  const lista = (PLAN_DATA && PLAN_DATA.agendadas ? PLAN_DATA.agendadas.slice() : [])
    .filter(a => a && a.id != null)
    .sort((a,b) => {
      const fa = (a.fecha_programada||'').slice(0,10), fb = (b.fecha_programada||'').slice(0,10);
      if(fa !== fb) return fa < fb ? -1 : 1;
      const pa = a.producto||'', pb = b.producto||'';
      if(pa !== pb) return pa < pb ? -1 : 1;
      return (a.id||0) - (b.id||0);
    });
  if(!lista.length){ return; }
  let idx = lista.findIndex(a => a.id === cur.id);
  if(idx < 0){ idx = 0; }
  const ni = idx + dir;
  if(ni < 0 || ni >= lista.length){
    // Borde · feedback sutil (no romper)
    const btn = document.getElementById(dir < 0 ? 'lote-nav-prev' : 'lote-nav-next');
    if(btn){ btn.style.opacity = '0.35'; setTimeout(()=>{ btn.style.opacity=''; }, 400); }
    return;
  }
  const nx = lista[ni];
  abrirLoteModal(nx.id, nx.producto, (nx.fecha_programada||'').slice(0,10), nx.kg || nx.cantidad_kg || 0);
}

function buscarNecesidadProducto(producto){
  // Busca info de Necesidades sobre el producto · velocidad, ml, etc
  if (!PLAN_DATA || !PLAN_DATA.plan) return null;
  const ctx = (PLAN_DATA.plan.contexto_enviado && PLAN_DATA.plan.contexto_enviado.productos) || [];
  return ctx.find(p => (p.nombre || '').toUpperCase() === producto.toUpperCase()) || null;
}

// Normaliza · sin acentos · upper · trim · útil para matching de nombres
// Fix B-4 · regex creado con string + new RegExp para evitar literales combinantes
function _norm(s){
  const reMarks = new RegExp('[\\u0300-\\u036F]', 'g');
  return String(s || '').normalize('NFD').replace(reMarks,'').toUpperCase().trim().replace(/\s+/g, ' ');
}

// Fix B-2 · escape para atributos HTML (previene XSS si producto tiene comilla)
// Reemplaza " por &quot; y ' por &#39; antes de meter en onclick.
function escAttr(s){
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Modal para sugerencias IA (✨ amarillas punteadas) · NO están en BD ·
// permite ver detalle, agendar, modificar o ignorar antes de aplicar
async function abrirSugerenciaModal(producto, fecha, kg, motivo){
  document.getElementById('lote-titulo').textContent = '✨ Sugerencia · ' + producto;
  document.getElementById('lote-body').innerHTML = '<div class="muted" style="padding:30px;text-align:center">Cargando…</div>';
  document.getElementById('loteModal').classList.add('show');

  // Datos del producto (igual que abrirLoteModal)
  let info = null;
  try {
    const r = await fetch('/api/plan/necesidades');
    if (r.ok){
      const d = await r.json();
      const animus = (d.clientes || []).find(c => c.cliente_id === 'ANIMUS_DTC');
      const todos = (animus && animus.productos) || [];
      const target = _norm(producto);
      info = todos.find(p => _norm(p.producto_nombre) === target);
      if (!info) info = todos.find(p => _norm(p.producto_nombre).includes(target) || target.includes(_norm(p.producto_nombre)));
    }
  } catch(e){}

  // Buscar el item en plan_items para confianza/razonamiento
  const it = (PLAN_DATA.plan.plan_items || []).find(x => x.producto === producto && x.fecha === fecha);

  let html = '';
  html += '<div class="banner-inline info"><strong>Esta es una sugerencia del autoplan IA</strong> · todavía NO está agendada en EOS. Apretá "Agendar ahora" para confirmarla, o "Ignorar" para descartarla.</div>';

  if (info){
    const ml = info.ml_unidad || 30;
    const velUds = info.velocidad_uds_dia || 0;
    const velMes = Math.round(velUds * 30);
    const velKgDia = info.velocidad_kg_dia || 0;
    html += '<div class="metric-grid">';
    html += '<div class="metric-card"><div class="metric-lbl">Volumen envase</div><div class="metric-val">' + ml + ' ml</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Kg a producir</div><div class="metric-val">' + kg + ' kg</div><div class="metric-sub">' + Math.round(kg * 1000 / ml) + ' uds aprox</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Vende/día</div><div class="metric-val">' + velUds.toFixed(1) + '</div><div class="metric-sub">' + velKgDia.toFixed(2) + ' kg/día</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Vende/mes</div><div class="metric-val">' + velMes + '</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Stock actual</div><div class="metric-val">' + (info.stock_uds_total || 0) + ' uds</div></div>';
    html += '<div class="metric-card"><div class="metric-lbl">Cobertura actual</div><div class="metric-val">' + (info.dias_cobertura != null ? info.dias_cobertura + 'd' : '—') + '</div><div class="metric-sub">' + (info.urgencia || '') + '</div></div>';
    html += '</div>';
    // Próxima producción tras este lote · buffer 25d (sincronizado con
    // cob_alerta backend · Sebastián 23-may-2026)
    if (velKgDia > 0.001 && kg > 0){
      const diasDura = Math.round(kg / velKgDia);
      const fProx = new Date(fecha + 'T12:00:00');
      fProx.setDate(fProx.getDate() + Math.max(diasDura - 25, 1));
      html += '<div class="banner-inline ok">🔁 Este lote durará ~' + diasDura + ' días · próxima producción sugerida: <strong>' + fechaLocalStr(fProx) + '</strong></div>';
    }
  }

  // Info IA
  if (it && it.from_ia){
    html += '<div class="banner-inline warn"><strong>🤖 Razonamiento IA</strong>';
    if (it.confianza) html += ' · confianza ' + Math.round(it.confianza * 100) + '%';
    html += '<br>' + escapeHtml(it.razonamiento_ia || it.motivo || '(sin detalle)') + '</div>';
  } else {
    html += '<div class="banner-inline info"><strong>Motivo:</strong> ' + escapeHtml(motivo || 'auto-plan') + ' · fecha sugerida ' + fecha + ' · cantidad ' + kg + ' kg</div>';
  }

  // Acciones específicas para sugerencia
  html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:1px solid #e2e8f0">';
  html += '<button onclick="agendarSugerencia(&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;,' + kg + ')" class="success">✅ Agendar ahora</button>';
  html += '<button onclick="modificarSugerencia(&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="secondary">📅 Cambiar fecha</button>';
  html += '<button onclick="modificarSugerenciaKg(&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;,' + kg + ')" class="secondary">⚖ Cambiar kg</button>';
  html += '<button onclick="ignorarSugerenciaModal(&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;)" class="danger">✕ Ignorar</button>';
  html += '<div style="flex-basis:100%;font-size:11px;color:#64748b;margin-top:6px">💡 También podés arrastrar al calendario para cambiar la fecha</div>';
  html += '</div>';

  document.getElementById('lote-body').innerHTML = html;
}

async function agendarSugerencia(producto, fecha, kg){
  cerrarLoteModal();
  // Sebastián 14-may-2026: "no sé es como hacer que quede ya allí como
  // plan y todos lo vean, y además empezar a moverlo si al aceptar
  // aparece en futuro durante un año".
  // Cambio: en vez de 1 lote único, preguntar frecuencia y crear serie
  // anual (eos_canonico). Default 60 días si el usuario no responde.
  const rawFreq = prompt(
    '¿Agendar este producto como CANÓNICO ANUAL?\\n\\n' +
    'Producto: ' + producto + '\\n' +
    'Primer lote: ' + fecha + ' · ' + kg + 'kg\\n\\n' +
    'Frecuencia días entre lotes (cada cuántos días se produce):\\n' +
    '• 30 = mensual\\n' +
    '• 45 = cada 45 días\\n' +
    '• 60 = cada 2 meses (default)\\n' +
    '• 90 = trimestral',
    '60'
  );
  if (rawFreq === null) return;  // usuario canceló
  const freq = parseInt(rawFreq);
  if (isNaN(freq) || freq < 7 || freq > 180){
    alert('Frecuencia inválida · debe estar entre 7 y 180 días');
    return;
  }
  try {
    const r = await fetch('/api/plan/programar-canonico', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({
        producto_nombre: producto,
        cantidad_kg: kg,
        frecuencia_dias: freq,
        horizonte_dias: 365,
        fecha_inicio: fecha,
        notas: 'Agendado desde IA · serie anual cada ' + freq + 'd',
      }),
    });
    let d = null; let txt = '';
    try { d = await r.json(); } catch(e){ txt = await r.text(); }
    if (!r.ok){
      const errMsg = (d && (d.error || d.message)) || txt || ('HTTP ' + r.status);
      alert('❌ No se pudo agendar serie anual:\\n\\n' + errMsg +
            (r.status === 403 ? '\\n\\nProbable: MFA no activado · /seguridad' : ''));
      return;
    }
    // Quitar de plan_items (ya agendada) + feedback IA
    const idx = (PLAN_DATA.plan.plan_items || []).findIndex(x => x.producto === producto && x.fecha === fecha);
    if (idx >= 0){
      const it = PLAN_DATA.plan.plan_items[idx];
      if (it.from_ia && it.decision_id) feedbackIA(it.decision_id, 'aceptada', kg, fecha, null);
      PLAN_DATA.plan.plan_items.splice(idx, 1);
    }
    alert('✅ Serie anual creada\\n\\n' +
          '• ' + (d.lotes_creados ? d.lotes_creados.length : (d.total || 0)) + ' lotes generados\\n' +
          '• Cada ' + freq + ' días\\n' +
          '• Horizonte 365 días\\n\\n' +
          'Aparecerán en el calendario · arrastrá cualquiera para moverlo.');
    cargar();
  } catch(e){ alert('Error de red: ' + e.message); }
}

function modificarSugerencia(producto, fecha){
  cerrarLoteModal();
  const it = (PLAN_DATA.plan.plan_items || []).find(x => x.producto === producto && x.fecha === fecha);
  const idx = (PLAN_DATA.plan.plan_items || []).findIndex(x => x.producto === producto && x.fecha === fecha);
  if (idx < 0) return;
  const nueva = prompt('Cambiar fecha de la sugerencia\\n\\n' + producto + '\\nActual: ' + fecha + '\\n\\nNueva (YYYY-MM-DD):', fecha);
  if (!nueva || nueva === fecha) return;
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(nueva.trim())){ alert('Formato inválido'); return; }
  it.fecha = nueva.trim();
  if (it.from_ia && it.decision_id) feedbackIA(it.decision_id, 'movida', it.kg, nueva.trim(), 'Cambio desde modal');
  render();
}

function modificarSugerenciaKg(producto, fecha, kg){
  cerrarLoteModal();
  const it = (PLAN_DATA.plan.plan_items || []).find(x => x.producto === producto && x.fecha === fecha);
  if (!it) return;
  // Fix B-3 · check del raw string ANTES de parseFloat para detectar cancel vs valor inválido
  const raw = prompt('Cambiar kg de la sugerencia\\n\\n' + producto + '\\nActual: ' + kg + 'kg\\n\\nNueva cantidad (kg):', String(kg));
  if (raw === null) return;  // usuario canceló
  const nuevaKg = parseFloat(raw);
  if (isNaN(nuevaKg) || nuevaKg <= 0){ alert('Cantidad inválida'); return; }
  it.kg = nuevaKg;
  if (it.from_ia && it.decision_id) feedbackIA(it.decision_id, 'movida', nuevaKg, fecha, 'Cambio kg desde modal');
  render();
}

function ignorarSugerenciaModal(producto, fecha){
  cerrarLoteModal();
  if (!confirm('¿Descartar esta sugerencia del autoplan?')) return;
  const idx = (PLAN_DATA.plan.plan_items || []).findIndex(x => x.producto === producto && x.fecha === fecha);
  if (idx >= 0){
    const it = PLAN_DATA.plan.plan_items[idx];
    if (it.from_ia && it.decision_id) feedbackIA(it.decision_id, 'ignorada', null, null, null);
    PLAN_DATA.plan.plan_items.splice(idx, 1);
    render();
  }
}

// Parsea observaciones del lote para extraer aportes B2B · Sebastián 19-may-2026.
// Devuelve { kg_total, entradas: [{cliente, kg, color}], kg_residual_dtc }
// Patrones soportados (de _integrar_pedido_b2b_al_plan):
//   · "+Xkg B2B <Cliente> (pedido #N)" → suma a lote canónico
//   · "Pedido B2B <Cliente> · #N · entrega estimada ..." → lote dedicado eos_b2b
function _parsearComposicionLote(loteData, kgTotal){
  if (!loteData) return null;
  const obs = String(loteData.observaciones || '');
  const origen = String(loteData.origen || '');
  const kgT = parseFloat(kgTotal) || 0;
  const entradas = [];
  const PALETA = ['#db2777', '#7c3aed', '#0891b2', '#ca8a04', '#dc2626', '#16a34a'];
  let idx = 0;
  const _color = () => PALETA[(idx++) % PALETA.length];

  // 0) FUENTE PRIMARIA · desglose estructurado desde pedidos_b2b_lote (mig 171),
  //    que el listado ya trae en cada lote (desglose_b2b + kg_dtc). Sebastián
  //    30-may-2026: antes solo se parseaba el TEXTO de observaciones, así que los
  //    lotes con B2B vinculado pero SIN nota en obs (la mayoría) salían "100%
  //    Animus" y el consumo no restaba al cliente. Ahora se usa la tabla → TODOS
  //    los lotes con Kelly/etc. muestran el desglose y el DTC correcto.
  const desg = loteData.desglose_b2b;
  if (Array.isArray(desg) && desg.length){
    const porPed = {};   // dedupe defensivo por pedido_id
    desg.forEach(function(x){
      const key = (x.pedido_id != null) ? ('p' + x.pedido_id) : ((x.cliente||'') + '|' + x.kg);
      porPed[key] = { cliente: x.cliente || 'B2B', kg: parseFloat(x.kg) || 0 };
    });
    let b2bTot = 0;
    Object.keys(porPed).forEach(function(k){
      entradas.push({ cliente: porPed[k].cliente, kg: porPed[k].kg, color: _color() });
      b2bTot += porPed[k].kg;
    });
    const kgDTC = (loteData.kg_dtc != null) ? parseFloat(loteData.kg_dtc) : Math.max(kgT - b2bTot, 0);
    if (kgDTC > 0.01){
      entradas.unshift({ cliente: 'Animus DTC', kg: Math.round(kgDTC * 100) / 100, color: '#0f766e' });
    }
    return { kg_total: kgT, entradas, kg_residual_dtc: Math.max(kgDTC, 0) };
  }

  // 1) Lote dedicado eos_b2b: 100% del kg al cliente del pedido
  if (origen === 'eos_b2b'){
    const m = obs.match(/Pedido B2B (.+?) · #(\d+)/);
    if (m){
      entradas.push({ cliente: m[1].trim(), kg: kgT, color: _color() });
      return { kg_total: kgT, entradas, kg_residual_dtc: 0 };
    }
  }

  // 2) Lote canónico con sumados: extraer cada "+Xkg B2B <Cliente> (pedido #N)"
  // FIX 30-may-2026 · Sebastián "en BHA Kelly sale dos veces": si la integración
  // B2B corrió >1 vez, el aporte queda escrito 2× en observaciones y se contaba
  // doble (kg_residual_dtc se hundía → duración mal). Deduplicamos por # de
  // pedido (último valor gana) → cada pedido cuenta UNA sola vez.
  const reSum = /\+(\d+(?:\.\d+)?)\s*kg\s+B2B\s+(.+?)\s*\(pedido\s+#(\d+)\)/gi;
  let mm;
  const porPedido = {};
  while ((mm = reSum.exec(obs)) !== null){
    porPedido[mm[3]] = { cliente: mm[2].trim(), kg: parseFloat(mm[1]) || 0 };
  }
  let aportadoTotal = 0;
  Object.keys(porPedido).forEach(function(ped){
    entradas.push({ cliente: porPedido[ped].cliente, kg: porPedido[ped].kg, color: _color() });
    aportadoTotal += porPedido[ped].kg;
  });
  // Lo que queda (total − B2B) es DTC / Animus
  const kgDTC = Math.max(kgT - aportadoTotal, 0);
  if (kgDTC > 0.01){
    entradas.unshift({ cliente: 'Animus DTC', kg: kgDTC, color: '#0f766e' });
  }
  return { kg_total: kgT, entradas, kg_residual_dtc: kgDTC };
}

// Sebastián 25-may-2026 PM · cache de envases para el dropdown.
// Se llena en primera carga · subsecuentes lotes usan el mismo cache.
window._MEES_CACHE = null;

// FIX 27-may-2026 PM · Sebastián · "el calendario debe colocar la realidad
// del envase, que lo tenga cada producción". Cache por lote_id de la
// composición ya calculada (evita re-fetch al re-abrir el mismo modal).
window._COMP_MEE_CACHE = window._COMP_MEE_CACHE || {};

// FIX 27-may-2026 PM · Sebastián · "deberias dejarme poder editar la cantidad
// de envases por si esta mal lo hago manual · pero para todos los producto, y
// que cuando se cambie calcule perfecto". Editar uds/mes de referencia de una
// presentación · afecta todos los lotes futuros (es ratio del producto).
async function _editarUdsMesPresentacion(loteId, productoEnc, codigo, etiqueta, volMl, envaseCodigo, udsActuales){
  const producto = decodeURIComponent(productoEnc);
  const nueva = prompt(
    'Editar uds/mes de referencia · ' + producto + ' · ' + etiqueta + '\\n\\n' +
    'Este número se usa como referencia para el ratio de envases en TODOS los lotes futuros (planificación).\\n' +
    'El descuento real ocurre cuando fabricación termina envasado.\\n\\n' +
    'Uds/mes actual estimadas para este lote: ' + udsActuales + '\\n' +
    'Ingresá las uds/mes REALES (0 = no se vende esa presentación):',
    ''
  );
  if (nueva === null) return;  // cancel
  const valor = parseFloat(nueva);
  if (isNaN(valor) || valor < 0){ alert('Número inválido · debe ser ≥ 0'); return; }
  // Obtener CSRF
  let csrf = '';
  try {
    if (window._csrfTok) { csrf = window._csrfTok; }
    else {
      const tr = await fetch('/api/csrf-token', {credentials:'same-origin'});
      if (tr.ok){ const td = await tr.json(); csrf = td.csrf_token || ''; window._csrfTok = csrf; }
    }
  } catch(_){}
  try {
    const r = await fetch('/api/admin/producto-presentaciones-upsert', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
      body: JSON.stringify({
        producto_nombre: producto,
        presentacion_codigo: codigo,
        etiqueta: etiqueta,
        volumen_ml: volMl,
        envase_codigo: envaseCodigo,
        ventas_mes_referencia: valor,
      })
    });
    const d = await r.json();
    if(r.ok && d.ok){
      // Invalida cache · recarga composición
      delete window._COMP_MEE_CACHE[loteId];
      const box = document.getElementById('comp-mee-' + loteId);
      if (box) box.innerHTML = '<span style="opacity:.7">⏳ Recalculando...</span>';
      _cargarComposicionMee(loteId);
    } else {
      alert('Error ' + r.status + ': ' + (d.error || 'desconocido'));
    }
  } catch(e){
    alert('Error red: ' + e.message);
  }
}

// Sebastián 30-may-2026 · cantidad FIJA por lote para una presentación.
// Caso SUERO ILUMINADOR TRX: 10ml = SIEMPRE 1200 uds (no %). El sistema reserva
// esas uds primero y reparte el resto del bulk en las demás presentaciones.
// Sebastián 30-may-2026 · cantidad FIJA · pregunta el alcance:
//  · TODAS las futuras → cambia el DEFAULT del producto (producto_presentaciones)
//  · solo ESTE lote → override por lote (produccion_programada.fija_override_json)
// Vacío → quita el override de este lote (vuelve al default).
async function _fijarUdsPresentacion(loteId, productoEnc, codigo, etiqueta, volMl, envaseCodigo, efectiva, defaultUds, esOverride){
  const producto = decodeURIComponent(productoEnc);
  const msg = 'Cantidad fija de "' + etiqueta + '" (' + producto + ')\\n\\n' +
    'Default del producto (todas las futuras): ' + (defaultUds || 0) + ' uds' +
    (esOverride ? '  ·  override SOLO este lote: ' + (efectiva || 0) : '') + '\\n\\n' +
    'Escribí las uds (ej. 1200), o dejá VACÍO para quitar el override de este lote.';
  const nueva = prompt(msg, String(efectiva || 0));
  if (nueva === null) return;  // cancel
  const limpio = nueva.trim();
  let csrf = '';
  try {
    if (window._csrfTok) { csrf = window._csrfTok; }
    else {
      const tr = await fetch('/api/csrf-token', {credentials:'same-origin'});
      if (tr.ok){ const td = await tr.json(); csrf = td.csrf_token || ''; window._csrfTok = csrf; }
    }
  } catch(_){}
  const _recalc = (r, d) => {
    if(r.ok && d && d.ok){
      delete window._COMP_MEE_CACHE[loteId];
      const box = document.getElementById('comp-mee-' + loteId);
      if (box) box.innerHTML = '<span style="opacity:.7">⏳ Recalculando...</span>';
      _cargarComposicionMee(loteId);
    } else { alert('Error ' + (r.status||'') + ': ' + ((d && d.error) || 'desconocido')); }
  };
  // Caso 1 · VACÍO → quitar override de este lote (vuelve al default)
  if (limpio === ''){
    try {
      const r = await fetch('/api/programacion/lote/' + loteId + '/fija-override', {
        method:'PATCH', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
        body: JSON.stringify({ presentacion_codigo: codigo, uds: '' })
      });
      _recalc(r, await r.json());
    } catch(e){ alert('Error red: ' + e.message); }
    return;
  }
  const valor = parseFloat(limpio);
  if (isNaN(valor) || valor < 0){ alert('Número inválido · debe ser ≥ 0 (o vacío para quitar el override)'); return; }
  // Preguntar ALCANCE
  const todasFuturas = confirm(
    '¿Aplicar ' + valor + ' uds a TODAS las producciones futuras de "' + producto + '" (' + etiqueta + ')?\\n\\n' +
    '• ACEPTAR = TODAS las futuras (cambia el default del producto)\\n' +
    '• CANCELAR = SOLO este lote'
  );
  try {
    let r, d;
    if (todasFuturas){
      // Default del producto · aplica a todas las futuras
      r = await fetch('/api/admin/producto-presentaciones-upsert', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
        body: JSON.stringify({ producto_nombre: producto, presentacion_codigo: codigo,
          etiqueta: etiqueta, volumen_ml: volMl, envase_codigo: envaseCodigo,
          cantidad_fija_uds: valor })
      });
      d = await r.json();
      // Limpiar el override de ESTE lote para que use el nuevo default
      try {
        await fetch('/api/programacion/lote/' + loteId + '/fija-override', {
          method:'PATCH', credentials:'same-origin',
          headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
          body: JSON.stringify({ presentacion_codigo: codigo, uds: '' })
        });
      } catch(_){}
    } else {
      // Solo este lote · override
      r = await fetch('/api/programacion/lote/' + loteId + '/fija-override', {
        method:'PATCH', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
        body: JSON.stringify({ presentacion_codigo: codigo, uds: valor })
      });
      d = await r.json();
    }
    _recalc(r, d);
  } catch(e){
    alert('Error red: ' + e.message);
  }
}
async function _cargarComposicionMee(loteId){
  const box = document.getElementById('comp-mee-' + loteId);
  if(!box) return;
  // Cache hit
  if(window._COMP_MEE_CACHE[loteId]){
    box.innerHTML = window._COMP_MEE_CACHE[loteId];
    return;
  }
  try{
    const r = await fetch('/api/programacion/programar/' + loteId + '/composicion-mee', {credentials:'same-origin'});
    if(!r.ok){ box.style.display='none'; return; }
    const d = await r.json();
    if(!d.ok || !d.variantes || d.variantes.length === 0){
      box.innerHTML = '<span style="font-weight:700">📐 Composición:</span> <span style="opacity:.7">producto sin variantes configuradas · usa envase default</span>';
      return;
    }
    const fuenteTxt = {
      'shopify_90d': '<span style="color:#15803d;font-weight:700">📊 ratio Shopify 90d</span>',
      'uniforme': '<span style="color:#a16207;font-weight:700">⚖ ratio uniforme (sin ventas históricas)</span>',
      'unica': '<span style="color:#6b7280;font-weight:700">1 sola variante</span>',
    }[d.fuente_ratio] || d.fuente_ratio;
    let h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><span style="font-weight:800;font-size:13px">📐 Composición de envases · ' + d.cantidad_kg + 'kg bulk</span><span style="font-size:10px">' + fuenteTxt + '</span></div>';
    h += '<div style="display:grid;grid-template-columns:1fr;gap:6px">';
    for(const v of d.variantes){
      const esFija = !!v.es_fija;
      const ratioBg = esFija ? '#7c3aed' : (v.ratio_pct >= 50 ? '#0d9488' : (v.ratio_pct >= 25 ? '#0891b2' : '#64748b'));
      const chipTxt = esFija ? ('🔢 ' + v.ratio_pct + '%') : (v.ratio_pct + '%');
      const chipTitle = esFija ? ('FIJA ' + (v.cantidad_fija_uds || 0) + ' uds por lote') : 'porcentaje del bulk';
      h += '<div style="display:grid;grid-template-columns:96px 60px 1fr 96px 66px;gap:6px;align-items:center;background:#fff;border:1px solid #ccfbf1;border-radius:6px;padding:6px 10px;font-size:12px">';
      h += '<div><span title="' + chipTitle + '" style="background:' + ratioBg + ';color:#fff;padding:2px 8px;border-radius:10px;font-weight:700;font-size:11px">' + chipTxt + '</span></div>';
      h += '<div style="font-weight:700;color:#0f766e">' + escapeHtml(v.etiqueta || '') + '</div>';
      h += '<div style="font-family:monospace;font-size:11px;color:#334155">' + escapeHtml(v.envase_codigo || '(sin envase)') + (v.envase_descripcion && v.envase_descripcion !== v.envase_codigo ? ' · <span style="color:#64748b">' + escapeHtml(v.envase_descripcion) + '</span>' : '') + '</div>';
      const fijaTag = esFija ? (v.fija_es_override ? ' <span style="font-size:9px;color:#b45309;font-weight:700" title="override solo para este lote">FIJA·LOTE</span>' : ' <span style="font-size:9px;color:#7c3aed;font-weight:700" title="cantidad fija (default del producto)">FIJA</span>') : '';
      h += '<div style="text-align:right;font-weight:800;color:#0e7490">' + (v.unidades_estimadas || 0).toLocaleString('es-CO') + ' uds' + fijaTag + '</div>';
      const _produ = encodeURIComponent(d.producto || '');
      const _pcodOk = v.presentacion_codigo && v.presentacion_codigo !== '-';
      h += '<div style="display:flex;gap:3px;justify-content:flex-end">';
      // ✏ editar uds/mes de referencia (ratio · afecta TODOS los lotes futuros)
      h += '<button onclick="_editarUdsMesPresentacion(' + loteId + ',&quot;' + _produ + '&quot;,&quot;' + escapeHtml(v.presentacion_codigo || '') + '&quot;,&quot;' + escapeHtml(v.etiqueta || '') + '&quot;,' + (v.volumen_ml || 0) + ',&quot;' + escapeHtml(v.envase_codigo || '') + '&quot;,' + (v.unidades_estimadas || 0) + ')" title="Editar uds/mes de referencia (RATIO · % del bulk)" style="background:#a78bfa;color:#fff;border:0;padding:4px 6px;border-radius:4px;cursor:pointer;font-size:11px">✏</button>';
      // 🔢 cantidad FIJA por lote (ej. 10ml regalo = 1200 uds siempre)
      if(_pcodOk){
        h += '<button onclick="_fijarUdsPresentacion(' + loteId + ',&quot;' + _produ + '&quot;,&quot;' + escapeHtml(v.presentacion_codigo || '') + '&quot;,&quot;' + escapeHtml(v.etiqueta || '') + '&quot;,' + (v.volumen_ml || 0) + ',&quot;' + escapeHtml(v.envase_codigo || '') + '&quot;,' + (v.cantidad_fija_uds || 0) + ',' + (v.cantidad_fija_default || 0) + ',' + (v.fija_es_override ? 'true' : 'false') + ')" title="Cantidad fija · podés aplicarla a TODAS las futuras o solo a este lote" style="background:#0f766e;color:#fff;border:0;padding:4px 6px;border-radius:4px;cursor:pointer;font-size:11px">🔢</button>';
      }
      h += '</div>';
      h += '</div>';
    }
    h += '</div>';
    // Total
    const totalUds = d.variantes.reduce((acc, v) => acc + (v.unidades_estimadas || 0), 0);
    h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px"><span style="font-size:10px;color:#64748b">💡 Este cálculo es <b>estimado para planificación</b> · el descuento real ocurre en Fabricación al envasar.</span><span style="font-size:11px;color:#0f766e;font-weight:700">Total: ' + totalUds.toLocaleString('es-CO') + ' uds</span></div>';
    window._COMP_MEE_CACHE[loteId] = h;
    box.innerHTML = h;
  } catch(e){
    box.innerHTML = '<span style="color:#dc2626">⚠ Error cargando composición: ' + escapeHtml(e.message || '') + '</span>';
  }
}

async function _cargarOpcionesEnvases(loteId, envActual){
  const sel = document.getElementById('env-ovr-' + loteId);
  if(!sel) return;
  // Cache hit · usar directo
  if(window._MEES_CACHE){
    _pintarOpcionesEnvase(sel, window._MEES_CACHE, envActual);
    return;
  }
  try{
    const r = await fetch('/api/programacion/mees-disponibles');
    if(!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    window._MEES_CACHE = d.items || [];
    _pintarOpcionesEnvase(sel, window._MEES_CACHE, envActual);
  }catch(e){
    sel.innerHTML = '<option value="">Error cargando: ' + e.message + '</option>';
  }
}
function _pintarOpcionesEnvase(sel, mees, envActual){
  let html = '<option value="">— Sin override (usa default del producto) —</option>';
  // Agrupar por categoría para optgroups
  const porCat = {};
  mees.forEach(m => {
    const cat = m.categoria || 'Sin categoría';
    porCat[cat] = porCat[cat] || [];
    porCat[cat].push(m);
  });
  Object.keys(porCat).sort().forEach(cat => {
    html += '<optgroup label="' + cat.replace(/"/g,'&quot;') + '">';
    porCat[cat].forEach(m => {
      const selAttr = m.codigo === envActual ? ' selected' : '';
      const label = (m.codigo + ' · ' + (m.descripcion || '')).slice(0, 90);
      html += '<option value="' + m.codigo.replace(/"/g,'&quot;') + '"' + selAttr + '>' + label + '</option>';
    });
    html += '</optgroup>';
  });
  sel.innerHTML = html;
}

// Sebastián 25-may-2026 PM · opción B · cambia el envase default del
// producto en sku_mee_config · futuros lotes nuevos lo usan automático.
async function envaseAplicarDefault(loteId){
  if(!confirm('¿Cambiar el envase DEFAULT del producto?\n\nEsto modifica sku_mee_config global · TODOS los lotes futuros NUEVOS de este producto usarán este envase a menos que les setees otro override individual.\n\n¿Continuar?')) return;
  try{
    const r = await fetch('/api/programacion/lote/' + loteId + '/envase-aplicar-default', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokPlan || '')},
      body: '{}',
    });
    const d = await r.json();
    if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    alert(d.mensaje || '✓ Default actualizado');
    if(typeof cargar === 'function') cargar();
  }catch(e){ alert('Error red: ' + e.message); }
}

// Sebastián 25-may-2026 PM · opción C · propaga el envase override
// a todos los lotes futuros del producto que aún no iniciaron · no
// toca el default global.
async function envasePropagarFuturos(loteId){
  if(!confirm('¿Propagar este envase a lotes futuros del producto?\n\nVa a setear el envase_codigo_override en TODOS los lotes futuros del mismo producto que aún no iniciaron · NO toca el default global del sku_mee_config.\n\n¿Continuar?')) return;
  try{
    const r = await fetch('/api/programacion/lote/' + loteId + '/envase-propagar-futuros', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokPlan || '')},
      body: '{}',
    });
    const d = await r.json();
    if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    alert(d.mensaje || '✓ Propagado');
    if(typeof cargar === 'function') cargar();
  }catch(e){ alert('Error red: ' + e.message); }
}

// Sebastián 25-may-2026 PM · guardar envase override del lote.
// Sobreescribe el envase default del producto · MEE Abastecimiento usa
// este código para calcular el consumo. Vacío = limpiar, volver al default.
async function guardarEnvaseOverride(loteId){
  const input = document.getElementById('env-ovr-' + loteId);
  const ok = document.getElementById('env-ovr-ok-' + loteId);
  if(!input) return;
  // Sebastián 25-may-2026 PM · ahora es SELECT · value ya es el código exacto
  const env = (input.value || '').trim().toUpperCase();
  try{
    const r = await fetch('/api/programacion/lote/' + loteId + '/envase-override', {
      method: 'PATCH',
      headers: {'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokPlan || '')},
      body: JSON.stringify({envase_codigo_override: env}),
    });
    const d = await r.json();
    if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    if(ok){
      ok.style.display = 'inline';
      setTimeout(() => { ok.style.display = 'none'; }, 1500);
    }
    // Refrescar lista para que el cache muestre el cambio
    if(typeof cargar === 'function') setTimeout(cargar, 200);
  }catch(e){ alert('Error red: ' + e.message); }
}

// Sebastián 25-may-2026 PM · guardar plan envasado editable de un
// cliente B2B en un lote. Envía PATCH con plan_envasado_uds + notas.
async function guardarPlanEnvasado(loteId, pblId){
  const inputUds = document.getElementById('env-uds-' + pblId);
  const inputNota = document.getElementById('env-nota-' + pblId);
  const btn = document.getElementById('env-save-' + pblId);
  const ok = document.getElementById('env-ok-' + pblId);
  if(!inputUds || !inputNota) return;
  const uds = parseInt(inputUds.value) || 0;
  const nota = inputNota.value.trim();
  if(btn){ btn.disabled = true; btn.textContent = 'Guardando...'; }
  try{
    const r = await fetch('/api/programacion/lote/' + loteId + '/plan-envasado/' + pblId, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokPlan || '')},
      body: JSON.stringify({plan_envasado_uds: uds, plan_envasado_notas: nota}),
    });
    const d = await r.json();
    if(!r.ok){
      alert('Error: ' + (d.error || r.status));
      if(btn){ btn.disabled = false; btn.textContent = '💾 Guardar'; }
      return;
    }
    if(ok){
      ok.style.display = 'inline';
      setTimeout(() => { ok.style.display = 'none'; }, 2000);
    }
    if(btn){ btn.disabled = false; btn.textContent = '💾 Guardar'; }
  }catch(e){
    alert('Error red: ' + e.message);
    if(btn){ btn.disabled = false; btn.textContent = '💾 Guardar'; }
  }
}

async function abrirLoteModal(id, producto, fecha, kg){
  window._LOTE_MODAL_ACTUAL = {id: id, producto: producto, fecha: fecha, kg: kg};
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
  // Sebastián 15-may-2026: el diagnóstico TARDE/TEMPRANO solo tiene
  // sentido para el PRIMER lote futuro de cada producto. Los lotes
  // siguientes son la serie planificada (cada Xd) · compararlos contra
  // "hoy + cobertura" siempre los marca TARDE falsamente.
  const _lotesProd = (PLAN_DATA.agendadas || [])
    .filter(a => a.producto === producto)
    .map(a => (a.fecha_programada || '').slice(0, 10))
    .filter(Boolean).sort();
  const _esPrimerLote = _lotesProd.length === 0 || fecha <= _lotesProd[0];
  if (!_esPrimerLote){
    diagFecha = 'serie';
    diagFechaTxt = '📋 Lote de la serie planificada · el diagnóstico de timing (TARDE/a tiempo) aplica solo al PRIMER lote del producto, no a los siguientes';
  } else if (velKgDia > 0.0001){
    // Sebastián 30-may-2026 · FIX lógica óptimo · ANTES usaba info.dias_cobertura,
    // que = stock_kg_total / velocidad e incluye pipeline_FIJO (¡la producción ya
    // programada, incluido ESTE lote!). Eso era circular: el lote se contaba a sí
    // mismo como stock → salía "TEMPRANO" por cientos de días. AHORA el óptimo se
    // mide contra el stock FÍSICO real (góndola + tránsito pipeline), SIN la
    // producción programada. Buffer 25d = cob_alerta del backend (igual que la
    // próxima sugerida · antes eran 20 vs 25, inconsistentes).
    const stockFisicoKg = (info.stock_kg_gondola || 0) + (info.pipeline_kg || 0);
    const diasCobFisica = Math.round(stockFisicoKg / velKgDia);
    const hoy = new Date();
    const fAgot = new Date(hoy); fAgot.setDate(fAgot.getDate() + diasCobFisica);
    const fOpt = new Date(fAgot); fOpt.setDate(fOpt.getDate() - 25);
    const fProg = new Date(fecha + 'T12:00:00');
    const diffDias = Math.round((fProg - fOpt) / 86400000);
    const _cobTxt = stockFisicoKg.toFixed(1) + 'kg físico ≈ ' + diasCobFisica + 'd (sin contar este lote)';
    if (Math.abs(diffDias) <= 7){
      diagFecha = 'ok'; diagFechaTxt = '✅ A tiempo · dentro de ±7d del óptimo · produce ~25d antes de agotar el stock físico · ' + _cobTxt;
    } else if (diffDias > 0){
      diagFecha = 'tarde'; diagFechaTxt = '⚠ TARDE · ' + diffDias + ' días después del óptimo · el stock físico se agota antes · ' + _cobTxt;
    } else {
      diagFecha = 'temprano'; diagFechaTxt = '📌 TEMPRANO · ' + Math.abs(diffDias) + ' días antes del óptimo (no urgente) · ' + _cobTxt;
    }
  }

  // Próxima producción sugerida según los kg programados ahora
  // kg programados / velKgDia = días que va a durar el lote
  // FIX 23-may-2026 Sebastián · buffer 25d (no 20) · "las sugerencias deben
  // ser 25 días antes de que se acabe" · sincronizado con cob_alerta del
  // backend _calcular_animus_dtc · lote 90d → próxima a los 65d, no 70d.
  let proximaSugerida = null;
  let proximaTxt = '';
  if (velKgDia > 0.001 && kg > 0){
    // FIX 30-may-2026 · Sebastián · "el lote no es todo Animus, va a otro cliente".
    // La duración la determina SOLO la porción que consume Animus al ritmo DTC ·
    // los kg comprometidos a B2B (Fernando Meza, etc.) salen del lote y no cubren
    // demanda diaria · usar kg_residual_dtc de la composición, no el lote completo.
    let kgAnimus = kg;
    try {
      const _c = _parsearComposicionLote((PLAN_DATA.agendadas || []).find(a => a.id === id), kg);
      if (_c && _c.entradas.length > 0 && _c.kg_residual_dtc != null && _c.kg_residual_dtc > 0.01) {
        kgAnimus = _c.kg_residual_dtc;
      }
    } catch(e){}
    const kgB2B = Math.max(0, kg - kgAnimus);
    const diasDura = kgAnimus / velKgDia;
    const diasHastaProx = Math.max(Math.round(diasDura) - 25, 1);  // 25d antes de agotar · mín 1
    const fProx = new Date(fecha + 'T12:00:00');
    fProx.setDate(fProx.getDate() + diasHastaProx);
    proximaSugerida = fechaLocalStr(fProx);
    const _kgTxt = kgB2B > 0.01
      ? kg + 'kg (' + kgAnimus.toFixed(1) + ' Animus + ' + kgB2B.toFixed(1) + ' B2B)'
      : kg + 'kg';
    proximaTxt = '✓ Lote programado para <strong>' + fecha + '</strong> · ' + _kgTxt + ' · cubre Animus ~' + Math.round(diasDura) + ' días al ritmo actual · próxima producción sugerida: <strong>' + proximaSugerida + '</strong>';
  }

  let html = '';

  // Sebastián 25-may-2026 PM · selector envase override del lote.
  // Dropdown que carga de /api/programacion/mees-disponibles (maestro_mee)
  // · evita typos · match perfecto con la BD.
  try {
    const _loteFull0 = (PLAN_DATA.agendadas || []).find(a => a.id === id);
    const envActual = (_loteFull0 && _loteFull0.envase_codigo_override) || '';
    html += '<div style="background:#ecfeff;border:1px solid #67e8f9;border-radius:8px;padding:10px 14px;margin-bottom:12px">';
    html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">';
    html += '<span style="font-size:11px;font-weight:800;color:#0e7490;text-transform:uppercase;letter-spacing:.5px">📦 Envase del lote</span>';
    html += '<select id="env-ovr-' + id + '" data-actual="' + escapeHtml(envActual) + '" style="flex:1;min-width:240px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;font-family:inherit;background:#fff">';
    html += '<option value="">— Cargando envases —</option>';
    html += '</select>';
    html += '<button onclick="guardarEnvaseOverride(' + id + ')" style="padding:6px 14px;font-size:11px;background:#0891b2;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:700">💾 Guardar</button>';
    html += '<span id="env-ovr-ok-' + id + '" style="color:#15803d;font-size:11px;display:none">✓</span>';
    html += '</div>';
    html += '<div style="font-size:11px;color:#0e7490;margin-top:6px">' +
       (envActual ? '✓ Override <strong>' + escapeHtml(envActual) + '</strong> · MEE calcula con este envase' :
                     '⚙ Sin override · MEE usa el envase default del producto · elegí uno de la lista para forzar otro') + '</div>';
    // Cargar opciones (cache global · una sola llamada)
    setTimeout(() => { _cargarOpcionesEnvases(id, envActual); }, 50);
    // Sebastián 25-may-2026 PM · botones B (default global) y C (propagar futuros)
    // Solo se muestran si hay override seteado (sino no tiene sentido propagar nada)
    if (envActual){
      html += '<details style="margin-top:10px;border-top:1px dashed #67e8f9;padding-top:8px">';
      html += '<summary style="cursor:pointer;font-size:11px;color:#0e7490;font-weight:700">▸ Propagación opcional (avanzado)</summary>';
      html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">';
      html += '<button onclick="envaseAplicarDefault(' + id + ')" style="padding:6px 12px;font-size:11px;background:#f59e0b;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:700" title="Cambia el envase default del producto en sku_mee_config · futuros lotes nuevos lo usan automático">⚓ Aplicar como default del producto</button>';
      html += '<button onclick="envasePropagarFuturos(' + id + ')" style="padding:6px 12px;font-size:11px;background:#6366f1;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:700" title="Setea este envase como override en TODOS los lotes futuros del producto que aún no iniciaron · no toca el default global">↪ Propagar a lotes futuros</button>';
      html += '</div>';
      html += '<div style="font-size:10px;color:#64748b;margin-top:6px;line-height:1.4">';
      html += '<strong>⚓ Default</strong>: cambia sku_mee_config global · permanente hasta que lo cambies de nuevo<br>';
      html += '<strong>↪ Propagar</strong>: sobreescribe override en cada lote futuro · no toca config global · útil cuando es cambio temporal';
      html += '</div></details>';
    }
    html += '</div>';
  } catch(_e_env){ /* sin lote en PLAN_DATA · no mostrar */ }

  // Sebastián 27-may-2026 PM · "el calendario debe colocar la realidad
  // del envase, que lo tenga cada producción". Bloque composición de
  // variantes auto-derivado desde Shopify · async post-render para no
  // bloquear modal · placeholder + fetch + replace.
  html += '<div id="comp-mee-' + id + '" style="background:#f0fdfa;border:1px solid #5eead4;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px;color:#0f766e">'
    + '<span style="font-weight:700">📐 Composición de envases:</span> <span style="opacity:.7">cargando...</span>'
    + '</div>';
  setTimeout(function(){ _cargarComposicionMee(id); }, 50);

  // Sebastián 25-may-2026 PM · Desglose B2B vs DTC del lote + plan
  // envasado editable. "como ya estas primeras producciones estan
  // deberias colocar que yo mismo lo escriba, y tenga algo como
  // observaciones". Cada cliente del lote (DTC + B2B) tiene su fila
  // con kg asignados, envase, unidades calculadas, plan editable y
  // observaciones libres.
  try {
    const _loteFull = (PLAN_DATA.agendadas || []).find(a => a.id === id);
    const _desg = (_loteFull && _loteFull.desglose_b2b) || [];
    if (_desg.length > 0 || (_loteFull && _loteFull.kg_b2b_total > 0)){
      const kgB2B = (_loteFull && _loteFull.kg_b2b_total) || 0;
      const kgDTC = (_loteFull && _loteFull.kg_dtc) || 0;
      const inconsist = !!(_loteFull && _loteFull.split_inconsistente);
      let dHtml = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:12px">';
      dHtml += '<div style="font-size:12px;font-weight:800;color:#0f766e;margin-bottom:8px">📦 Plan de envasado · ' + kg + 'kg total</div>';
      if (inconsist){
        dHtml += '<div style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:5px;font-size:11px;margin-bottom:8px">⚠ <strong>Datos inconsistentes</strong> · suma B2B (' + kgB2B + 'kg) > total lote (' + kg + 'kg).</div>';
      }
      dHtml += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
      dHtml += '<thead><tr style="background:#fff;color:#475569;font-size:10px;text-transform:uppercase">'
        + '<th style="text-align:left;padding:6px 8px">Cliente</th>'
        + '<th style="padding:6px 8px">kg</th>'
        + '<th style="padding:6px 8px">Envase</th>'
        + '<th style="padding:6px 8px">Uds calc</th>'
        + '<th style="padding:6px 8px;background:#fef3c7">Uds a envasar ✏</th>'
        + '<th style="padding:6px 8px;background:#fef3c7">Observaciones ✏</th>'
        + '</tr></thead><tbody>';
      // Fila DTC (no editable, no tiene pbl_id)
      if (kgDTC > 0.05){
        const udsDtcCalc = '—';
        dHtml += '<tr style="border-top:1px solid #e2e8f0;background:#eff6ff">'
          + '<td style="padding:6px 8px;font-weight:700;color:#1e40af">🛍️ Animus DTC</td>'
          + '<td style="padding:6px 8px;text-align:center;font-weight:700">' + kgDTC + ' kg</td>'
          + '<td style="padding:6px 8px;text-align:center;color:#64748b">default</td>'
          + '<td style="padding:6px 8px;text-align:center;color:#64748b">—</td>'
          + '<td style="padding:6px 8px;text-align:center;color:#94a3b8" colspan="2"><em>DTC se calcula automático · no editable</em></td>'
          + '</tr>';
      }
      // Filas B2B (editables)
      _desg.forEach((d, idx) => {
        const cli = (d.cliente || 'B2B');
        const cliEsc = cli.replace(/'/g, "&#39;");
        const envase = d.envase || '—';
        const udsCalc = d.unidades_calculadas || 0;
        // FIX 30-may-2026 · Sebastián (caso Kelly BHA): el campo arrancaba en 0
        // cuando no se había llenado → una orden quedaba en 0 y NO se envasaba.
        // Ahora pre-llena con las uds calculadas (el operario solo confirma y
        // guarda). Si de verdad quieren 0, lo escriben.
        const planUds = (d.plan_envasado_uds && Number(d.plan_envasado_uds) > 0)
                        ? d.plan_envasado_uds : udsCalc;
        const planNotas = (d.plan_envasado_notas || '').replace(/"/g, '&quot;');
        const pblId = d.pbl_id;
        const inputId = 'env-uds-' + pblId;
        const notaId = 'env-nota-' + pblId;
        const guardId = 'env-save-' + pblId;
        const okId = 'env-ok-' + pblId;
        dHtml += '<tr style="border-top:1px solid #e2e8f0;background:#fce7f3">'
          + '<td style="padding:6px 8px;font-weight:700;color:#9d174d" title="pedido B2B #' + (d.pedido_id||'') + '">📦 ' + escapeHtml(cli) + '</td>'
          + '<td style="padding:6px 8px;text-align:center;font-weight:700">' + d.kg + ' kg</td>'
          + '<td style="padding:6px 8px;text-align:center;font-size:10px">' + escapeHtml(envase) + '</td>'
          + '<td style="padding:6px 8px;text-align:center;color:#64748b" title="' + d.kg + 'kg × 1000 ÷ ' + (d.ml||0) + 'ml">' + udsCalc + ' uds</td>'
          + '<td style="padding:6px 8px;text-align:center"><input id="' + inputId + '" type="number" min="0" max="10000000" value="' + planUds + '" placeholder="' + udsCalc + '" style="width:90px;padding:4px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;text-align:center"></td>'
          + '<td style="padding:6px 8px"><input id="' + notaId + '" type="text" maxlength="500" value="' + planNotas + '" placeholder="etiqueta, color, arte..." style="width:100%;padding:4px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px"></td>'
          + '</tr>';
        dHtml += '<tr style="background:#fce7f3"><td colspan="6" style="padding:0 8px 8px;text-align:right">'
          + '<span id="' + okId + '" style="color:#15803d;font-size:11px;margin-right:8px;display:none">✓ guardado</span>'
          + '<button id="' + guardId + '" onclick="guardarPlanEnvasado(' + id + ',' + pblId + ')" style="padding:4px 12px;font-size:11px;background:#0f766e;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:700">💾 Guardar</button>'
          + '</td></tr>';
      });
      dHtml += '</tbody></table></div>';
      html += dHtml;
    } else {
      // Lote sin atribución B2B explícita · asumido todo DTC
      html += '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:11px;color:#64748b">📦 Lote sin desglose B2B · asumido <strong>' + kg + 'kg DTC</strong></div>';
    }
  } catch(_e_desg){ /* sin lote en PLAN_DATA · no mostrar */ }

  // Sección 1: Datos de venta y stock
  html += '<div class="metric-grid">';
  html += '<div class="metric-card"><div class="metric-lbl">Volumen envase</div><div class="metric-val">' + ml + ' ml</div></div>';
  // Sebastián 15-may-2026: "kilogramos a producir" editable desde el popup
  html += '<div class="metric-card"><div class="metric-lbl">Kg a producir</div>' +
    '<div style="display:flex;gap:4px;align-items:center;margin-top:2px">' +
    '<input id="edit-kg-lote" type="number" min="1" max="1000" step="1" value="' + kg + '" ' +
    'oninput="var u=document.getElementById(&quot;edit-kg-uds&quot;);if(u)u.textContent=Math.round((parseFloat(this.value)||0)*1000/' + ml + ')+&quot; uds aprox&quot;" ' +
    'style="width:64px;font-size:16px;font-weight:800;padding:3px 5px;border:1px solid #cbd5e1;border-radius:5px">' +
    '<span style="font-size:12px;color:#64748b">kg</span>' +
    '<button onclick="guardarKgLote(' + id + ')" style="padding:5px 9px;font-size:11px;margin:0">💾 Guardar</button>' +
    '</div>' +
    '<div class="metric-sub" id="edit-kg-uds">' + Math.round(kg * 1000 / ml) + ' uds aprox</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Vende/día</div><div class="metric-val">' + velUds.toFixed(1) + '</div><div class="metric-sub">' + velKgDia.toFixed(2) + ' kg/día</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Vende/mes</div><div class="metric-val">' + velMes + '</div><div class="metric-sub">' + (velKgDia * 30).toFixed(1) + ' kg/mes</div></div>';
  // FIX 30-may-2026 · "237 uds / 72.1 kg" era incoherente · 237 uds × 30ml = 7.1kg,
  // no 72.1 (eso era góndola + lote programado). Mostrar el FÍSICO de góndola, que
  // sí cuadra con las uds. La cobertura (que sí cuenta lo programado) va en su tarjeta.
  const _stockKgFisico = (info.stock_kg_gondola != null) ? info.stock_kg_gondola : stockKg;
  html += '<div class="metric-card"><div class="metric-lbl">Stock actual</div><div class="metric-val">' + stockUds + ' uds</div><div class="metric-sub">' + _stockKgFisico.toFixed(1) + ' kg físico</div></div>';
  html += '<div class="metric-card"><div class="metric-lbl">Cobertura</div><div class="metric-val">' + (diasCob != null ? diasCob + 'd' : '—') + '</div><div class="metric-sub">' + (info.urgencia || '') + '</div></div>';
  html += '</div>';

  // Sección 1.5: Composición del lote · Sebastián 19-may-2026
  // "extensión de marca · la misma producción sirve para varios clientes".
  // Parsea observaciones para extraer aportes B2B y muestra el desglose.
  try {
    const loteData = (PLAN_DATA.agendadas || []).find(a => a.id === id);
    const composicion = _parsearComposicionLote(loteData, kg);
    if (composicion && composicion.entradas.length > 0){
      html += '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;margin:8px 0">';
      html += '<div style="font-size:12px;font-weight:700;color:#0f766e;margin-bottom:6px">👥 Composición del lote · este lote atiende a:</div>';
      html += '<table style="width:100%;font-size:11px;border-collapse:collapse">';
      composicion.entradas.forEach(e => {
        const pct = composicion.kg_total > 0 ? Math.round((e.kg / composicion.kg_total) * 100) : 0;
        html += '<tr style="border-top:1px solid #e2e8f0">';
        html += '<td style="padding:4px 8px"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:' + e.color + ';margin-right:6px;vertical-align:middle"></span>' + escapeHtml(e.cliente) + '</td>';
        html += '<td style="padding:4px 8px;text-align:right;font-weight:600">' + e.kg.toFixed(2) + ' kg</td>';
        html += '<td style="padding:4px 8px;text-align:right;color:#64748b">' + pct + '%</td>';
        html += '</tr>';
      });
      html += '</table>';
      if (composicion.kg_residual_dtc > 0.01){
        html += '<div style="font-size:10px;color:#64748b;margin-top:4px;font-style:italic">DTC (Animus / inventario) = total − suma B2B</div>';
      }
      html += '</div>';
    }
  } catch(e){ console.warn('composicion lote falló:', e); }

  // Sección 2: Diagnóstico fecha programada
  if (diagFechaTxt){
    const cls = (diagFecha === 'ok' || diagFecha === 'serie') ? 'ok' : (diagFecha === 'tarde' ? 'danger' : 'info');
    html += '<div class="banner-inline ' + cls + '"><strong>Fecha programada: ' + fecha + '</strong><br>' + diagFechaTxt + '</div>';
  }

  // Sección 3: Próxima producción sugerida
  if (proximaTxt){
    html += '<div class="banner-inline ok">🔁 ' + proximaTxt + '</div>';
  }

  // Sebastián 30-may-2026 · "¿la próxima ya está programada?" · cruza la fecha
  // sugerida contra las producciones YA agendadas de ESTE producto y deja
  // programarla / ajustarla desde el mismo modal.
  if (proximaSugerida){
    const _toD = s => new Date((s || '').slice(0,10) + 'T12:00:00');
    let prox = null;
    (PLAN_DATA.agendadas || []).forEach(a => {
      if (a.id === id) return;
      if ((a.producto || '') !== producto) return;
      const f = (a.fecha_programada || '').slice(0,10);
      if (!f || f <= fecha) return;  // sólo lotes posteriores a éste
      const est = (a.estado || '').toLowerCase();
      if (est === 'cancelado' || est === 'completado') return;
      if (!prox || f < (prox.fecha_programada || '').slice(0,10)) prox = a;
    });
    if (prox){
      const pf = (prox.fecha_programada || '').slice(0,10);
      const dd = Math.round((_toD(pf) - _toD(proximaSugerida)) / 86400000);  // + = después
      let txt, col;
      if (Math.abs(dd) <= 7){ txt = '✅ alineada con la sugerida'; col = '#15803d'; }
      else if (dd < 0){ txt = '📌 ' + Math.abs(dd) + ' días ANTES de la sugerida'; col = '#7c3aed'; }
      else { txt = '⚠ ' + dd + ' días DESPUÉS de la sugerida (stock se agota antes)'; col = '#b45309'; }
      // Sebastián 30-may-2026 · botón "Aplicar recomendación": mueve la próxima
      // a la fecha sugerida automáticamente (adelanta/atrasa según corresponda),
      // en vez de tener que abrir y mover a mano. Solo si NO está alineada (±7d).
      let accionBtn = '';
      if (Math.abs(dd) > 7){
        const verbo = dd > 0 ? 'Adelantar' : 'Atrasar';
        accionBtn = '<button onclick="aplicarRecomendacionProxima(' + prox.id + ',&quot;' + proximaSugerida + '&quot;,' + id + ',&quot;' + escapeHtml(producto) + '&quot;,&quot;' + fecha + '&quot;,' + kg + ')" '
          + 'style="margin-left:8px;background:#16a34a;color:#fff;border:none;padding:3px 11px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer" '
          + 'title="Mueve la próxima producción a la fecha sugerida">✅ ' + verbo + ' a ' + proximaSugerida + '</button>';
      }
      html += '<div class="banner-inline" style="border-color:' + col + ';color:' + col + '">'
            + '✓ La próxima YA está programada el <strong>' + pf + '</strong> · ' + txt + '. '
            + accionBtn
            + '<button onclick="abrirLoteModal(' + prox.id + ',&quot;' + escapeHtml(producto) + '&quot;,&quot;' + pf + '&quot;,' + (prox.kg || 0) + ')" '
            + 'style="margin-left:6px;background:#fff;border:1px solid ' + col + ';color:' + col + ';padding:2px 9px;border-radius:5px;font-size:11px;cursor:pointer">abrir</button>'
            + '</div>';
    } else {
      html += '<div class="banner-inline" style="border-color:#b45309;color:#b45309">'
            + '⚠ No hay una próxima producción programada para este producto. '
            + '<button onclick="programarProxima(&quot;' + escapeHtml(producto) + '&quot;,&quot;' + proximaSugerida + '&quot;,' + kg + ')" '
            + 'style="margin-left:6px;background:#16a34a;color:#fff;border:none;padding:3px 11px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">📅 Programar el ' + proximaSugerida + ' (' + kg + 'kg)</button>'
            + '</div>';
    }
  }

  // Sección 4: Acciones
  html += _renderAccionesLote(id, producto, fecha);
  document.getElementById('lote-body').innerHTML = html;
}

// Sebastián 15-may-2026: editar kg a producir desde el popup del lote
async function guardarKgLote(id){
  const inp = document.getElementById('edit-kg-lote');
  if (!inp) return;
  const nuevo = parseFloat(inp.value);
  if (isNaN(nuevo) || nuevo <= 0 || nuevo > 1000){
    alert('Kg inválido · debe estar entre 1 y 1000');
    return;
  }
  try {
    const r = await fetch('/api/plan/proximas/' + id + '/cantidad', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials:'same-origin',
      body: JSON.stringify({cantidad_kg: nuevo}),
    });
    const d = await r.json();
    if (!r.ok){ alert('❌ ' + (d.error || ('Error ' + r.status))); return; }
    alert('✅ Kg actualizado: ' + d.kg_antes + ' → ' + d.kg_nuevo + ' kg');
    cerrarLoteModal();
    cargar();  // recargar calendario con el cambio
  } catch(e){ alert('Error de red: ' + e.message); }
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
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({motivo_pausa: motivo.trim()}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  } else if (accion === 'C'){
    if (!confirm('¿Cancelar lote?')) return;
    const r = await fetch('/api/plan/proximas/' + id, {
      method:'DELETE',
      headers:{'X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
    });
    if (!r.ok){ const d = await r.json(); alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  } else if (accion === 'R'){
    const r = await fetch('/api/plan/proximas/' + id + '/reactivar', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    cargar();
  }
}

async function programarProxima(producto, fecha, kg){
  // Sebastián 30-may-2026 · programar la próxima producción sugerida desde el
  // modal del lote · crea produccion_programada (origen eos_plan) en esa fecha.
  const f = prompt('Programar próxima producción de "' + producto + '"\\n\\nFecha (YYYY-MM-DD):', fecha);
  if (!f) return;
  let kgN = parseFloat(prompt('Kg a producir:', kg) || kg);
  if (!(kgN > 0)){ alert('Kg inválido'); return; }
  try {
    const r = await fetch('/api/plan/programar-produccion', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({producto_nombre: producto, fecha_programada: f.trim(), cantidad_kg: kgN}),
    });
    const d = await r.json();
    if (!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    cerrarLoteModal();
    cargar();
  } catch(e){ alert('Error de red: ' + e.message); }
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

// Sebastián 30-may-2026 · "Aplicar recomendación": mueve la próxima producción
// a la fecha sugerida (adelanta/atrasa) con un clic, en vez de abrir y mover a
// mano. Reprograma (queda Fijo) y refresca el calendario + este modal.
async function aplicarRecomendacionProxima(proxId, fechaSugerida, curId, producto, curFecha, curKg){
  if(!confirm('¿Mover la próxima producción de "' + producto + '" a la fecha recomendada ' + fechaSugerida + '?\\n\\nSe reprograma el lote (queda como Fijo).')) return;
  await reprogramarLote(proxId, fechaSugerida, 'aplicar_recomendacion');
  try { await cargar(); } catch(_){}            // asegurar PLAN_DATA fresco
  try { abrirLoteModal(curId, producto, curFecha, curKg); } catch(_){}  // refrescar este modal
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

// Sebastián 14-may-2026: "solo sale el gel hidratante" · diag in-situ
async function diagCalendar(){
  try {
    const r = await fetch('/api/plan/health-canonicos');
    if (!r.ok){ alert('Error diag: ' + r.status); return; }
    const d = await r.json();
    const lr = d.listado_calendar_replica || {};
    const prods = lr.productos || [];
    const lista = prods.map(p => '  - ' + p.producto + ' · ' + p.n_lotes + ' lotes').join('\\n');
    const msg = '🔍 DIAGNÓSTICO BACKEND\\n\\n' +
      '· Última mig aplicada: ' + d.ultima_mig_aplicada + '\\n' +
      '· Mig 136 aplicada: ' + d.mig_136_aplicada + ' · inserts visibles: ' + d.mig_136_inserts_visible + '\\n' +
      '· Mig 137 aplicada: ' + d.mig_137_aplicada + ' · inserts visibles: ' + d.mig_137_inserts_visible + ' (esperado 96)\\n' +
      '· Total eos_canonico activos: ' + d.total_eos_canonico_activos + '\\n\\n' +
      'LO QUE DEVUELVE LA QUERY DEL CALENDARIO:\\n' +
      '  total lotes: ' + lr.total_lotes + '\\n' +
      '  productos únicos: ' + lr.productos_unicos + '\\n\\n' +
      'Productos detectados:\\n' + (lista || '  (ninguno)');
    alert(msg);
    console.log('DIAG full:', d);
  } catch(e){ alert('Error: ' + e.message); }
}

// Sebastián 15-may-2026: "usamos las sugerencias de la IA con los
// parámetros que establecimos y volvemos eso canónico y los ponemos
// allí, yo muevo lo que sea necesario". Botón ÚNICO · 1 sola acción:
// genera plan IA + lo persiste como eos_plan (canónico) + recarga.
async function generarPlanIA(){
  if (!confirm('¿Generar el plan de producción con IA?\n\n' +
               '· La IA calcula qué producir, cuándo y cuánto\n' +
               '  (horizonte ' + HORIZONTE + ' días · L-V · sin festivos)\n' +
               '· El plan queda FIJO en el calendario\n' +
               '· Después movés a mano los lotes que quieras\n\n' +
               '⚠ Esto REEMPLAZA el plan actual (incluido lo que hayas\n' +
               'movido a mano). ¿Continuar?')) return;

  // Hay 2 botones con esta acción (barra superior + barra del grid).
  const btns = [document.getElementById('btn-generar-ia'),
                document.getElementById('btn-generar-ia-2')].filter(Boolean);
  btns.forEach(b => { b.disabled = true; b.textContent = '⏳ Calculando plan…'; });
  document.getElementById('ia-comentario').innerHTML =
    '<div class="banner info">⏳ Paso 1/2 · La IA analiza ventas, stock y reglas… (~30-60s, modelo Sonnet 4.6)</div>';

  try {
    // PASO 1 · generar sugerencias con IA
    const rIA = await fetch('/api/plan/autoplan-ia', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({cliente:'ANIMUS_DTC', horizonte_dias: HORIZONTE, forzar_recalcular: true}),
    });
    let dIA = null;
    try { dIA = await rIA.json(); } catch(e){}
    if (!rIA.ok || !dIA){
      const em = (dIA && (dIA.error || dIA.message)) || ('HTTP ' + rIA.status);
      document.getElementById('ia-comentario').innerHTML =
        '<div class="banner danger">❌ Error generando plan IA: ' + escapeHtml(em) + '</div>';
      return;
    }
    const sugerencias = dIA.sugerencias || [];
    if (!sugerencias.length){
      document.getElementById('ia-comentario').innerHTML =
        '<div class="banner warn">🤖 La IA no devolvió sugerencias.<br>' +
        escapeHtml(dIA.comentario_general || '') + '</div>';
      return;
    }

    // PASO 2 · persistir como canónico (eos_plan) en el calendario
    btns.forEach(b => b.textContent = '⏳ Guardando plan…');
    document.getElementById('ia-comentario').innerHTML =
      '<div class="banner info">⏳ Paso 2/2 · Guardando ' + sugerencias.length +
      ' lotes en el calendario…</div>';
    const rBulk = await fetch('/api/plan/aplicar-ia-bulk', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({
        sugerencias: sugerencias.map(s => ({
          producto: s.producto, kg: s.kg, fecha: s.fecha,
        })),
        cancelar_actual: true,
      }),
    });
    const dBulk = await rBulk.json();
    if (!rBulk.ok){
      document.getElementById('ia-comentario').innerHTML =
        '<div class="banner danger">❌ Error guardando el plan: ' +
        escapeHtml(dBulk.error || rBulk.status) + '</div>';
      return;
    }

    // PASO 3 · recargar el calendario para mostrar el plan fijo
    let resumen = '<div class="banner success">✅ <strong>Plan IA generado y guardado</strong><br>' +
      '· ' + dBulk.n_lotes_creados + ' lotes en el calendario<br>' +
      '· ' + dBulk.n_lotes_cancelados + ' lotes del plan anterior reemplazados<br>';
    if (dBulk.lotes_movidos) resumen += '· ' + dBulk.lotes_movidos + ' movidos al sig día hábil (festivo/finde)<br>';
    if (dBulk.sin_formula && dBulk.sin_formula.length)
      resumen += '⚠ Sin fórmula (omitidos): ' + escapeHtml(dBulk.sin_formula.join(', ')) + '<br>';
    resumen += '<span style="font-size:11px">' + escapeHtml(dIA.comentario_general || '') +
      '</span><br><strong>Ahora podés arrastrar los lotes para moverlos.</strong></div>';
    document.getElementById('ia-comentario').innerHTML = resumen;

    await cargar();  // recarga el calendar · muestra el plan persistido
  } catch(e){
    document.getElementById('ia-comentario').innerHTML =
      '<div class="banner danger">❌ Error de red: ' + escapeHtml(e.message) + '</div>';
  } finally {
    btns.forEach(b => { b.disabled = false; b.textContent = '🤖 Generar plan IA'; });
  }
}

async function autoplanIA(){
  const btn = document.getElementById('btn-ia');
  btn.disabled = true;
  btn.textContent = '🤖 Consultando IA...';
  document.getElementById('ia-comentario').innerHTML = '<div class="banner info">⏳ La IA está analizando ventas, stock, MPs y feedback previo… esto toma ~20-45 segundos (modelo Sonnet 4.6)</div>';
  try {
    const r = await fetch('/api/plan/autoplan-ia', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({cliente:'ANIMUS_DTC', horizonte_dias: HORIZONTE, forzar_recalcular: true}),
    });
    let d = null; let txtErr = '';
    try { d = await r.json(); } catch(e){ txtErr = await r.text(); }

    if (!r.ok){
      const errMsg = (d && (d.error || d.message)) || txtErr || ('HTTP ' + r.status);
      const hint = (errMsg && errMsg.includes('ANTHROPIC_API_KEY')) ?
        '<br>👉 Configurá ANTHROPIC_API_KEY en Render → Environment y reiniciá el servicio.' :
        (r.status === 403 ? '<br>👉 Probable: MFA no activado · andá a /seguridad' : '');
      document.getElementById('ia-comentario').innerHTML =
        '<div class="banner danger">❌ <strong>Error ' + r.status + ':</strong> ' +
        escapeHtml(errMsg) + hint + '</div>';
      return;
    }

    const sugerencias = d.sugerencias || [];
    const n = sugerencias.length;

    if (n === 0){
      // IA respondió OK pero con CERO sugerencias · explicar y mostrar raw
      const rawIA = d.raw_text_ia || '';
      const comentario = d.comentario_general || '';
      let html = '<div class="banner warn"><strong>🤖 IA (' + escapeHtml(d.modelo_ia || '') + ') no devolvió sugerencias</strong>';
      if (comentario){
        html += '<br><br>💬 <strong>Comentario IA:</strong><br>' + escapeHtml(comentario);
      }
      if (rawIA){
        html += '<br><br><details><summary style="cursor:pointer;font-weight:700">🔍 Ver respuesta cruda de la IA (diagnóstico)</summary>';
        html += '<pre style="background:#fff;padding:10px;border-radius:6px;font-size:10px;overflow:auto;max-height:300px;white-space:pre-wrap">' + escapeHtml(rawIA) + '</pre>';
        html += '</details>';
      }
      html += '<br>Tokens: ' + (d.tokens_usados || 0) +
              ' · Historial aprendido: ' + (d.n_historial_aprendido || 0);
      html += '<br><br>💡 Acciones posibles:<br>' +
              '• Probá horizonte mayor (60/90/120 días)<br>' +
              '• Desmarcá "Solo sugerencias IA" para ver el plan determinista<br>' +
              '• Si la IA se equivocó, mandá la respuesta cruda al admin</div>';
      document.getElementById('ia-comentario').innerHTML = html;
      if (PLAN_DATA && PLAN_DATA.plan){
        PLAN_DATA.plan.plan_items = [];
        PLAN_DATA.plan.total_producciones = 0;
        document.getElementById('btn-aplicar').disabled = true;
      }
      render();
      return;
    }

    // IA devolvió sugerencias · inyectarlas
    // Sebastián 14-may-2026: ahora la IA devuelve frecuencia_dias en
    // cada sugerencia (plan canónico) · la guardamos para usar al aplicar
    PLAN_DATA.plan.plan_items = sugerencias.map((s, i) => ({
      producto: s.producto, fecha: s.fecha, kg: s.kg,
      frecuencia_dias: s.frecuencia_dias || null,  // NUEVO
      motivo: s.motivo, cob_dias_actual: s.cobertura_post_dias,
      razonamiento_ia: s.razonamiento, confianza: s.confianza,
      decision_id: (d.ids_decisiones || [])[i],
      from_ia: true,
    }));
    PLAN_DATA.plan.total_producciones = n;
    document.getElementById('btn-aplicar').disabled = false;
    // Sebastián 14-may-2026: mostrar botón "Aplicar plan IA anual"
    // cuando hay sugerencias IA cargadas
    document.getElementById('btn-ia-anual').style.display = 'inline-block';
    const cacheTag = d.cache_hit ? ' <span style="background:#dbeafe;color:#1e40af;padding:1px 5px;border-radius:3px;font-size:10px">cache 24h</span>' : '';
    // Confianza promedio para mostrar
    const confs = sugerencias.map(s => s.confianza || 0).filter(c => c > 0);
    const confProm = confs.length ? Math.round(100 * confs.reduce((a,b)=>a+b,0) / confs.length) : 0;
    document.getElementById('ia-comentario').innerHTML =
      '<div class="banner success">🤖 <strong>IA (' + escapeHtml(d.modelo_ia || '') + ') · ' + n + ' sugerencias · confianza promedio ' + confProm + '%</strong>' + cacheTag + '<br>' +
      escapeHtml(d.comentario_general || '') +
      '<br><span style="font-size:11px;color:#475569">Aprendí de ' + (d.n_historial_aprendido || 0) + ' decisiones previas · ' + (d.tokens_usados || 0) + ' tokens</span></div>';
    render();
  } catch(e){
    document.getElementById('ia-comentario').innerHTML = '<div class="banner danger">❌ Error de red: ' + escapeHtml(e.message) + '</div>';
  } finally {
    btn.disabled = false;
    btn.textContent = '🤖 Autoplan con IA';
  }
}

// Sebastián 14-may-2026: "el plan de la IA es mejor, cómo hago para
// que quede y replique por un año exactamente lo que pensamos"
async function aplicarIAanual(){
  if (!PLAN_DATA || !PLAN_DATA.plan || !PLAN_DATA.plan.plan_items){
    alert('No hay sugerencias IA · primero apretá "🤖 Autoplan con IA"');
    return;
  }
  const sugIA = PLAN_DATA.plan.plan_items.filter(it => it.from_ia);
  if (!sugIA.length){
    alert('No hay sugerencias IA cargadas');
    return;
  }
  // Sebastián 15-may-2026: la IA ahora propone UNA sugerencia POR LOTE
  // físico (no por producto con frecuencia). Se persisten TODAS tal cual.
  // El backend valida L-V + no festivo + max 2/día · mueve si no cumple.
  const porProducto = {};
  sugIA.forEach(s => {
    porProducto[s.producto] = (porProducto[s.producto] || 0) + 1;
  });
  const resumen = Object.keys(porProducto).sort().map(p =>
    '  · ' + p + ' · ' + porProducto[p] + ' lote' + (porProducto[p]>1?'s':'')
  ).join('\n');
  if (!confirm('¿Aplicar plan IA?\n\n' +
               sugIA.length + ' lotes en total · ' + Object.keys(porProducto).length + ' productos:\n\n' +
               resumen + '\n\n' +
               'Esto BORRA el plan actual (eos_canonico + eos_plan) y\n' +
               'persiste los lotes IA tal cual los propuso. Validación L-V\n' +
               'sin festivos (mueve al siguiente día hábil si choca).\n\n' +
               '¿Confirmás?')) return;
  const btn = document.getElementById('btn-ia-anual');
  btn.disabled = true;
  btn.textContent = '⏳ Aplicando…';
  try {
    const sugerencias = sugIA.map(s => ({
      producto: s.producto, kg: s.kg, fecha: s.fecha,
    }));
    const r = await fetch('/api/plan/aplicar-ia-bulk', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
      body: JSON.stringify({
        sugerencias: sugerencias,
        cancelar_actual: true,
      }),
    });
    const d = await r.json();
    if (!r.ok){
      alert('❌ Error: ' + (d.error || r.status));
      return;
    }
    let msg = '✅ Plan IA aplicado\n\n' +
      '· Lotes creados: ' + d.n_lotes_creados + '\n' +
      '· Lotes cancelados (plan anterior): ' + d.n_lotes_cancelados + '\n' +
      '· Lotes movidos al sig día hábil: ' + d.lotes_movidos + '\n' +
      '· Lotes rechazados: ' + d.n_rechazados + '\n';
    if (d.sin_formula && d.sin_formula.length){
      msg += '\n⚠ Productos sin fórmula (no agendados):\n  ' + d.sin_formula.join('\n  ');
    }
    if (d.rechazados && d.rechazados.length){
      msg += '\n⚠ Rechazados:\n' + d.rechazados.slice(0,5).map(x =>
        '  · ' + x.producto + ' · ' + x.razon
      ).join('\n');
    }
    alert(msg);
    cargar();
  } catch(e){
    alert('❌ Error red: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '🎯 Aplicar plan IA';
  }
}

async function feedbackIA(decisionId, accion, kgReal, fechaReal, comentario){
  if (!decisionId) return;
  try {
    await fetch('/api/plan/autoplan-ia/feedback', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
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
  // Fix B-7 · disable btn-aplicar durante POST + S-1 credentials same-origin
  const btnAp = document.getElementById('btn-aplicar');
  if (btnAp) btnAp.disabled = true;
  try {
    const r = await fetch('/api/plan/plan-sugerido/ejecutar', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':getCSRF()},
      credentials: 'same-origin',
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
  finally { if (btnAp) btnAp.disabled = false; }
}

cargar();
</script>
</body></html>"""


def _ia_autoplan_sugerir(payload_contexto, modelo="claude-sonnet-4-6"):
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

    # Sebastián 14-may-2026: "necesito que pueda aceptar y que no se borre
    # y ya quede ese plan · asegúrate que proponga con la logica de canonico"
    # Plan CANÓNICO = una entrada por producto con frecuencia y kg por lote.
    # El backend expande a serie completa (365d) respetando reglas operativas.
    system_prompt = (
        "Eres el jefe de producción de un laboratorio cosmético colombiano. "
        "Analizás las ventas y stock por producto, y devolvés sugerencias "
        "concretas de qué producir, cuándo y cuánto. Tu lógica: producir "
        "20 días antes de que se agote cada producto.\n\n"
        "REGLAS DE PRODUCCIÓN (obligatorias):\n"
        "1. OBLIGATORIO: para cada producto del input con velocidad > 0, "
        "devolvé TANTOS lotes como sean necesarios para CUBRIR EL HORIZONTE "
        "COMPLETO (horizonte_dias días). NO pares hasta cubrir los "
        "horizonte_dias completos. Si horizonte=365 y un lote dura 45 días, "
        "necesitás ~8 lotes de ese producto.\n"
        "2. Primer lote: hoy + cob_dias - 20. Si esa fecha cae antes de "
        "fecha_inicio_minima_plan, usá fecha_inicio_minima_plan (próximo "
        "día hábil). Programá lotes en mayo si la cobertura lo exige · "
        "NO empujes todo a meses futuros.\n"
        "3. Lotes siguientes: cada (kg_lote / velocidad_kg_dia) días desde "
        "el lote anterior. Repetí hasta llegar a hoy + horizonte_dias.\n"
        "4. kg por lote: usá lote_recomendado_kg (no lote_size_kg_excel). Si "
        "lote_fuente='excel_piloto_inviable' → OMITIR producto y mencionar.\n"
        "5. Si mps_status='FALTAN_MPS' → OMITIR producto y mencionar.\n\n"
        "REGLAS DE CALENDARIO (críticas):\n"
        "A. SOLO L-V · NUNCA programes sábado/domingo.\n"
        "B. EVITAR festivos_colombianos · si la fecha cae festivo, mover al "
        "siguiente día hábil.\n"
        "C. MÁXIMO 2 producciones por día.\n"
        "D. Lotes >50kg ocupan el día SOLO · no comparte con otro.\n"
        "E. Vit C y Triactive (productos complejos): SOLO lun o mié, ocupan "
        "el día solo.\n"
        "F. ESCALONAR: distribuí los lotes L-V a lo largo del horizonte. NO "
        "apiles todos el mismo día. Si dos productos chocan, mové el menos "
        "urgente al siguiente día hábil disponible.\n\n"
        "FORMATO: devolvé UNA sugerencia POR CADA LOTE físico (no una por "
        "producto · UNA POR LOTE). Si GEL necesita 8 lotes en horizonte "
        "365d, devolvés 8 sugerencias GEL con fechas distintas. Ordená "
        "cronológicamente por fecha.\n\n"
        "CONFIANZA (0.0-1.0): defecto 0.90 si reglas cumplen. 0.95+ si hay "
        "historial real. 0.80 si velocidad baja (<0.5 uds/día). NO uses <0.70.\n\n"
        "RESPUESTA: SOLO JSON válido sin markdown. Ejemplo para horizonte "
        "365 días con GEL HIDRATANTE (58kg dura ~45d → 8 lotes/año):\n"
        "{\"sugerencias\":["
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2026-05-25\",\"kg\":58,"
        "\"motivo\":\"urgente\",\"cobertura_post_dias\":45,\"confianza\":0.95,"
        "\"razonamiento\":\"Stock 23d · agota 6-jun · primer lote 20d antes\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2026-07-08\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 2 · 58kg/1.3kg-dia = 45d después del 1\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2026-08-21\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 3 · serie continúa\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2026-10-05\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 4\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2026-11-19\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 5\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2027-01-04\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 6\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2027-02-18\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 7\"},"
        "{\"producto\":\"GEL HIDRATANTE\",\"fecha\":\"2027-04-05\",\"kg\":58,"
        "\"motivo\":\"plan\",\"cobertura_post_dias\":45,\"confianza\":0.90,"
        "\"razonamiento\":\"Lote 8 · cubre hasta may-2027\"},"
        "{\"producto\":\"LIMP BHA 2%\",\"fecha\":\"2026-05-27\",\"kg\":200,"
        "\"motivo\":\"urgente\",\"cobertura_post_dias\":150,\"confianza\":0.95,"
        "\"razonamiento\":\"Día solo (>50kg) · escalonado vs GEL\"}],"
        "\"comentario_general\":\"GEL: 8 lotes (365d). BHA: serie iniciada.\"}"
    )
    # Sebastián 15-may-2026: quitado el [:8000] que truncaba productos.
    # Con 8 productos canónicos + reglas + historial + 365d festivos el
    # payload sano cabe en context window de Sonnet 4.6.
    h = payload_contexto.get('horizonte_dias', 30)
    user_msg = (
        f"Contexto del cliente y productos:\n"
        f"{_json.dumps(payload_contexto, ensure_ascii=False, default=str)}\n\n"
        f"Generá el autoplan para horizonte {h} días. CRÍTICO: cubrí los "
        f"{h} días COMPLETOS · si un producto necesita 8 lotes en el año, "
        f"devolvé 8 sugerencias de ese producto con fechas escalonadas. "
        f"NO truncar · NO devolver solo el primer lote. Devolvé SOLO JSON."
    )

    # Sebastián 15-may-2026: max_tokens subido 4000 → 16000.
    # Razón: ahora IA devuelve UNA sugerencia POR LOTE (no por producto).
    # En horizonte 180d con 8 productos puede dar 30-60 sugerencias,
    # cada una con razonamiento de 150-200 caracteres · 4000 truncaba.
    body = _json.dumps({
        "model": modelo,
        "max_tokens": 16000,
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
        with _ureq.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as ex:
        return None, f"Error llamando Anthropic: {ex}"

    raw_text = ""
    try:
        raw_text = data["content"][0]["text"]
    except Exception as ex:
        return None, f"Respuesta IA sin content: {ex} · data: {str(data)[:500]}"

    # Parser robusto · acepta markdown code blocks + texto extra
    text = raw_text.strip()
    parsed = None
    parse_err = None

    # Estrategia 1: parsear como JSON directo
    try:
        parsed = _json.loads(text)
    except Exception as ex1:
        parse_err = str(ex1)
        # Estrategia 2: extraer entre ```json...```
        import re as _re
        m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
        if m:
            try:
                parsed = _json.loads(m.group(1))
                parse_err = None
            except Exception as ex2:
                parse_err = str(ex2)
        # Estrategia 3: encontrar primer { y último } válido
        if parsed is None:
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start >= 0 and end > start:
                    parsed = _json.loads(text[start:end+1])
                    parse_err = None
            except Exception as ex3:
                parse_err = str(ex3)
        # Estrategia 4 · Sebastián 14-may-2026: respuestas largas se truncan
        # extraer cada sugerencia individual con regex robusta
        if parsed is None:
            try:
                # Buscar bloque "sugerencias": [
                m_sug = _re.search(r'"sugerencias"\s*:\s*\[(.*)', text, _re.DOTALL)
                if m_sug:
                    inner = m_sug.group(1)
                    # Extraer objetos { ... } balanceados uno a uno
                    sugs = []
                    depth = 0
                    start_obj = -1
                    for i, ch in enumerate(inner):
                        if ch == '{':
                            if depth == 0:
                                start_obj = i
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0 and start_obj >= 0:
                                obj_text = inner[start_obj:i+1]
                                try:
                                    obj = _json.loads(obj_text)
                                    if isinstance(obj, dict) and obj.get("producto"):
                                        sugs.append(obj)
                                except Exception:
                                    pass
                                start_obj = -1
                    if sugs:
                        # Comentario general · buscar después del último ]
                        m_com = _re.search(r'"comentario_general"\s*:\s*"([^"]*)"', text, _re.DOTALL)
                        comentario = m_com.group(1) if m_com else f"Parser recuperó {len(sugs)} sugerencias de respuesta truncada"
                        parsed = {"sugerencias": sugs, "comentario_general": comentario}
                        parse_err = None
            except Exception as ex4:
                parse_err = f"truncamiento_recovery: {ex4}"

    if parsed is None:
        return None, f"IA respondió pero no se pudo parsear JSON · error: {parse_err} · raw_preview: {raw_text[:800]}"

    tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
    return {"sugerencias": parsed.get("sugerencias", []),
            "comentario": parsed.get("comentario_general", ""),
            "tokens": tokens, "modelo": modelo,
            "raw_text": raw_text}, None


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
        # Sebastián 14-may-2026: "la IA solo me pone producciones por mayo
        # no hace por mas tiempos · proponga con la logica de canonico"
        # Cap subido de 180 → 730 días para permitir plan anual completo.
        horizonte = max(7, min(730, int(body.get("horizonte_dias") or 90)))
    except (ValueError, TypeError):
        horizonte = 90
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
                # NO reutilizar cache vacío · forzá recálculo si no había sugerencias
                if cached.get("sugerencias"):
                    cached["cache_hit"] = True
                    cached["cache_fecha"] = cache_row[1]
                    return jsonify(cached)
            except Exception:
                pass  # cache corrupto · ignorar y recalcular

    # 2) Construir contexto · solo Animus DTC por ahora (Fernando B2B después)
    necesidades = _calcular_animus_dtc(c, ventana=60, cob_critico=20,
                                        cob_alerta=25, cob_vigilar=45)

    # 2b) Producciones reales últ 180 días por producto · Sebastián 14-may-2026:
    # "sugiere triactive 0.2 gramos lo cual no tiene lógica · revisemos
    # porque sugiere eso". Causa: el Excel tiene lote_size_kg de FÓRMULA
    # PILOTO (Triactive=0.2kg = 200g de prueba), no lote real de producción
    # (que es 13kg según historial). La IA debe usar el promedio real.
    historico_por_prod = {}
    for r in c.execute(
        """SELECT producto, fecha_programada,
                  COALESCE(kg_real, cantidad_kg, 0)
           FROM produccion_programada
           WHERE fin_real_at IS NOT NULL
             AND COALESCE(kg_real, cantidad_kg, 0) > 0
             AND date(fin_real_at) >= date('now', '-5 hours', '-180 day')
           ORDER BY fin_real_at DESC""",
    ).fetchall():
        historico_por_prod.setdefault(r[0] or "", []).append({
            "fecha": (r[1] or "")[:10],
            "kg": float(r[2] or 0),
        })

    def _calcular_lote_real_promedio(prod_nombre, lote_excel):
        """Devuelve (lote_recomendado_kg, fuente, justificacion).
        Si hay historial real → usar promedio.
        Si el Excel tiene <3kg pero hay velocidad alta → usar fórmula de
        cobertura (vel × 60 días) como fallback.
        Si no hay nada → devolver el Excel pero con flag de advertencia.
        """
        historial = historico_por_prod.get(prod_nombre, [])
        if historial:
            kgs = [h["kg"] for h in historial]
            promedio = sum(kgs) / len(kgs)
            return round(promedio, 1), "historico_real", \
                   f"{len(historial)} producciones reales últ 180d · promedio {round(promedio, 1)}kg"
        # Sin historial · si lote_excel es muy chico, advertir
        if lote_excel and lote_excel < 3:
            return None, "excel_piloto_inviable", \
                   f"lote_size_kg del Excel ({lote_excel}kg) es fórmula piloto · no hay producciones reales · NO programar"
        return lote_excel, "excel", \
               f"lote_size_kg del Excel ({lote_excel}kg) · sin historial real"

    # Filtrar a productos relevantes · velocidad real + fórmula + cobertura
    # menor al horizonte (los que SI necesitan plan).
    # Sebastián 14-may-2026: timeout Anthropic con contexto grande · reducir
    # a productos que realmente requieren decisión para acelerar IA.
    productos_ctx = []
    for n in necesidades:
        if (n.get("velocidad_uds_dia") or 0) < 0.1:
            continue  # sin ventas
        if n.get("mps_status") == "SIN_FORMULA":
            continue
        # Sebastián 14-may-2026: "asegúrate que proponga con la logica de
        # canonico". Antes filtraba productos con cob > horizonte + 30
        # (los que no necesitaban plan ahora). Pero para plan canónico
        # anual, TODOS los productos con velocidad real deben tener serie.
        # Mantenemos el filtro SOLO si el horizonte es corto (≤60d).
        cob = n.get("dias_cobertura")
        if horizonte <= 60 and cob is not None and cob > horizonte + 30:
            continue
        nombre = n["producto_nombre"]
        lote_excel = n.get("lote_bulk_kg", 0) or 0
        lote_recomendado, fuente_lote, _ = _calcular_lote_real_promedio(nombre, lote_excel)
        # Solo últimas 2 producciones históricas (no 5) · payload menor
        historial = historico_por_prod.get(nombre, [])[:2]
        productos_ctx.append({
            "nombre": nombre,
            "ml": n.get("ml_unidad", 30),
            "lote_kg": lote_recomendado or lote_excel,
            "lote_fuente": fuente_lote,
            "stock_kg": n.get("stock_kg_total", 0),
            "vel_uds_dia": round(n.get("velocidad_uds_dia", 0), 2),
            "vel_kg_dia": round(n.get("velocidad_kg_dia", 0), 3),
            "cob_dias": cob,
            "urgencia": n.get("urgencia"),
            "mps_status": n.get("mps_status"),
            "ultima_prod": n.get("ultima_produccion_fecha"),
            "ultima_kg": n.get("ultima_produccion_kg"),
            "produc_recientes": historial,
            "lotes_agendados_n": len(n.get("planificacion") or []),
        })

    # 3) Historial reciente para feedback · últimas 20 decisiones
    historial_rows = c.execute(
        """SELECT producto_nombre, sugerencia_kg, sugerencia_fecha,
                  motivo_ia, accion_usuario, kg_real, fecha_real,
                  comentario_usuario
           FROM autoplan_decisiones
           WHERE cliente = ?
             AND accion_usuario IS NOT NULL
             AND accion_usuario != 'obsoleta_mig131'
           ORDER BY accion_at DESC LIMIT 10""",
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
    # Sebastián 15-may-2026: "necesito que recomiende en mayo también ·
    # el martes después del lunes debemos producir". El inicio del plan
    # es el PRÓXIMO DÍA HÁBIL (L-V no festivo), arrancando mañana. Si el
    # lunes es festivo (ej. 18-may-2026 Ascensión), arranca el martes.
    # Antes era "el próximo lunes" fijo · empujaba el plan a junio.
    _d_ini = hoy_dt + _td_ia(days=1)
    _guard = 0
    while (_d_ini.weekday() >= 5 or es_festivo_colombia(_d_ini)) and _guard < 30:
        _d_ini = _d_ini + _td_ia(days=1)
        _guard += 1
    fecha_inicio_minima = _d_ini.isoformat()

    # Festivos colombianos del horizonte para que la IA los vea explícitos
    festivos_horizonte = []
    for offset in range(horizonte + 14):
        d = hoy_dt + _td_ia(days=offset)
        if es_festivo_colombia(d):
            festivos_horizonte.append(d.isoformat())

    reglas = {
        "fecha_inicio_minima": fecha_inicio_minima,
        "regla_inicio": "Empezar a programar desde el " + fecha_inicio_minima + " (próximo día hábil) · NO antes",
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
        "horizontes_validos": [15, 30, 60, 90, 120, 180, 365, 730],
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
            # P0-8 23-may-PM · auditoría agente · keys mismatch hacían que
            # lote_size_kg, velocidad_uds_mes, ml_unidad SIEMPRE quedaran
            # NULL en autoplan_decisiones (toda data IA de los últimos
            # ~10 días corrupta). prod_ctx tiene 'lote_kg' (no 'lote_size_kg'),
            # 'vel_uds_dia' (no 'velocidad_uds_mes'), 'ml' (no 'ml_unidad').
            (cliente, prod_nom, horizonte,
             prod_ctx.get("stock_kg") if prod_ctx else None,
             round((prod_ctx.get("vel_uds_dia") or 0) * 30, 2) if prod_ctx else None,
             prod_ctx.get("ml") if prod_ctx else None,
             prod_ctx.get("lote_kg") if prod_ctx else None,
             s.get("kg"), s.get("fecha"), s.get("cobertura_post_dias"),
             s.get("motivo") or s.get("razonamiento"), user,
             resultado["modelo"], resultado["tokens"],
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
        "raw_text_ia": resultado.get("raw_text", "")[:3000],  # diagnóstico
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
                """SELECT producto, fecha_programada, origen, estado, fin_real_at,
                          inicio_real_at
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
            if row[5]:  # inicio_real_at · lote en curso · inmutable
                errores.append({"accion": "cancelar", "indice": i,
                                "error": f"id {pid_int} en curso (inicio_real_at) · no cancelable"})
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
            # INSERT retroactivo · Sebastián 14-may-2026 (audit W3):
            # Setear inicio_real_at + fin_real_at consistente con
            # registrar-produccion-completada (placeholders 8:00/17:00)
            c.execute(
                """INSERT INTO produccion_programada
                       (producto, fecha_programada, cantidad_kg, kg_real,
                        estado, origen, inicio_real_at, fin_real_at,
                        lotes, observaciones)
                   VALUES (?, ?, ?, ?, 'completado', 'eos_retroactivo',
                           ? || ' 08:00:00', ? || ' 17:00:00', 1, ?)""",
                (producto_canonico, fecha, lote_size, kg, fecha, fecha,
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


def _es_producto_complejo(producto_nombre, conn=None):
    """True si el producto requiere envasado el mismo día.

    FIX P2 audit 24-may-2026 · ahora consulta producto_perfil_riesgo.
    requiere_envasado_mismo_dia (mig 169) primero. Si no hay perfil ·
    fallback al hard-coded PRODUCTOS_COMPLEJOS_SUBSTR (Vit C, Triactive).
    Permite que el equipo agregue nuevos productos complejos desde UI
    sin tocar código.
    """
    if not producto_nombre:
        return False
    pu = producto_nombre.upper()
    # Intentar BD primero (autoritativo si el perfil existe)
    if conn is not None:
        try:
            row = conn.execute(
                """SELECT COALESCE(requiere_envasado_mismo_dia, 0)
                   FROM producto_perfil_riesgo
                   WHERE UPPER(TRIM(producto_nombre)) = UPPER(TRIM(?))""",
                (producto_nombre,),
            ).fetchone()
            if row is not None:
                return bool(row[0])
        except Exception:
            pass
    # Fallback hard-coded (Vit C / Triactive)
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
    es_complejo = _es_producto_complejo(producto_nombre, c if hasattr(c, 'execute') else None)
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

    # FIX 1-jun-2026 audit Planta (P0 drift) · el flujo canónico de iniciar
    # (prog_iniciar_produccion) descuenta MP y setea inicio_real_at/
    # inventario_descontado_at SIN cambiar estado (queda 'programado'). El guard
    # de arriba (solo estado) dejaba cancelar una producción YA iniciada con MP
    # descontada SIN revertir → la MP desaparecía del kardex (drift permanente).
    # Ahora bloqueamos si ya arrancó/descontó: hay que revertir el descuento primero.
    ya = cur.execute(
        "SELECT COALESCE(inicio_real_at,''), COALESCE(inventario_descontado_at,'') "
        "FROM produccion_programada WHERE id=?", (pid,)).fetchone()
    if ya and (ya[0] or ya[1]):
        return jsonify({
            "error": "no se puede cancelar: la producción ya inició o descontó inventario. "
                     "Revertí el descuento primero (revertir-completado).",
            "codigo": "YA_EN_EJECUCION",
            "inicio_real_at": ya[0] or None,
            "inventario_descontado_at": ya[1] or None,
        }), 409

    cur.execute("UPDATE produccion_programada SET estado='cancelado' WHERE id = ?", (pid,))
    # FIX 1-jun-2026 · audit ANTES del commit (audit_log usa el cursor del caller
    # sin commit propio · antes corría DESPUÉS del commit → nunca se persistía).
    audit_log(cur, usuario=user, accion="CANCELAR_PRODUCCION_PROGRAMADA",
              tabla="produccion_programada", registro_id=pid,
              antes={"estado": estado_actual, "producto": producto, "fecha": fecha},
              despues={"estado": "cancelado"})
    conn.commit()
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
    # Sebastián 19-may-2026: arrastrar una producción la FIJA (origen=eos_plan).
    # Es una decisión del usuario → los procesos automáticos (regenerar
    # canónicos, generar-plan-perfecto, sync) ya no la tocan.
    cur.execute(
        """UPDATE produccion_programada
           SET fecha_programada = ?,
               origen = 'eos_plan',
               observaciones = COALESCE(observaciones,'') ||
                   ' · REPROGRAMADO de ' || COALESCE(?,'?') || ' a ' || ? ||
                   CASE WHEN ? != '' THEN ' (razón: ' || ? || ')' ELSE '' END ||
                   ' · FIJADO · ' || datetime('now', '-5 hours')
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


@bp.route("/api/plan/proximas/<int:pid>/cantidad", methods=["POST"])
def actualizar_cantidad_proxima(pid):
    """Cambia los kg a producir de un lote agendado.

    Sebastián 15-may-2026: "cuando le doy click al producto quiero
    poder cambiar los kilogramos a producir".

    Body: {cantidad_kg: float > 0}

    Inmutabilidad: si el lote ya inició o terminó → 409.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    body = request.get_json(silent=True) or {}
    try:
        nueva_kg = float(body.get("cantidad_kg") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_kg inválida"}), 400
    if not (0 < nueva_kg <= 1000):
        return jsonify({"error": "cantidad_kg debe estar entre 0 y 1000"}), 400

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        """SELECT estado, producto, cantidad_kg, inicio_real_at, fin_real_at
           FROM produccion_programada WHERE id = ?""",
        (pid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "lote no encontrado"}), 404
    estado_actual, producto, kg_antes, inicio_real, fin_real = row

    if fin_real:
        return jsonify({"error": "lote ya completado · no editable"}), 409
    if inicio_real:
        return jsonify({"error": "lote en curso · no editable"}), 409
    if estado_actual not in ('pendiente', 'programado', 'esperando_recurso'):
        return jsonify({
            "error": f"solo editable en pendiente/programado · estado: {estado_actual}",
        }), 409

    # Sebastián 16-may-2026: si la nueva cantidad convierte el lote en
    # GRANDE (>50kg), ese día debe quedar SOLO. Si el día ya tiene otro
    # lote, avisar · salvo que se pase forzar=true.
    if nueva_kg > LOTE_GRANDE_KG and not body.get("forzar"):
        fila_fecha = cur.execute(
            "SELECT fecha_programada FROM produccion_programada WHERE id = ?",
            (pid,),
        ).fetchone()
        if fila_fecha and fila_fecha[0]:
            otros = cur.execute(
                """SELECT COUNT(*) FROM produccion_programada
                   WHERE date(fecha_programada) = date(?)
                     AND id != ?
                     AND estado IN ('pendiente','programado','en_curso','esperando_recurso')""",
                (fila_fecha[0], pid),
            ).fetchone()[0]
            if otros and otros > 0:
                return jsonify({
                    "error": (f"Con {nueva_kg:.0f}kg este lote pasa a ser GRANDE "
                              f"(>{LOTE_GRANDE_KG}kg) y necesita el día solo · "
                              f"ese día ya tiene {otros} producción(es). Movelo a "
                              f"otro día o reintentá marcando forzar."),
                    "lote_grande_conflicto": True,
                    "otros_ese_dia": otros,
                }), 409

    # Sebastián 19-may-2026: editar los kg también FIJA la producción.
    cur.execute(
        """UPDATE produccion_programada
           SET cantidad_kg = ?,
               origen = 'eos_plan',
               observaciones = COALESCE(observaciones,'') ||
                 ' · KG editado de ' || COALESCE(CAST(? AS TEXT),'?') ||
                 ' a ' || CAST(? AS TEXT) || ' · FIJADO · ' || datetime('now','-5 hours')
           WHERE id = ?""",
        (nueva_kg, kg_antes, nueva_kg, pid),
    )
    audit_log(cur, usuario=user, accion="EDITAR_KG_PRODUCCION",
              tabla="produccion_programada", registro_id=pid,
              antes={"cantidad_kg": kg_antes, "producto": producto},
              despues={"cantidad_kg": nueva_kg})
    conn.commit()
    return jsonify({"ok": True, "id": pid, "producto": producto,
                    "kg_antes": kg_antes, "kg_nuevo": nueva_kg})


@bp.route("/api/admin/diagnostico-migracion", methods=["GET"])
def diagnostico_migracion():
    """Compara conteos de la base vieja (SQLite en /var/data/inventario.db)
    contra la nueva (PostgreSQL) · diagnóstico de pérdida de datos en la
    migración 18-may-2026. Solo admin / Compras.

    Crítico: detectar si movimientos (kardex MPs) o produccion_programada
    perdieron filas en la migración.
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    import os
    import sqlite3 as _sq
    SQLITE_PATH = '/var/data/inventario.db'
    if not os.path.exists(SQLITE_PATH):
        return jsonify({'error': f'SQLite viejo no existe en {SQLITE_PATH}',
                        'hint': 'puede haberse borrado'}), 404

    TABLAS = [
        'movimientos', 'produccion_programada', 'maestro_mps',
        'ordenes_compra', 'ordenes_compra_items',
        'solicitudes_compra', 'solicitudes_compra_items',
        'pagos_oc', 'comprobantes_pago',
        'conteos_fisicos', 'conteo_items',
        'lotes_mp',
    ]
    pg_cur = get_db().cursor()
    sq_conn = _sq.connect(SQLITE_PATH)
    sq_cur = sq_conn.cursor()

    resumen = []
    for t in TABLAS:
        try:
            sq_cur.execute(f"SELECT COUNT(*) FROM {t}")
            sq_count = sq_cur.fetchone()[0]
        except Exception as e:
            sq_count = f'ERR: {str(e)[:80]}'
        try:
            pg_cur.execute(f"SELECT COUNT(*) FROM {t}")
            pg_count = pg_cur.fetchone()[0]
        except Exception as e:
            pg_count = f'ERR: {str(e)[:80]}'
        diff = None
        try:
            diff = int(sq_count) - int(pg_count)
        except Exception:
            pass
        resumen.append({
            'tabla': t, 'sqlite_viejo': sq_count,
            'postgres_actual': pg_count, 'diff_faltan_en_pg': diff,
            'alerta': isinstance(diff, int) and diff != 0,
        })

    estados = []
    try:
        sq_cur.execute("""SELECT LOWER(COALESCE(estado,'')), COUNT(*)
                          FROM produccion_programada GROUP BY 1""")
        sq_e = dict(sq_cur.fetchall())
    except Exception:
        sq_e = {}
    try:
        pg_cur.execute("""SELECT LOWER(COALESCE(estado,'')), COUNT(*)
                          FROM produccion_programada GROUP BY 1""")
        pg_e = dict(pg_cur.fetchall())
    except Exception:
        pg_e = {}
    for e in sorted(set(sq_e.keys()) | set(pg_e.keys())):
        s = sq_e.get(e, 0)
        p = pg_e.get(e, 0)
        estados.append({'estado': e or '(vacío)',
                        'sqlite_viejo': s, 'postgres_actual': p,
                        'diff_faltan_en_pg': s - p})

    movs_tipo = []
    try:
        sq_cur.execute("""SELECT tipo, COUNT(*) FROM movimientos GROUP BY 1""")
        sq_m = dict(sq_cur.fetchall())
    except Exception:
        sq_m = {}
    try:
        pg_cur.execute("""SELECT tipo, COUNT(*) FROM movimientos GROUP BY 1""")
        pg_m = dict(pg_cur.fetchall())
    except Exception:
        pg_m = {}
    for t in sorted(set(sq_m.keys()) | set(pg_m.keys())):
        s = sq_m.get(t, 0)
        p = pg_m.get(t, 0)
        movs_tipo.append({'tipo': t or '(vacío)',
                          'sqlite_viejo': s, 'postgres_actual': p,
                          'diff_faltan_en_pg': s - p})

    sq_conn.close()
    return jsonify({
        'sqlite_path': SQLITE_PATH,
        'tablas': resumen,
        'produccion_por_estado': estados,
        'movimientos_por_tipo': movs_tipo,
    })


@bp.route("/api/admin/diagnostico-migracion-detalle", methods=["GET"])
def diagnostico_migracion_detalle():
    """Diagnóstico granular fila-por-fila · compara IDs específicos entre
    SQLite viejo y PostgreSQL actual. Confirma con certeza que ninguna
    producción ejecutada ni movimiento de kardex se perdió."""
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    import os
    import sqlite3 as _sq
    SQLITE_PATH = '/var/data/inventario.db'
    if not os.path.exists(SQLITE_PATH):
        return jsonify({'error': f'SQLite viejo no existe en {SQLITE_PATH}'}), 404

    pg_cur = get_db().cursor()
    sq_conn = _sq.connect(SQLITE_PATH)
    sq_cur = sq_conn.cursor()

    # ── 1) Producciones ejecutadas (fin_real_at o inventario_descontado_at) ──
    Q_EJEC = ("""SELECT id, COALESCE(producto,''), COALESCE(fecha_programada,''),
                        COALESCE(fin_real_at,''), COALESCE(cantidad_kg, 0),
                        COALESCE(estado,''),
                        COALESCE(inventario_descontado_at,''),
                        COALESCE(origen,'')
                 FROM produccion_programada
                 WHERE fin_real_at IS NOT NULL
                    OR inventario_descontado_at IS NOT NULL
                 ORDER BY id""")
    sq_cur.execute(Q_EJEC)
    sq_prods = {r[0]: r for r in sq_cur.fetchall()}
    pg_cur.execute(Q_EJEC)
    pg_prods = {r[0]: r for r in pg_cur.fetchall()}
    prod_faltan = []
    for pid in sorted(sq_prods.keys() - pg_prods.keys()):
        r = sq_prods[pid]
        prod_faltan.append({
            'id': r[0], 'producto': r[1], 'fecha_programada': r[2],
            'fin_real_at': r[3], 'cantidad_kg': r[4], 'estado': r[5],
            'inventario_descontado_at': r[6], 'origen': r[7],
        })

    # ── 2) Movimientos (kardex MP) — comparar todos los IDs ──
    sq_cur.execute("SELECT id FROM movimientos")
    sq_mov = {r[0] for r in sq_cur.fetchall()}
    pg_cur.execute("SELECT id FROM movimientos")
    pg_mov = {r[0] for r in pg_cur.fetchall()}
    mov_faltan_ids = sorted(sq_mov - pg_mov)

    mov_faltan_detalle = []
    if mov_faltan_ids:
        ph = ','.join(['?'] * len(mov_faltan_ids))
        sq_cur.execute(f"""SELECT id, COALESCE(material_id,''),
                          COALESCE(material_nombre,''), COALESCE(cantidad,0),
                          COALESCE(fecha,''), COALESCE(lote,''),
                          COALESCE(tipo,'')
                          FROM movimientos WHERE id IN ({ph})
                          ORDER BY id""", mov_faltan_ids)
        for r in sq_cur.fetchall():
            mov_faltan_detalle.append({
                'id': r[0], 'material_id': r[1], 'material_nombre': r[2],
                'cantidad': r[3], 'fecha': r[4], 'lote': r[5], 'tipo': r[6],
            })

    # ── 3) Últimas 15 Entradas (ingresos de MP) · verificación visual ──
    Q_ENT = """SELECT id, COALESCE(material_id,''),
                      COALESCE(material_nombre,''), COALESCE(cantidad,0),
                      COALESCE(fecha,''), COALESCE(lote,'')
               FROM movimientos WHERE tipo='Entrada'
               ORDER BY fecha DESC, id DESC LIMIT 15"""
    sq_cur.execute(Q_ENT)
    sq_ent = [{'id': r[0], 'material_id': r[1], 'material_nombre': r[2],
               'cantidad': r[3], 'fecha': r[4], 'lote': r[5]}
              for r in sq_cur.fetchall()]
    pg_cur.execute(Q_ENT)
    pg_ent = [{'id': r[0], 'material_id': r[1], 'material_nombre': r[2],
               'cantidad': r[3], 'fecha': r[4], 'lote': r[5]}
              for r in pg_cur.fetchall()]

    sq_conn.close()
    return jsonify({
        'producciones_ejecutadas': {
            'sqlite_total': len(sq_prods),
            'postgres_total': len(pg_prods),
            'faltan_en_postgres': prod_faltan,
            'todas_intactas': len(prod_faltan) == 0,
        },
        'movimientos_kardex': {
            'sqlite_total': len(sq_mov),
            'postgres_total': len(pg_mov),
            'ids_faltan_en_postgres': mov_faltan_ids,
            'detalle_faltantes': mov_faltan_detalle,
            'todos_intactos': len(mov_faltan_ids) == 0,
        },
        'ultimas_15_entradas_mp': {
            'sqlite': sq_ent,
            'postgres': pg_ent,
        },
    })


@bp.route("/api/plan/recuperar-semana-19may2026", methods=["GET", "POST"])
def recuperar_semana_19may2026():
    """Recuperación puntual · Sebastián 19-may-2026.

    La programación del 19-22 may (4 producciones que Alejandro arregló
    el 18-may) se perdió de produccion_programada. Se reconstruye desde
    el audit_log con origen='eos_plan' → Fija · intocable por procesos
    automáticos. Idempotente: si ya existe (mismo producto + fecha, no
    cancelada) no la duplica.

    Acepta GET para que Sebastián solo abra la URL en el navegador (está
    logueado como admin) y ejecute la recuperación de un solo uso. Si se
    vuelve a abrir, no duplica nada (idempotente).
    """
    user, err = _require_admin_or_compras()
    if err:
        body, code = err
        return jsonify(body), code

    PLAN_SEMANA = [
        ('LIMPIADOR FACIAL HIDRATANTE',  '2026-05-19', 70.0),
        ('SUERO TRIACTIVE RETINOID NAD', '2026-05-20', 20.0),
        ('GEL HIDRATANTE',               '2026-05-21', 60.0),
        ('AZ HIBRID CLEAR',              '2026-05-22', 50.0),
    ]
    conn = get_db()
    c = conn.cursor()
    creadas, ya_existian = [], []
    for producto, fecha, kg in PLAN_SEMANA:
        existe = c.execute(
            """SELECT id FROM produccion_programada
               WHERE UPPER(TRIM(producto)) = UPPER(TRIM(?))
                 AND date(fecha_programada) = ?
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')""",
            (producto, fecha),
        ).fetchone()
        if existe:
            ya_existian.append({'producto': producto, 'fecha': fecha, 'id': existe[0]})
            continue
        c.execute(
            """INSERT INTO produccion_programada
               (producto, fecha_programada, cantidad_kg, lotes, estado, origen,
                observaciones)
               VALUES (?,?,?,1,'programado','eos_plan',
                       'Recuperado del audit_log (perdido 19-may) · FIJADO · '
                       || datetime('now','-5 hours'))""",
            (producto, fecha, kg),
        )
        new_id = c.lastrowid
        creadas.append({'producto': producto, 'fecha': fecha,
                        'cantidad_kg': kg, 'id': new_id})
        try:
            audit_log(c, usuario=user, accion='RECUPERAR_PRODUCCION',
                      tabla='produccion_programada', registro_id=new_id,
                      despues={'producto': producto, 'fecha': fecha,
                               'cantidad_kg': kg, 'origen': 'eos_plan'},
                      detalle=f'Recuperación semana 19-may · {producto} · {fecha}')
        except Exception as _e:
            log.warning('audit RECUPERAR_PRODUCCION falló: %s', _e)
    conn.commit()
    return jsonify({'ok': True, 'creadas': creadas, 'ya_existian': ya_existian,
                    'total_creadas': len(creadas)})


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


@bp.route("/api/plan/aplicar-ia-bulk", methods=["POST"])
def aplicar_ia_bulk():
    """Persiste las N sugerencias IA tal cual · valida L-V + no festivo +
    max 2/día. Si fecha cae mal, mueve al siguiente día hábil disponible.

    Sebastián 15-may-2026: "vamos por paso, logica adecuada, L-V no
    festivos, logica de produccion". Ahora la IA propone UNA sugerencia
    POR LOTE FÍSICO (no por producto). Este endpoint persiste cada
    una sin expandir con frecuencia.

    Body:
        sugerencias: list of {producto, kg, fecha}
        cancelar_actual: bool (default true) · cancela eos_canonico+eos_plan
    """
    user, err = _require_admin_or_compras()
    if err:
        body_err, code = err
        return jsonify(body_err), code

    body = request.get_json(silent=True) or {}
    sugerencias = body.get("sugerencias") or []
    cancelar_actual = bool(body.get("cancelar_actual", True))

    if not isinstance(sugerencias, list) or not sugerencias:
        return jsonify({"error": "sugerencias debe ser lista no vacía"}), 400

    conn = get_db()
    cur = conn.cursor()

    # 1) Cancelar plan canónico sugerido · NUNCA toca lo FIJO (eos_plan)
    # Sebastián 19-may-2026: antes incluía eos_plan, lo que borraba lo que
    # el usuario fijó. Ahora respeta la separación Fijo vs Sugerido.
    n_cancelados = 0
    if cancelar_actual:
        n_cancelados = cur.execute(
            """UPDATE produccion_programada
               SET estado='cancelado',
                   observaciones=COALESCE(observaciones,'') ||
                     ' · CANCELADO_BULK_IA_' || datetime('now','-5 hours')
               WHERE origen IN ('eos_canonico','calendar','manual')
                 AND estado IN ('pendiente','programado','esperando_recurso')
                 AND fin_real_at IS NULL
                 AND inicio_real_at IS NULL""",
        ).rowcount or 0

    # 2) Insertar cada sugerencia · validando fecha hábil
    from datetime import date as _date
    creados = []
    rechazados = []
    sin_formula = []

    for s in sugerencias:
        prod = (s.get("producto") or "").strip()
        if not prod:
            rechazados.append({"producto": "", "razon": "sin nombre"})
            continue
        try:
            kg = float(s.get("kg") or 0)
        except (ValueError, TypeError):
            rechazados.append({"producto": prod, "razon": "kg inválido"})
            continue
        if kg <= 0:
            rechazados.append({"producto": prod, "razon": "kg <= 0"})
            continue
        fecha_str = (s.get("fecha") or "").strip()
        if not fecha_str or not _valida_fecha_iso(fecha_str):
            rechazados.append({"producto": prod, "razon": "fecha inválida"})
            continue
        if not cur.execute(
            "SELECT 1 FROM formula_headers WHERE producto_nombre = ?",
            (prod,),
        ).fetchone():
            sin_formula.append(prod)
            continue

        # Validar L-V no festivo · si no cumple, mover al sig hábil
        f = _date.fromisoformat(fecha_str[:10])
        f_real = _proxima_fecha_habil(
            cur, f, prefer_mwf=False,
            lote_kg=kg, producto_nombre=prod,
        )
        if f_real is None:
            rechazados.append({"producto": prod, "razon": "sin slot hábil"})
            continue
        movida = (f_real != f)

        cur.execute(
            """INSERT INTO produccion_programada
                 (producto, fecha_programada, cantidad_kg, lotes, estado,
                  origen, observaciones, creado_en)
               VALUES (?, ?, ?, 1, 'pendiente', 'eos_plan', ?,
                       datetime('now','-5 hours'))""",
            (prod, f_real.isoformat(), kg,
             f"IA-bulk · {kg}kg" + (f" · movida de {fecha_str[:10]} (festivo/sat)" if movida else "")),
        )
        creados.append({
            "id": cur.lastrowid, "producto": prod, "kg": kg,
            "fecha_pedida": fecha_str[:10],
            "fecha_real": f_real.isoformat(),
            "movida": movida,
        })

    audit_log(cur, usuario=user, accion="APLICAR_IA_BULK",
              tabla="produccion_programada", registro_id=None,
              despues={"n_creados": len(creados),
                       "n_cancelados": n_cancelados,
                       "n_rechazados": len(rechazados),
                       "sin_formula": sin_formula})
    conn.commit()

    return jsonify({
        "ok": True,
        "n_lotes_creados": len(creados),
        "n_lotes_cancelados": n_cancelados,
        "n_rechazados": len(rechazados),
        "lotes_movidos": sum(1 for c in creados if c["movida"]),
        "creados": creados,
        "rechazados": rechazados,
        "sin_formula": sin_formula,
    }), 201


@bp.route("/api/plan/aplicar-ia-anual", methods=["POST"])
def aplicar_ia_anual():
    """Toma las sugerencias IA actuales y las convierte en plan anual
    canónico (eos_canonico × 365 días). Reemplaza el plan activo.

    Sebastián 14-may-2026: "el plan de la IA es mejor, cómo hago para que
    quede y replique por un año exactamente lo que pensamos".

    Para cada producto único en sugerencias:
      - Usa fecha_inicio (primera sugerencia de ese producto en el body)
      - Usa frecuencia_dias del body o frecuencia_default (30)
      - Genera serie hasta horizonte_dias (default 365) respetando L-V,
        festivos colombianos, max 2/día.

    Body:
        sugerencias: list of {producto, kg, fecha_inicio, frecuencia_dias?}
        cancelar_actual: bool (default true) · cancela eos_canonico activos
        horizonte_dias: int (default 365)
        frecuencia_default: int (default 30 · si la sugerencia no la trae)
    """
    user, err = _require_admin_or_compras()
    if err:
        body_err, code = err
        return jsonify(body_err), code

    body = request.get_json(silent=True) or {}
    sugerencias = body.get("sugerencias") or []
    cancelar_actual = bool(body.get("cancelar_actual", True))
    try:
        horizonte = int(body.get("horizonte_dias") or 365)
    except (ValueError, TypeError):
        horizonte = 365
    if not (30 <= horizonte <= 730):
        horizonte = 365
    try:
        freq_default = int(body.get("frecuencia_default") or 30)
    except (ValueError, TypeError):
        freq_default = 30

    if not isinstance(sugerencias, list) or not sugerencias:
        return jsonify({"error": "sugerencias debe ser lista no vacía"}), 400

    # Agrupar sugerencias por producto · primera fecha + frecuencia
    from collections import OrderedDict
    plan_por_producto = OrderedDict()
    for s in sugerencias:
        prod = (s.get("producto") or "").strip()
        if not prod:
            continue
        try:
            kg = float(s.get("kg") or 0)
        except (ValueError, TypeError):
            continue
        if kg <= 0:
            continue
        fecha_ini = (s.get("fecha_inicio") or s.get("fecha") or "").strip()
        try:
            freq = int(s.get("frecuencia_dias") or freq_default)
        except (ValueError, TypeError):
            freq = freq_default
        if not (7 <= freq <= 180):
            freq = freq_default
        if prod not in plan_por_producto:
            plan_por_producto[prod] = {
                "producto": prod, "kg": kg, "fecha_inicio": fecha_ini,
                "frecuencia_dias": freq,
            }

    if not plan_por_producto:
        return jsonify({"error": "ninguna sugerencia válida"}), 400

    conn = get_db()
    cur = conn.cursor()

    # 1) Cancelar todos los lotes auto-generados · plan limpio.
    # Sebastián 14-may-2026: "necesito que pueda aceptar y que no se
    # borre y ya quede ese plan que me propone".
    # SOLO se cancelan eos_canonico (algoritmo auto) · NO se cancelan
    # eos_plan (plan IA aceptado previamente) para preservar decisiones
    # del usuario. Si Sebastián quiere re-aceptar, este endpoint los
    # reemplaza limpiamente porque luego inserta los nuevos.
    n_cancelados = 0
    if cancelar_actual:
        n_cancelados = cur.execute(
            """UPDATE produccion_programada
               SET estado='cancelado',
                   observaciones=COALESCE(observaciones,'') ||
                     ' · CANCELADO_PLAN_IA_ANUAL_' || datetime('now','-5 hours')
               WHERE origen IN ('eos_canonico','calendar','manual')
                 AND estado IN ('pendiente','programado','esperando_recurso')
                 AND fin_real_at IS NULL
                 AND inicio_real_at IS NULL""",
        ).rowcount or 0

    # 2) Generar serie anual para cada producto único
    from datetime import date as _date, timedelta as _td
    hoy = _hoy_colombia()
    f_fin = hoy + _td(days=horizonte)

    total_creados = 0
    detalle_por_producto = []
    productos_sin_formula = []

    # Sebastián 14-may-2026: "acumula todo en un solo dia"
    # Escalonar por producto · cada producto empieza 2 días hábiles
    # después que el anterior · evita pico el primer día.
    productos_lista = list(plan_por_producto.items())
    for idx, (prod, info) in enumerate(productos_lista):
        if not cur.execute(
            "SELECT 1 FROM formula_headers WHERE producto_nombre = ?",
            (prod,),
        ).fetchone():
            productos_sin_formula.append(prod)
            continue

        fecha_ini_str = info["fecha_inicio"]
        if fecha_ini_str and _valida_fecha_iso(fecha_ini_str):
            f_ini = _date.fromisoformat(fecha_ini_str[:10])
            if f_ini < hoy:
                f_ini = hoy + _td(days=3)
        else:
            f_ini = hoy + _td(days=3)

        # OFFSET por producto · escalonar primer lote ·  + 2 días por orden
        f_ini = f_ini + _td(days=idx * 2)

        freq = info["frecuencia_dias"]
        kg = info["kg"]
        fecha_objetivo = f_ini
        creados_prod = 0

        while fecha_objetivo <= f_fin:
            # Pasar lote_kg y producto · respeta grandes solos + complejos lun/mié
            fecha_real = _proxima_fecha_habil(
                cur, fecha_objetivo, prefer_mwf=True,
                lote_kg=kg, producto_nombre=prod,
            )
            if fecha_real is None or fecha_real > f_fin:
                break
            # Origen='eos_plan' · plan aceptado por usuario (Sebastián).
            # Tiene prioridad máxima · ninguna mig ni cron lo cancela auto.
            cur.execute(
                """INSERT INTO produccion_programada
                     (producto, fecha_programada, cantidad_kg, lotes, estado,
                      origen, observaciones, creado_en)
                   VALUES (?, ?, ?, 1, 'pendiente', 'eos_plan', ?,
                           datetime('now','-5 hours'))""",
                (prod, fecha_real.isoformat(), kg,
                 f"Plan-IA-anual ACEPTADO · {kg}kg cada {freq}d · desde sugerencia IA {fecha_ini_str or '(default)'}"),
            )
            creados_prod += 1
            total_creados += 1
            fecha_objetivo = fecha_real + _td(days=freq)

        detalle_por_producto.append({
            "producto": prod, "kg": kg, "frecuencia_dias": freq,
            "fecha_inicio_real": (f_ini.isoformat()),
            "lotes_creados": creados_prod,
        })

    audit_log(cur, usuario=user, accion="APLICAR_IA_ANUAL",
              tabla="produccion_programada", registro_id=None,
              despues={"productos": list(plan_por_producto.keys()),
                       "horizonte_dias": horizonte,
                       "total_creados": total_creados,
                       "n_cancelados": n_cancelados,
                       "cancelar_actual": cancelar_actual})
    conn.commit()

    return jsonify({
        "ok": True,
        "n_productos_aplicados": len(detalle_por_producto),
        "n_lotes_creados": total_creados,
        "n_lotes_cancelados": n_cancelados,
        "horizonte_dias": horizonte,
        "detalle_por_producto": detalle_por_producto,
        "productos_sin_formula_skipped": productos_sin_formula,
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

    # Dedup · Sebastián 14-may-2026 (audit W5): si ya hay back-fill mismo
    # producto + fecha ± 5% kg en últ 7 días, devolver el existente (no doble click).
    dup = cur.execute(
        """SELECT id FROM produccion_programada
           WHERE producto = ?
             AND date(fin_real_at) = ?
             AND ABS(COALESCE(kg_real, cantidad_kg, 0) - ?) < ?
             AND origen = 'eos_retroactivo'""",
        (producto, fecha, kg, max(kg * 0.05, 0.5)),
    ).fetchone()
    if dup:
        return jsonify({
            "ok": True, "duplicado": True, "id": dup[0],
            "mensaje": f"Ya existe back-fill similar (id={dup[0]}) · no se crea duplicado",
        }), 200

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
