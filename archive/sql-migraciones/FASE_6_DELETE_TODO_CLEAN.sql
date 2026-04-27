-- ============================================================================
-- FASE 6: LIMPIAR TODOS LOS DATOS ANTIGUOS
-- ============================================================================
-- Elimina datos de fórmulas y movimientos ANTES de cargar con códigos MPMP
-- Orden: respeta constraints de foreign keys
-- ============================================================================

-- 1. Eliminar movimientos de producción (depende de formulas_productos)
DELETE FROM movimientos_produccion;

-- 2. Eliminar relaciones formula-ingrediente (depende de materiales y formulas)
DELETE FROM formulas_productos;

-- 3. Eliminar lotes históricos (depende de movimientos)
DELETE FROM lotes;

-- ============================================================================
-- RESUMEN DE ELIMINACIÓN
-- ============================================================================
-- ✓ movimientos_produccion: LIMPIO
-- ✓ formulas_productos:     LIMPIO
-- ✓ lotes:                  LIMPIO
--
-- Estado final:
-- - materiales: 212 registros (MPMP00001-MPMP00212) ✓ CONSERVADO
-- - Tablas de fórmulas: vacías, listas para cargar con códigos normalizados
-- ============================================================================
