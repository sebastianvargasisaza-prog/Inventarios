-- ============================================================================
-- FIX: Recrear VIEW stock_consolidado para que se recalcule correctamente
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Abre Supabase → SQL Editor
-- 2. Copia TODO este contenido
-- 3. Ejecuta (Ctrl+Enter o botón Run)
-- 4. Verifica que los cambios se reflejen en el panel en ~5 segundos

-- PASO 1: Eliminar el view viejo
DROP VIEW IF EXISTS stock_consolidado CASCADE;

-- PASO 2: Crear el view NUEVO y mejorado
CREATE OR REPLACE VIEW stock_consolidado AS
SELECT
  m.id,
  m.codigo,
  m.nombre_mp,
  m.nombre_inci,
  m.unidad,
  m.stock_minimo,
  -- Suma de cantidad activa en lotes
  COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) AS stock_total,
  -- Cantidad de lotes activos
  COUNT(l.id) FILTER (WHERE l.activo = TRUE AND l.cantidad > 0) AS num_lotes,
  -- Próxima fecha de vencimiento
  MIN(l.fecha_vencimiento) FILTER (WHERE l.activo = TRUE AND l.fecha_vencimiento IS NOT NULL) AS proximo_vencimiento,
  -- Estado del stock
  CASE
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= 0
      THEN 'SIN STOCK'
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= m.stock_minimo
      THEN 'BAJO MINIMO'
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= m.stock_minimo * 1.5
      THEN 'STOCK BAJO'
    ELSE 'OK'
  END AS estado_stock
FROM
  materiales m
LEFT JOIN
  lotes l ON l.material_id = m.id
WHERE
  m.activo = TRUE
GROUP BY
  m.id, m.codigo, m.nombre_mp, m.nombre_inci, m.unidad, m.stock_minimo;

-- PASO 3: Crear índice para mejorar performance
DROP INDEX IF EXISTS idx_lotes_material_activo;
CREATE INDEX idx_lotes_material_activo
  ON lotes(material_id, activo)
  WHERE activo = TRUE;

-- PASO 4: Verificación - Ver primeros 10 registros
SELECT
  nombre_mp,
  stock_total,
  estado_stock,
  num_lotes,
  proximo_vencimiento
FROM stock_consolidado
ORDER BY nombre_mp
LIMIT 10;

-- Si todo funcionó:
-- ✅ Deberías ver arriba los materiales con sus stock actualizados
-- ✅ El panel debería reflejar los cambios en ~5-10 segundos
-- ✅ "MOVIMIENTOS HOY" debería mostrar un número > 0 si hay producciones hoy
