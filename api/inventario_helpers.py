"""Helpers canónicos para cálculo de stock MP · CERO SESGO.

Sebastian (2-may-2026 audit zero-error):
"planta tiene un inventario de materias primas y de mee, eso debe funcionar
perfecto tener cero sesgo".

Antes de este módulo, había 6+ implementaciones inconsistentes del cálculo de
stock que usaban tipos inexistentes ('Ingreso','Consumo','Devolucion') y
devolvían valores negativos siempre. El semáforo del dashboard, el gate de
producción, el conteo cíclico y el cálculo IA de compras propuestas estaban
todos rotos por esta razón.

Los tipos REALES en la tabla movimientos son:
  - 'Entrada'   → suma stock (recepción de MP)
  - 'Salida'    → resta stock (consumo en producción)
  - 'Ajuste'    → suma (legacy/animus, sin signo · cantidad puede ser ±)
  - 'Ajuste +'  → suma (animus signed)
  - 'Ajuste -'  → resta (animus signed)

Estados de lote relevantes para "disponible para producción":
  - 'Aprobado' / 'Vigente' / NULL / ''  → SÍ disponible
  - 'CUARENTENA'  → NO disponible (en QC)
  - 'VENCIDO'     → NO disponible
  - 'RECHAZADO'   → NO disponible
  - 'AGOTADO'     → NO disponible

Usar:
  stock_mp_total(conn, codigo_mp)       → stock total incluyendo cuarentena
                                            (para conteo cíclico, auditoría)
  stock_mp_disponible(conn, codigo_mp)  → stock libre para producir HOY
                                            (para semáforo, gate, IA compras)
"""

# Estados de lote que NO se consideran disponibles para producción
ESTADOS_LOTE_NO_DISPONIBLES = ('CUARENTENA', 'VENCIDO', 'RECHAZADO', 'AGOTADO')


def stock_mp_total(conn, codigo_mp):
    """Stock total de un MP · suma todas las entradas - todas las salidas.

    Incluye lotes en cuarentena (visión completa para auditoría/conteo).
    Si necesitas solo lo aprobado para producción, usa stock_mp_disponible.

    Args:
        conn: conexión SQLite
        codigo_mp: str código de MP

    Returns:
        float gramos · puede ser negativo si hubo discrepancia (no es bug del
        helper, es señal de que falta una entrada o sobra una salida).
    """
    r = conn.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN tipo IN ('Entrada', 'Ajuste +', 'Ajuste') THEN cantidad
                WHEN tipo IN ('Salida', 'Ajuste -')            THEN -cantidad
                ELSE 0
            END
        ), 0)
        FROM movimientos
        WHERE material_id = ?
    """, (codigo_mp,)).fetchone()
    return float(r[0] if r else 0)


def stock_mp_disponible(conn, codigo_mp):
    """Stock disponible para producir HOY · excluye cuarentena/vencido/rechazado.

    Esta es la función que el semáforo de producción y la IA de compras DEBEN
    usar. Si un lote está en cuarentena (esperando QC), NO debe contar como
    disponible.

    La lógica es:
      total = stock_mp_total
      no_disponible = entradas con estado_lote en (CUARENTENA, VENCIDO, ...)
      disponible = total - no_disponible

    Salida no se filtra por estado_lote porque ya consumió stock independiente
    del estado del lote del que salió.

    Returns:
        float gramos disponibles · siempre >= 0 en condiciones normales.
    """
    placeholders = ','.join(['?'] * len(ESTADOS_LOTE_NO_DISPONIBLES))
    sql = f"""
        SELECT COALESCE(SUM(
            CASE
                WHEN tipo IN ('Entrada', 'Ajuste +', 'Ajuste')
                     AND COALESCE(NULLIF(TRIM(estado_lote), ''), 'Aprobado')
                         NOT IN ({placeholders})
                THEN cantidad
                WHEN tipo IN ('Salida', 'Ajuste -')
                THEN -cantidad
                ELSE 0
            END
        ), 0)
        FROM movimientos
        WHERE material_id = ?
    """
    params = ESTADOS_LOTE_NO_DISPONIBLES + (codigo_mp,)
    r = conn.execute(sql, params).fetchone()
    return float(r[0] if r else 0)


def stock_mp_cuarentena(conn, codigo_mp):
    """Cantidad en cuarentena de un MP (esperando QC).

    Útil para mostrar en UI "tienes X disponible, Y en QC esperando aprobación".
    """
    r = conn.execute("""
        SELECT COALESCE(SUM(cantidad), 0)
        FROM movimientos
        WHERE material_id = ?
          AND tipo IN ('Entrada', 'Ajuste +', 'Ajuste')
          AND UPPER(COALESCE(estado_lote, '')) = 'CUARENTENA'
    """, (codigo_mp,)).fetchone()
    return float(r[0] if r else 0)


def stock_mp_vencido(conn, codigo_mp):
    """Cantidad ya vencida de un MP · no debe usarse en producción."""
    r = conn.execute("""
        SELECT COALESCE(SUM(cantidad), 0)
        FROM movimientos
        WHERE material_id = ?
          AND tipo IN ('Entrada', 'Ajuste +', 'Ajuste')
          AND UPPER(COALESCE(estado_lote, '')) = 'VENCIDO'
    """, (codigo_mp,)).fetchone()
    return float(r[0] if r else 0)


# ─── MEE (Materiales de Empaque · envases/tapas/etiquetas) ─────────
# A diferencia de MPs, los MEEs tienen `stock_actual` PERSISTIDO en
# maestro_mee como REAL. Esto significa que CADA operación que cambie
# stock debe:
#   1. INSERT INTO movimientos_mee (audit trail)
#   2. UPDATE maestro_mee SET stock_actual (current value)
# en la misma transacción. Si solo hace una de las dos → DRIFT.
#
# stock_mee_persisted: lee directamente maestro_mee.stock_actual (rápido,
#   pero puede divergir del log si hay bug operacional).
# stock_mee_calculated: suma desde movimientos_mee (auditable, lento).
# stock_mee_drift: diferencia entre los dos (si != 0 → bug).


def stock_mee_persisted(conn, codigo_mee):
    """Stock persistido en maestro_mee.stock_actual. Rápido (O(1) lookup)."""
    r = conn.execute(
        "SELECT COALESCE(stock_actual, 0) FROM maestro_mee WHERE codigo = ?",
        (codigo_mee,)
    ).fetchone()
    return float(r[0] if r else 0)


def stock_mee_calculated(conn, codigo_mee):
    """Stock calculado desde movimientos_mee. Verifica consistencia.

    Considera:
      - 'Entrada' suma · cantidad debe ser positiva
      - 'Salida' resta · cantidad debe ser positiva
      - 'Ajuste' (LEGACY) → asume cantidad signed (puede ser positiva o negativa).
        Antes de may-2026 ajustes perdían signo · ahora ajustes nuevos usan
        Entrada/Salida. Para legacy 'Ajuste' tratar cantidad como signed.
      - anulado=1 se ignora.
    """
    r = conn.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN tipo = 'Entrada' AND COALESCE(anulado,0) = 0 THEN cantidad
                WHEN tipo = 'Salida'  AND COALESCE(anulado,0) = 0 THEN -cantidad
                WHEN tipo = 'Ajuste'  AND COALESCE(anulado,0) = 0 THEN cantidad
                ELSE 0
            END
        ), 0)
        FROM movimientos_mee
        WHERE mee_codigo = ?
    """, (codigo_mee,)).fetchone()
    return float(r[0] if r else 0)


def stock_mee_drift(conn, codigo_mee):
    """Diferencia entre stock_actual y SUM(movimientos_mee).

    Si != 0 hay un bug operacional · alguna operación cambió stock_actual sin
    crear el movimiento correspondiente, o viceversa.

    Tolerancia 1.0 unidad para floating point quirks.

    Returns: float · positivo si stock_actual > calc (más stock del que se
    puede justificar con movimientos), negativo si stock_actual < calc.
    """
    return stock_mee_persisted(conn, codigo_mee) - stock_mee_calculated(conn, codigo_mee)


def aplicar_movimiento_mee(conn, codigo_mee, tipo, cantidad, *,
                              observaciones='', responsable='',
                              lote_ref='', batch_ref=''):
    """Helper canónico: registra movimiento MEE Y actualiza stock_actual atómicamente.

    Garantiza CERO SESGO (drift = 0) si se usa para TODAS las operaciones que
    cambian stock MEE.

    Args:
        conn: conexión SQLite (caller controla commit)
        codigo_mee: str código del MEE (debe existir en maestro_mee)
        tipo: 'Entrada' | 'Salida' (NO 'Ajuste' · usar mee_ajustar_stock)
        cantidad: float · siempre positiva. La función decide el signo según tipo.
        observaciones, responsable, lote_ref, batch_ref: opcionales

    Raises:
        ValueError si tipo inválido o cantidad <= 0
        sqlite3 errors propagados al caller

    Returns:
        dict con {'mov_id', 'stock_anterior', 'stock_nuevo'}
    """
    if tipo not in ('Entrada', 'Salida'):
        raise ValueError(f"tipo debe ser 'Entrada' o 'Salida' (Ajuste usar mee_ajustar_stock); recibido: {tipo}")
    cantidad = float(cantidad)
    if cantidad <= 0:
        raise ValueError(f"cantidad debe ser > 0; recibido: {cantidad}")

    cur = conn.cursor()
    # Lock row + capturar stock antes
    row = cur.execute(
        "SELECT COALESCE(stock_actual, 0) FROM maestro_mee WHERE codigo = ?",
        (codigo_mee,)
    ).fetchone()
    if not row:
        raise ValueError(f"MEE '{codigo_mee}' no existe en maestro_mee")
    stock_anterior = float(row[0])

    # Calcular delta según tipo
    delta = cantidad if tipo == 'Entrada' else -cantidad
    stock_nuevo = stock_anterior + delta

    # Salida no puede dejar stock negativo (clamp en MAX(0, ...))
    if stock_nuevo < 0:
        stock_nuevo = 0.0

    # INSERT movimiento + UPDATE stock atómicamente (caller controla commit)
    cur.execute("""
        INSERT INTO movimientos_mee
          (mee_codigo, tipo, cantidad, observaciones, responsable, fecha,
           lote_ref, batch_ref)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)
    """, (codigo_mee, tipo, cantidad, observaciones, responsable,
          lote_ref or '', batch_ref or ''))
    mov_id = cur.lastrowid
    cur.execute(
        "UPDATE maestro_mee SET stock_actual = ? WHERE codigo = ?",
        (stock_nuevo, codigo_mee)
    )
    return {
        'mov_id': mov_id,
        'stock_anterior': stock_anterior,
        'stock_nuevo': stock_nuevo,
        'delta': delta,
    }
