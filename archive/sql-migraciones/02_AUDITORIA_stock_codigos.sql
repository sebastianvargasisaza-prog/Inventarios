-- ============================================================
-- AUDITORÍA DE STOCK: DETECCIÓN DE DUPLICADOS MP-XXX vs INCI
-- Problema: al normalizar códigos, se crearon registros INCI nuevos
-- pero los lotes quedaron vinculados a los códigos MP-XXX viejos.
-- Resultado: INCI muestra 0g en panel aunque hay stock real.
-- ============================================================

-- ============================================================
-- QUERY A: MP-XXX ACTIVOS CON STOCK REAL
-- Estos son los "fantasmas" — viejos códigos que tienen lotes
-- y deberían haber sido migrados al código INCI correspondiente
-- ============================================================
SELECT 
  m.id,
  m.codigo,
  m.nombre_mp,
  m.activo,
  ROUND(SUM(COALESCE(l.cantidad, 0))::numeric, 2) AS stock_g,
  COUNT(l.id) AS num_lotes,
  STRING_AGG(l.codigo_lote, ', ') AS lotes
FROM materiales m
LEFT JOIN lotes l ON l.material_id = m.id AND l.activo = TRUE
WHERE m.activo = TRUE 
  AND m.codigo ~ '^MP-[0-9]+'
GROUP BY m.id, m.codigo, m.nombre_mp, m.activo
HAVING SUM(COALESCE(l.cantidad, 0)) > 0
ORDER BY stock_g DESC;

-- ============================================================
-- QUERY B: REGISTROS INCI ACTIVOS CON 0 LOTES
-- Estos son los "huérfanos" — nuevos códigos sin lotes asociados
-- El stock real está en el registro MP-XXX correspondiente
-- ============================================================
SELECT 
  m.id,
  m.codigo,
  m.nombre_mp,
  m.stock_minimo,
  COUNT(l.id) AS num_lotes
FROM materiales m
LEFT JOIN lotes l ON l.material_id = m.id AND l.activo = TRUE
WHERE m.activo = TRUE 
  AND m.codigo NOT LIKE 'MP-%'
GROUP BY m.id, m.codigo, m.nombre_mp, m.stock_minimo
HAVING COUNT(l.id) = 0
ORDER BY m.nombre_mp;

-- ============================================================
-- QUERY C: VISTA COMPLETA — pares MP-XXX + INCI para mismo MP
-- Útil para confirmar qué pares existen antes de hacer merge
-- ============================================================
SELECT 
  m_inci.codigo AS codigo_inci,
  m_inci.nombre_mp,
  m_mp.codigo AS codigo_mp_viejo,
  ROUND(SUM(COALESCE(l.cantidad, 0))::numeric, 2) AS stock_en_mp_viejo,
  COUNT(l.id) AS lotes_en_mp_viejo
FROM materiales m_inci
JOIN materiales m_mp 
  ON LOWER(TRIM(m_inci.nombre_mp)) = LOWER(TRIM(m_mp.nombre_mp))
  AND m_mp.codigo ~ '^MP-[0-9]+'
  AND m_inci.codigo NOT LIKE 'MP-%'
LEFT JOIN lotes l ON l.material_id = m_mp.id AND l.activo = TRUE
WHERE m_inci.activo = TRUE AND m_mp.activo = TRUE
GROUP BY m_inci.codigo, m_inci.nombre_mp, m_mp.codigo
ORDER BY stock_en_mp_viejo DESC;

-- ============================================================
-- QUERY D (EJECUTAR SOLO DESPUÉS DE CONFIRMAR RESULTADOS A/B/C)
-- CORRECCIÓN: Reasignar lotes del código MP-XXX al código INCI
-- CUIDADO: ejecutar primero en 1 caso para verificar
-- ============================================================
/*
-- Ejemplo para UN caso específico (descomentar y adaptar):
UPDATE lotes
SET material_id = (
  SELECT id FROM materiales WHERE codigo = 'CODIGO_INCI_AQUI' AND activo = TRUE LIMIT 1
)
WHERE material_id = (
  SELECT id FROM materiales WHERE codigo = 'MP-XXX' AND activo = TRUE LIMIT 1
)
  AND activo = TRUE;

-- Luego desactivar el código MP-XXX viejo:
UPDATE materiales
SET activo = FALSE, updated_at = NOW()
WHERE codigo = 'MP-XXX';
*/

-- ============================================================
-- QUERY E: RESUMEN EJECUTIVO DEL PROBLEMA
-- ¿Cuántos MPs afectados en total?
-- ============================================================
WITH mp_con_stock AS (
  SELECT m.nombre_mp, SUM(COALESCE(l.cantidad,0)) AS stock_g
  FROM materiales m
  JOIN lotes l ON l.material_id = m.id AND l.activo = TRUE
  WHERE m.activo = TRUE AND m.codigo ~ '^MP-[0-9]+'
  GROUP BY m.nombre_mp
  HAVING SUM(COALESCE(l.cantidad,0)) > 0
),
inci_sin_lotes AS (
  SELECT m.nombre_mp
  FROM materiales m
  LEFT JOIN lotes l ON l.material_id = m.id AND l.activo = TRUE
  WHERE m.activo = TRUE AND m.codigo NOT LIKE 'MP-%'
  GROUP BY m.nombre_mp
  HAVING COUNT(l.id) = 0
)
SELECT 
  COUNT(*) AS pares_duplicados_detectados,
  SUM(mp.stock_g) AS stock_total_afectado_g
FROM mp_con_stock mp
JOIN inci_sin_lotes inci ON LOWER(TRIM(mp.nombre_mp)) = LOWER(TRIM(inci.nombre_mp));
