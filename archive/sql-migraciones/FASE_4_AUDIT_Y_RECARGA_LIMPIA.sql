-- ============================================
-- AUDITORÍA Y RECARGA LIMPIA DEL INVENTARIO
-- Paso 1: Auditar estado actual
-- Paso 2: Limpiar tabla lotes
-- Paso 3: Recargar solo con códigos válidos
-- ============================================

-- ============================================
-- PASO 1: AUDITORÍA DEL ESTADO ACTUAL
-- ============================================

-- Ver todos los lotes actualmente en la base de datos
SELECT
  l.id,
  m.codigo,
  m.nombre_inci,
  l.codigo_lote,
  l.cantidad,
  l.ubicacion,
  l.fecha_vencimiento,
  l.fecha_ingreso,
  l.activo
FROM lotes l
JOIN materiales m ON l.material_id = m.id
ORDER BY m.codigo, l.id;

-- Ver resumen de stock por material
SELECT
  m.codigo,
  m.nombre_inci,
  COUNT(*) as num_lotes,
  SUM(l.cantidad) as stock_total
FROM lotes l
JOIN materiales m ON l.material_id = m.id
WHERE l.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY m.codigo;

-- Ver stock consolidado desde la vista materializada
SELECT *
FROM stock_consolidado
ORDER BY codigo;

-- ============================================
-- PASO 2: LIMPIAR LA TABLA DE LOTES
-- ============================================

-- Eliminamos todos los lotes existentes
DELETE FROM lotes;

-- Verificar que la tabla quedó vacía
SELECT COUNT(*) as lotes_restantes FROM lotes;

-- ============================================
-- PASO 3: RECARGAR CON CÓDIGOS VÁLIDOS
-- Solo estos 7 códigos existen en materiales y en formulas
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

-- Verificar carga exitosa
SELECT
  m.codigo,
  m.nombre_inci,
  COUNT(*) as num_lotes,
  SUM(l.cantidad) as stock_total
FROM lotes l
JOIN materiales m ON l.material_id = m.id
WHERE l.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_inci
ORDER BY m.codigo;

-- Ver el stock consolidado actualizado
SELECT *
FROM stock_consolidado
ORDER BY codigo;

-- Total de unidades cargadas
SELECT SUM(cantidad) as total_unidades_cargadas
FROM lotes
WHERE activo = TRUE;
