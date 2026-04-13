-- ============================================
-- AUDITORÍA COMPLETA + LIMPIEZA TOTAL
-- Detecta duplicados antes de eliminar TODO
-- ============================================

-- ============================================
-- PASO 1: AUDITAR DUPLICADOS DE CÓDIGOS CANÓNICOS
-- ============================================

SELECT '=== AUDITORÍA: MISMO NOMBRE CON CÓDIGOS DIFERENTES ===' as audit;

SELECT
  nombre_inci,
  COUNT(DISTINCT codigo) as num_codigos_diferentes,
  STRING_AGG(DISTINCT codigo, ' | ') as codigos_diferentes,
  COUNT(*) as total_registros,
  ARRAY_AGG(DISTINCT activo) as estados_activos
FROM materiales
WHERE nombre_inci IS NOT NULL
GROUP BY nombre_inci
HAVING COUNT(DISTINCT codigo) > 1
ORDER BY nombre_inci;

-- ============================================
-- REPORTE: ESTADO ACTUAL DE BASES DE DATOS
-- ============================================

SELECT '=== ESTADO ACTUAL ===' as estado;

SELECT
  'materiales' as tabla,
  COUNT(*) as total_registros,
  COUNT(CASE WHEN activo = TRUE THEN 1 END) as activos,
  COUNT(CASE WHEN activo = FALSE THEN 1 END) as inactivos
FROM materiales
UNION ALL
SELECT
  'lotes',
  COUNT(*),
  COUNT(CASE WHEN activo = TRUE THEN 1 END),
  COUNT(CASE WHEN activo = FALSE THEN 1 END)
FROM lotes
UNION ALL
SELECT
  'formulas_productos',
  COUNT(*),
  NULL,
  NULL
FROM formulas_productos
UNION ALL
SELECT
  'movimientos_produccion',
  COUNT(*),
  NULL,
  NULL
FROM movimientos_produccion;

-- Detallar stock por material
SELECT '=== STOCK ACTUAL POR MATERIAL ===' as stock;

SELECT
  m.codigo,
  m.nombre_inci,
  COUNT(l.id) as num_lotes,
  COALESCE(SUM(l.cantidad), 0) as cantidad_total,
  m.activo
FROM materiales m
LEFT JOIN lotes l ON m.id = l.material_id
GROUP BY m.id, m.codigo, m.nombre_inci, m.activo
ORDER BY m.codigo;

-- ============================================
-- PASO 2: LISTAR TODOS LOS MATERIALES (para validar)
-- ============================================

SELECT '=== LISTA COMPLETA DE MATERIALES ===' as listado;

SELECT
  id,
  codigo,
  nombre_inci,
  proveedor,
  activo,
  CASE WHEN activo = TRUE THEN '✓ ACTIVO' ELSE '✗ INACTIVO' END as estado
FROM materiales
ORDER BY codigo;

-- ============================================
-- PASO 3: LIMPIEZA TOTAL (DESCOMENTAR PARA EJECUTAR)
-- ============================================

-- ⚠️ DESCOMENTAR PARA EJECUTAR LIMPIEZA TOTAL

/*
DELETE FROM movimientos_produccion;
DELETE FROM formulas_productos;
DELETE FROM lotes;
DELETE FROM materiales;

-- Verificar que todo está vacío
SELECT COUNT(*) as materiales_restantes FROM materiales;
SELECT COUNT(*) as lotes_restantes FROM lotes;
SELECT COUNT(*) as formulas_restantes FROM formulas_productos;
SELECT COUNT(*) as movimientos_restantes FROM movimientos_produccion;
*/

-- ============================================
-- PASO 4: RECARGA LIMPIA (DESPUÉS DE DELETE)
-- ============================================

-- Descomenta SOLO después de ejecutar los DELETE arriba

/*
-- Cargar 7 materiales canónicos sin duplicados
INSERT INTO materiales (codigo, nombre_inci, proveedor, costo, unidad, activo)
VALUES
  ('MPACCL02', 'Acetyl Carnitine', 'Proveedor Estándar', 150.00, 'g', TRUE),
  ('MPPOAZO01', 'Poderoso Azoico', 'Proveedor Estándar', 120.00, 'ml', TRUE),
  ('MPBIOTA00325', 'Biotina', 'Proveedor Estándar', 200.00, 'mg', TRUE),
  ('MPAGE03925', 'AGE Complex', 'Proveedor Estándar', 180.00, 'g', TRUE),
  ('MPPEG027', 'PEG-27', 'Proveedor Estándar', 95.00, 'ml', TRUE),
  ('MPINCH02325', 'Inchada Activa', 'Proveedor Estándar', 160.00, 'g', TRUE),
  ('MPPTR028', 'Proteína 28', 'Proveedor Estándar', 140.00, 'g', TRUE);

-- Cargar inventario limpio
INSERT INTO lotes (material_id, codigo_lote, cantidad, ubicacion, fecha_vencimiento, fecha_ingreso, activo)
SELECT
  m.id,
  t.codigo_lote,
  t.cantidad,
  t.ubicacion,
  CASE WHEN t.fecha_vencimiento IS NOT NULL THEN t.fecha_vencimiento::date ELSE NULL END,
  CURRENT_DATE,
  TRUE
FROM (
  VALUES
    ('MPACCL02', 'AVC25062025AC', 185.0, 'ESTANTERIA 4', NULL::text),
    ('MPPOAZO01', 'ZB826001', 30.0, 'ESTANTERIA 4', NULL::text),
    ('MPBIOTA00325', 'F5491124', 480.0, 'ESTANTERIA 4', NULL::text),
    ('MPAGE03925', '109625', 2000.0, 'ESTANTERIA 4', NULL::text),
    ('MPPEG027', 'SCB1R042410142', 1860.0, 'ESTANTERIA 4', NULL::text),
    ('MPINCH02325', 'GCD200088042141', 1000.0, 'ESTANTERIA 4', NULL::text),
    ('MPPTR028', '211026525', 1000.0, 'ESTANTERIA 4', NULL::text)
) AS t(codigo_mp, codigo_lote, cantidad, ubicacion, fecha_vencimiento)
JOIN materiales m ON m.codigo = t.codigo_mp;

-- Verificar carga
SELECT 'VERIFICACIÓN FINAL' as resultado;
SELECT
  m.codigo,
  m.nombre_inci,
  COUNT(l.id) as num_lotes,
  SUM(l.cantidad) as stock_total
FROM materiales m
LEFT JOIN lotes l ON m.id = l.material_id
WHERE m.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY m.codigo;

SELECT SUM(cantidad) as TOTAL_UNIDADES_EN_STOCK FROM lotes WHERE activo = TRUE;
*/
