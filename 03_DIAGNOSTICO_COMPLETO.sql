-- ============================================================
-- DIAGNÓSTICO COMPLETO DE STOCK — ejecutar TODO de una vez
-- Resultados en 4 tablas. Comparte el resultado de cada query.
-- ============================================================

-- ── QUERY 1: ¿Cuántos materiales activos hay y cuántos sin stock? ─────────────
-- Esperado sano: la mayoría en OK o STOCK BAJO. Muchos SIN STOCK = problema.
SELECT
  estado_stock,
  COUNT(*) AS cant_materiales,
  ROUND(SUM(stock_total)::numeric, 0) AS stock_total_g
FROM stock_consolidado
GROUP BY estado_stock
ORDER BY cant_materiales DESC;


-- ── QUERY 2: Materiales ACTIVOS con mismo nombre (duplicados semánticos) ──────
-- Si aparece aquí = hay 2 registros activos para el mismo MP.
-- Resultado esperado: 0 filas. Cada fila es un problema.
SELECT
  m1.codigo    AS codigo_A,
  m1.nombre_mp AS nombre_A,
  COALESCE((SELECT SUM(l.cantidad) FROM lotes l WHERE l.material_id = m1.id AND l.activo), 0) AS stock_A,
  m2.codigo    AS codigo_B,
  m2.nombre_mp AS nombre_B,
  COALESCE((SELECT SUM(l.cantidad) FROM lotes l WHERE l.material_id = m2.id AND l.activo), 0) AS stock_B
FROM materiales m1
JOIN materiales m2 ON m1.id < m2.id
WHERE m1.activo = TRUE
  AND m2.activo = TRUE
  AND LOWER(TRIM(m1.nombre_mp)) = LOWER(TRIM(m2.nombre_mp))
ORDER BY m1.nombre_mp;


-- ── QUERY 3: Lotes activos duplicados (mismo código en 2+ materiales) ─────────
-- Resultado esperado: 0 filas. Si aparece = está contando stock doble.
SELECT
  l1.codigo_lote,
  m1.codigo || ' · ' || m1.nombre_mp AS material_1,
  l1.cantidad AS g_1,
  m2.codigo || ' · ' || m2.nombre_mp AS material_2,
  l2.cantidad AS g_2,
  (l1.cantidad + l2.cantidad) AS overcounting_g
FROM lotes l1
JOIN lotes l2 ON l1.codigo_lote = l2.codigo_lote
             AND l1.material_id < l2.material_id
JOIN materiales m1 ON l1.material_id = m1.id
JOIN materiales m2 ON l2.material_id = m2.id
WHERE l1.activo = TRUE
  AND l2.activo = TRUE
ORDER BY overcounting_g DESC;


-- ── QUERY 4: Materiales activos SIN LOTES (panel mostrará 0g) ─────────────────
-- Si un MP sin lotes tiene stock_minimo > 0 → genera alerta falsa.
-- Comparte esta lista completa.
SELECT
  m.codigo,
  m.nombre_mp,
  m.stock_minimo,
  COUNT(l.id) AS lotes_activos
FROM materiales m
LEFT JOIN lotes l ON l.material_id = m.id AND l.activo = TRUE AND l.cantidad > 0
WHERE m.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_mp, m.stock_minimo
HAVING COUNT(l.id) = 0
ORDER BY m.nombre_mp;
