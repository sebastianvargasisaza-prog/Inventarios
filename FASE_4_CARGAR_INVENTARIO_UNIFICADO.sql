-- ============================================
-- FASE 4: CARGAR INVENTARIO REAL - UNIFICADO
-- Solo códigos válidos que existen en materiales
-- Generado: 2026-04-12 17:54:58
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
    ('MPACCL02', 'AVC25062025AC', 185.0, '4', '2027-06-25')
    ('MPPOAZO01', 'ZB826001', 30.0, '4', '2027-06-02')
    ('MPBIOTA00325', 'F5491124', 480.0, '4', '2026-11-01')
    ('MPAGE03925', '109625', 2000.0, '4', '2027-07-20')
    ('MPPEG027', 'SCB1R042410142', 1860.0, '4', '2026-10-13')
    ('MPINCH02325', 'GCD200088042141', 1000.0, '4', '2027-01-06')
    ('MPPTR028', '211026525', 1000.0, '4', '2027-04-26')
) AS t(codigo_mp, codigo_lote, cantidad, ubicacion, fecha_vencimiento)
JOIN materiales m ON m.codigo = t.codigo_mp;