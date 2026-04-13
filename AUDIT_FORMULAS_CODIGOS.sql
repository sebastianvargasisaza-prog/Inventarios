-- ============================================
-- AUDITORÍA DE FÓRMULAS: Revisar códigos canónicos
-- ============================================

-- ============================================
-- PASO 1: VISIÓN GENERAL DE FORMULAS
-- ============================================

SELECT '=== RESUMEN DE FÓRMULAS CARGADAS ===' as audit;

SELECT
  COUNT(*) as total_formulas,
  COUNT(DISTINCT producto_id) as productos_diferentes,
  COUNT(DISTINCT material_id) as materiales_diferentes
FROM formulas_productos;

-- ============================================
-- PASO 2: LISTAR TODAS LAS FORMULAS CON CÓDIGOS
-- ============================================

SELECT '=== DETALLE COMPLETO DE FÓRMULAS ===' as detalle;

SELECT
  fp.id,
  p.codigo as producto_codigo,
  p.nombre as producto_nombre,
  m.codigo as material_codigo,
  m.nombre_inci as material_nombre,
  fp.cantidad_requerida as cantidad,
  fp.unidad,
  CASE
    WHEN m.activo = TRUE THEN '✓ ACTIVO'
    WHEN m.activo = FALSE THEN '✗ INACTIVO'
    WHEN m.id IS NULL THEN '⚠️ SIN REFERENCIA'
  END as estado_material
FROM formulas_productos fp
LEFT JOIN productos p ON fp.producto_id = p.id
LEFT JOIN materiales m ON fp.material_id = m.id
ORDER BY producto_codigo, material_codigo;

-- ============================================
-- PASO 3: DETECTAR PROBLEMAS
-- ============================================

SELECT '=== PROBLEMAS DETECTADOS ===' as problemas;

-- A) Fórmulas que referencian materiales inactivos
SELECT
  fp.id as formula_id,
  p.codigo as producto,
  m.codigo as material_codigo,
  m.nombre_inci,
  m.activo,
  '⚠️ MATERIAL INACTIVO' as problema
FROM formulas_productos fp
LEFT JOIN productos p ON fp.producto_id = p.id
LEFT JOIN materiales m ON fp.material_id = m.id
WHERE m.activo = FALSE;

-- B) Fórmulas con referencia nula (material eliminado)
SELECT
  fp.id as formula_id,
  fp.producto_id,
  fp.material_id,
  '⚠️ MATERIAL NO EXISTE' as problema
FROM formulas_productos fp
WHERE fp.material_id IS NULL
   OR fp.material_id NOT IN (SELECT id FROM materiales);

-- C) Productos que no existen
SELECT
  fp.id as formula_id,
  fp.producto_id,
  m.codigo as material_codigo,
  '⚠️ PRODUCTO NO EXISTE' as problema
FROM formulas_productos fp
LEFT JOIN materiales m ON fp.material_id = m.id
WHERE fp.producto_id IS NULL
   OR fp.producto_id NOT IN (SELECT id FROM productos);

-- ============================================
-- PASO 4: RESUMEN POR PRODUCTO
-- ============================================

SELECT '=== INGREDIENTES POR PRODUCTO ===' as por_producto;

SELECT
  p.codigo as producto,
  p.nombre,
  COUNT(*) as num_ingredientes,
  STRING_AGG(
    m.codigo || ' (' || m.nombre_inci || ')',
    ' | '
  ) as materiales,
  STRING_AGG(
    fp.cantidad_requerida::text || fp.unidad,
    ' | '
  ) as cantidades
FROM formulas_productos fp
LEFT JOIN productos p ON fp.producto_id = p.id
LEFT JOIN materiales m ON fp.material_id = m.id
GROUP BY p.id, p.codigo, p.nombre
ORDER BY p.codigo;

-- ============================================
-- PASO 5: DETECTAR DUPLICADOS EN MISMO PRODUCTO
-- ============================================

SELECT '=== POSIBLES DUPLICADOS EN FÓRMULAS ===' as duplicados;

SELECT
  p.codigo as producto,
  m.nombre_inci as ingrediente,
  COUNT(*) as veces_cargado,
  STRING_AGG(DISTINCT m.codigo, ' | ') as codigos_diferentes,
  SUM(fp.cantidad_requerida) as cantidad_total,
  '⚠️ ESTE INGREDIENTE ESTÁ MÚLTIPLES VECES' as PROBLEMA
FROM formulas_productos fp
LEFT JOIN productos p ON fp.producto_id = p.id
LEFT JOIN materiales m ON fp.material_id = m.id
WHERE m.nombre_inci IS NOT NULL
GROUP BY p.id, p.codigo, m.nombre_inci
HAVING COUNT(*) > 1
ORDER BY p.codigo, m.nombre_inci;

-- ============================================
-- PASO 6: CONSISTENCIA DE CÓDIGOS CANÓNICOS
-- ============================================

SELECT '=== MISMO INGREDIENTE, MÚLTIPLES CÓDIGOS ===' as consistency;

SELECT
  m1.nombre_inci,
  STRING_AGG(DISTINCT m1.codigo, ' | ') as codigos_diferentes,
  COUNT(DISTINCT m1.codigo) as num_codigos,
  '⚠️ NORMALIZACIÓN ROTA' as PROBLEMA
FROM materiales m1
LEFT JOIN formulas_productos fp ON m1.id = fp.material_id
WHERE m1.nombre_inci IS NOT NULL
  AND m1.activo = TRUE
GROUP BY m1.nombre_inci
HAVING COUNT(DISTINCT m1.codigo) > 1
ORDER BY m1.nombre_inci;

-- ============================================
-- PASO 7: RELACIÓN FORMULAS ↔ MATERIALES ↔ LOTES
-- ============================================

SELECT '=== COBERTURA: ¿CADA MATERIAL EN FÓRMULA TIENE STOCK? ===' as cobertura;

SELECT
  m.codigo,
  m.nombre_inci,
  COUNT(DISTINCT fp.producto_id) as en_num_formulas,
  COUNT(DISTINCT l.id) as num_lotes,
  COALESCE(SUM(l.cantidad), 0) as stock_actual,
  CASE
    WHEN COUNT(DISTINCT fp.producto_id) > 0 AND COUNT(DISTINCT l.id) = 0 THEN '⚠️ EN FÓRMULA PERO SIN STOCK'
    WHEN COUNT(DISTINCT fp.producto_id) = 0 AND COUNT(DISTINCT l.id) > 0 THEN '⚠️ CON STOCK PERO NO EN FÓRMULA'
    WHEN COUNT(DISTINCT fp.producto_id) > 0 AND COUNT(DISTINCT l.id) > 0 THEN '✓ OK'
    ELSE '⚠️ MATERIAL HUÉRFANO'
  END as estado
FROM materiales m
LEFT JOIN formulas_productos fp ON m.id = fp.material_id
LEFT JOIN lotes l ON m.id = l.material_id AND l.activo = TRUE
WHERE m.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY m.codigo;
