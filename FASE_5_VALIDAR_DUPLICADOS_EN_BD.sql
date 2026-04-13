-- ============================================
-- FASE 5: VALIDAR DUPLICADOS EN SUPABASE
-- Ejecuta esto en Supabase SQL Editor para confirmar
-- ============================================

SELECT '=== ¿HAY DUPLICADOS EN LA BD? ===' as paso;

-- Query 1: Detectar todos los materiales que tienen múltiples códigos
SELECT
  nombre_inci as MATERIAL,
  COUNT(DISTINCT codigo) as NUM_CODIGOS_DIFERENTES,
  STRING_AGG(DISTINCT codigo, ' | ') as CODIGOS,
  COUNT(*) as TOTAL_REGISTROS,
  STRING_AGG(DISTINCT id::text, ' | ') as IDS
FROM materiales
WHERE nombre_inci IS NOT NULL
GROUP BY nombre_inci
HAVING COUNT(DISTINCT codigo) > 1
ORDER BY NUM_CODIGOS_DIFERENTES DESC;

-- ============================================
-- Resultado esperado:
-- Si la query devuelve filas → SÍ HAY DUPLICADOS → proceder con consolidación
-- Si la query devuelve vacío → NO HAY DUPLICADOS → verificar Excel vs BD
-- ============================================

SELECT '=== DETALLE: QUÉ FORMULAS USAN CADA CÓDIGO ===' as paso;

-- Ejemplo: AGUA DESIONIZADA
SELECT
  m.codigo,
  m.nombre_inci,
  m.id,
  COUNT(fp.id) as USADO_EN_FORMULAS,
  STRING_AGG(DISTINCT p.nombre, ' | ') as PRODUCTOS
FROM materiales m
LEFT JOIN formulas_productos fp ON m.id = fp.material_id
LEFT JOIN productos p ON fp.producto_id = p.id
WHERE UPPER(m.nombre_inci) = 'AGUA DESIONIZADA'
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY CODIGO;

-- ============================================
-- Repetir para los otros materiales problemáticos:
-- - BETAINA
-- - PROPILENGLICOL
-- Cambiar el UPPER(m.nombre_inci) = 'XXX' según corresponda
-- ============================================

SELECT '=== STOCK POR CÓDIGO (para saber cuál tiene inventario) ===' as paso;

-- Ver stock consolidado por código (no por material único)
SELECT
  m.codigo,
  m.nombre_inci,
  m.activo,
  COUNT(l.id) as NUM_LOTES,
  COALESCE(SUM(l.cantidad), 0) as STOCK_TOTAL
FROM materiales m
LEFT JOIN lotes l ON m.id = l.material_id AND l.activo = TRUE
WHERE m.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY m.nombre_inci, m.codigo;

-- ============================================
-- DECISIÓN: Cuál código usar como canónico
-- Criterios:
-- 1. Código más usado en formulas
-- 2. Código con stock actual
-- 3. Código "más correcto" según nomenclatura (MPTXXXXXX)
-- ============================================

SELECT '=== LOTES ACTIVOS POR CÓDIGO ===' as paso;

SELECT
  m.codigo,
  m.nombre_inci,
  l.codigo_lote,
  l.cantidad,
  l.fecha_ingreso
FROM lotes l
JOIN materiales m ON l.material_id = m.id
WHERE l.activo = TRUE
  AND UPPER(m.nombre_inci) IN ('AGUA DESIONIZADA', 'BETAINA', 'PROPILENGLICOL')
ORDER BY m.nombre_inci, m.codigo, l.fecha_ingreso;
