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
