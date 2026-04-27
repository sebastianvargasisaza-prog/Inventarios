-- ============================================
-- FASE 5: CONSOLIDAR CÓDIGOS CANÓNICOS
-- Una vez identifiques qué código usar, ejecuta esto
-- ============================================

-- ============================================
-- CASO 1: AGUA DESIONIZADA
-- Decisión: Usar MPAGUALI01 (está en 4 productos)
-- Eliminar: MPAGUALI02
-- ============================================

-- Paso 1: Reasignar todas las fórmulas que usan MPAGUALI02 a MPAGUALI01
UPDATE formulas_productos
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPAGUALI01' AND nombre_inci = 'AGUA DESIONIZADA'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPAGUALI02' AND nombre_inci = 'AGUA DESIONIZADA'
);

-- Paso 2: Reasignar todos los lotes que usan MPAGUALI02 a MPAGUALI01
UPDATE lotes
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPAGUALI01' AND nombre_inci = 'AGUA DESIONIZADA'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPAGUALI02' AND nombre_inci = 'AGUA DESIONIZADA'
);

-- Paso 3: Verificar que se consolidó
SELECT * FROM materiales
WHERE UPPER(nombre_inci) = 'AGUA DESIONIZADA'
ORDER BY codigo;

-- Paso 4: Eliminar el registro duplicado
DELETE FROM materiales
WHERE codigo = 'MPAGUALI02' AND nombre_inci = 'AGUA DESIONIZADA';

-- Paso 5: Verificar que quedó solo 1
SELECT
  codigo, nombre_inci, COUNT(*) as cant
FROM materiales
WHERE UPPER(nombre_inci) = 'AGUA DESIONIZADA'
GROUP BY codigo, nombre_inci;
-- Debe devolver: 1 fila


-- ============================================
-- CASO 2: BETAINA
-- Decisión: Usar MPBETASO02 (está más usado)
-- Eliminar: MPBETASO01
-- ============================================

-- Paso 1: Reasignar fórmulas
UPDATE formulas_productos
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPBETASO02' AND nombre_inci = 'BETAINA'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPBETASO01' AND nombre_inci = 'BETAINA'
);

-- Paso 2: Reasignar lotes
UPDATE lotes
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPBETASO02' AND nombre_inci = 'BETAINA'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPBETASO01' AND nombre_inci = 'BETAINA'
);

-- Paso 3: Eliminar duplicado
DELETE FROM materiales
WHERE codigo = 'MPBETASO01' AND nombre_inci = 'BETAINA';

-- Paso 4: Verificar
SELECT
  codigo, nombre_inci, COUNT(*) as cant
FROM materiales
WHERE nombre_inci = 'BETAINA'
GROUP BY codigo, nombre_inci;


-- ============================================
-- CASO 3: PROPILENGLICOL
-- Decisión: Usar MPPROPLI01 (está en 4 productos)
-- Eliminar: MPPROLISO01 (es typo)
-- ============================================

-- Paso 1: Reasignar fórmulas
UPDATE formulas_productos
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPPROPLI01' AND UPPER(nombre_inci) = 'PROPILENGLICOL'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPPROLISO01' AND UPPER(nombre_inci) = 'PROPILENGLICOL'
);

-- Paso 2: Reasignar lotes
UPDATE lotes
SET material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPPROPLI01' AND UPPER(nombre_inci) = 'PROPILENGLICOL'
)
WHERE material_id = (
  SELECT id FROM materiales
  WHERE codigo = 'MPPROLISO01' AND UPPER(nombre_inci) = 'PROPILENGLICOL'
);

-- Paso 3: Eliminar duplicado
DELETE FROM materiales
WHERE codigo = 'MPPROLISO01' AND UPPER(nombre_inci) = 'PROPILENGLICOL';

-- Paso 4: Verificar
SELECT
  codigo, nombre_inci, COUNT(*) as cant
FROM materiales
WHERE UPPER(nombre_inci) = 'PROPILENGLICOL'
GROUP BY codigo, nombre_inci;


-- ============================================
-- VERIFICACIÓN FINAL
-- ============================================

SELECT '=== VERIFICACIÓN FINAL ===' as paso;

-- Debe devolver: vacío (0 filas) si no hay más duplicados
SELECT
  nombre_inci,
  COUNT(DISTINCT codigo) as num_codigos,
  STRING_AGG(DISTINCT codigo, ' | ') as codigos
FROM materiales
WHERE nombre_inci IS NOT NULL
GROUP BY nombre_inci
HAVING COUNT(DISTINCT codigo) > 1;

-- Debe devolver: lista de todos los materiales normalizados
SELECT
  codigo,
  nombre_inci,
  COUNT(l.id) as num_lotes,
  COALESCE(SUM(l.cantidad), 0) as stock
FROM materiales m
LEFT JOIN lotes l ON m.id = l.material_id AND l.activo = TRUE
WHERE m.activo = TRUE
GROUP BY m.id, codigo, nombre_inci
ORDER BY codigo;
