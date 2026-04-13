-- ============================================
-- LIMPIEZA TOTAL Y RECARGA UNIFICADA
-- Elimina TODO y recarga de forma limpia sin duplicados
-- ============================================

-- ============================================
-- PASO 1: AUDITORÍA PRE-LIMPIEZA
-- ============================================

SELECT 'ESTADO ANTES DE LIMPIEZA' as status;

SELECT COUNT(*) as total_materiales FROM materiales;
SELECT COUNT(*) as total_lotes FROM lotes;
SELECT COUNT(*) as total_formulas FROM formulas_productos;

-- ============================================
-- PASO 2: ELIMINACIÓN EN CASCADA
-- Orden importante: formulas primero, luego lotes, luego materiales
-- ============================================

-- Primero eliminamos las relaciones de movimientos de producción
DELETE FROM movimientos_produccion;

-- Eliminamos las fórmulas
DELETE FROM formulas_productos;

-- Eliminamos los lotes
DELETE FROM lotes;

-- Eliminamos los materiales
DELETE FROM materiales;

-- Verificar que todo está limpio
SELECT 'ESTADO DESPUÉS DE LIMPIEZA' as status;
SELECT COUNT(*) as total_materiales FROM materiales;
SELECT COUNT(*) as total_lotes FROM lotes;
SELECT COUNT(*) as total_formulas FROM formulas_productos;
SELECT COUNT(*) as total_movimientos FROM movimientos_produccion;

-- ============================================
-- PASO 3: RECARGA DE MATERIALES - UNIFICADOS
-- Solo 7 materiales con códigos canónicos limpios
-- ============================================

INSERT INTO materiales (codigo, nombre_inci, proveedor, costo, unidad, activo)
VALUES
  ('MPACCL02', 'Acetyl Carnitine', 'Proveedor Estándar', 150.00, 'g', TRUE),
  ('MPPOAZO01', 'Poderoso Azoico', 'Proveedor Estándar', 120.00, 'ml', TRUE),
  ('MPBIOTA00325', 'Biotina', 'Proveedor Estándar', 200.00, 'mg', TRUE),
  ('MPAGE03925', 'AGE Complex', 'Proveedor Estándar', 180.00, 'g', TRUE),
  ('MPPEG027', 'PEG-27', 'Proveedor Estándar', 95.00, 'ml', TRUE),
  ('MPINCH02325', 'Inchada Activa', 'Proveedor Estándar', 160.00, 'g', TRUE),
  ('MPPTR028', 'Proteína 28', 'Proveedor Estándar', 140.00, 'g', TRUE);

-- Verificar inserción
SELECT 'MATERIALES CARGADOS:' as status;
SELECT id, codigo, nombre_inci, activo FROM materiales ORDER BY codigo;

-- ============================================
-- PASO 4: RECARGA DE INVENTARIO LIMPIO
-- Lotes con cantidades correctas, sin duplicados
-- ============================================

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

-- Verificar inventario cargado
SELECT 'INVENTARIO CARGADO:' as status;
SELECT
  m.codigo,
  m.nombre_inci,
  l.codigo_lote,
  l.cantidad,
  l.ubicacion
FROM lotes l
JOIN materiales m ON l.material_id = m.id
WHERE l.activo = TRUE
ORDER BY m.codigo;

-- Stock consolidado
SELECT 'STOCK CONSOLIDADO POR MATERIAL:' as status;
SELECT *
FROM stock_consolidado
ORDER BY codigo;

-- ============================================
-- PASO 5: RECARGA DE FÓRMULAS UNIFICADAS
-- Solo productos que usan los 7 materiales canónicos
-- ============================================

-- Para esto necesitamos identificar qué productos existen
-- Primero verificamos si hay tabla de productos
-- SELECT COUNT(*) as total_productos FROM productos;

-- Ejemplo de fórmula para un producto (ajusta según tus productos reales):
-- INSERT INTO formulas_productos (producto_id, material_id, cantidad_requerida, unidad)
-- VALUES
--   (?, (SELECT id FROM materiales WHERE codigo = 'MPACCL02'), 10.0, 'g'),
--   (?, (SELECT id FROM materiales WHERE codigo = 'MPPEG027'), 5.0, 'ml');

-- ============================================
-- PASO 6: VERIFICACIÓN FINAL
-- ============================================

SELECT 'VERIFICACIÓN FINAL:' as status;

SELECT COUNT(*) as total_materiales FROM materiales WHERE activo = TRUE;
SELECT COUNT(*) as total_lotes FROM lotes WHERE activo = TRUE;
SELECT SUM(cantidad) as total_unidades_inventario FROM lotes WHERE activo = TRUE;
SELECT COUNT(*) as total_formulas FROM formulas_productos;

SELECT 'LIMPIEZA Y RECARGA COMPLETADA' as resultado;
