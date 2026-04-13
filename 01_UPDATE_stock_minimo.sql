-- ============================================================
-- UPDATE stock_minimo BASADO EN CONSUMO REAL ABR-JUN 2026
-- Fuente: Plan_Compras_Corregido_Abr-Jun_2026.xlsx · Hoja "4. Consumo Detallado"
-- Método: max(consumo_mensual × 2, 50) para activos de baja rotación
--         max(consumo_mensual × 1.5, 100) para MPs de alta rotación
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- PASO 1: VER ESTADO ACTUAL antes de hacer cambios (ejecutar primero)
SELECT codigo, nombre_mp, stock_minimo AS minimo_actual
FROM materiales
WHERE activo = TRUE
  AND LOWER(nombre_mp) IN (
    'centella asiatica',
    'acetyl hexapeptide-8',
    'retinaldehido',
    'adenosina',
    'ergotioneina',
    'silimarina',
    'acido hialuronico 50 kd',
    'acido hialuronico 1500 kd',
    'acido hialuronico 300 kd',
    'acido hialuronico 300kda',
    'alfa arbutina',
    'escualeno',
    'ectoina',
    'resveratrol',
    'copper tripeptide 1',
    'backuchiol',
    'glutation',
    'palmitoyl tripeptide-1',
    'palmitoyl tetrapeptide-7',
    'palmitoyl tripeptide-5',
    'biotinoil tripeptido 1',
    'betaglucan'
  )
ORDER BY nombre_mp;

-- ============================================================
-- PASO 2: ACTUALIZAR (ejecutar después de revisar el paso 1)
-- ============================================================
UPDATE materiales
SET stock_minimo = CASE
  -- Alta rotación (>400g/mes) — 1.5× mensual
  WHEN LOWER(nombre_mp) LIKE '%acido hialuronico 50%kd%'   OR LOWER(nombre_mp) = 'acido hialuronico 50 kd'   THEN 2206
  WHEN LOWER(nombre_mp) LIKE '%acido hialuronico 1500%kd%' OR LOWER(nombre_mp) = 'acido hialuronico 1500 kd' THEN 1764
  WHEN LOWER(nombre_mp) LIKE '%alfa arbutina%'                                                                 THEN 2245
  WHEN LOWER(nombre_mp) LIKE '%betaglucan%'                                                                    THEN 565
  WHEN LOWER(nombre_mp) LIKE '%acido hialuronico 300 kd%'  AND LOWER(nombre_mp) NOT LIKE '%300kda%'           THEN 614
  WHEN LOWER(nombre_mp) LIKE '%acido hialuronico 300kda%'                                                      THEN 382

  -- Rotación media — 2× mensual
  WHEN LOWER(nombre_mp) LIKE '%centella asiatica%'                                                             THEN 428
  WHEN LOWER(nombre_mp) LIKE '%silimarina%'                                                                    THEN 79
  WHEN LOWER(nombre_mp) LIKE '%escualeno%'                                                                     THEN 294
  WHEN LOWER(nombre_mp) LIKE '%ectoina%'                                                                       THEN 239
  WHEN LOWER(nombre_mp) LIKE '%resveratrol%'                                                                   THEN 233
  WHEN LOWER(nombre_mp) LIKE '%copper tripeptide%'                                                             THEN 75
  WHEN LOWER(nombre_mp) LIKE '%backuchiol%'                                                                    THEN 70

  -- Activos de baja rotación — piso 50g
  WHEN LOWER(nombre_mp) LIKE '%acetyl hexapeptide%'                                                            THEN 50
  WHEN LOWER(nombre_mp) LIKE '%retinaldehido%'                                                                 THEN 50
  WHEN LOWER(nombre_mp) LIKE '%adenosina%'                                                                     THEN 50
  WHEN LOWER(nombre_mp) LIKE '%ergotioneina%'                                                                  THEN 50
  WHEN LOWER(nombre_mp) LIKE '%glutation%'                                                                     THEN 50
  WHEN LOWER(nombre_mp) LIKE '%palmitoyl tripeptide-1%'                                                        THEN 50
  WHEN LOWER(nombre_mp) LIKE '%palmitoyl tetrapeptide-7%'                                                      THEN 50
  WHEN LOWER(nombre_mp) LIKE '%palmitoyl tripeptide-5%'                                                        THEN 50
  WHEN LOWER(nombre_mp) LIKE '%biotinoil tripeptido%'                                                          THEN 50
  ELSE stock_minimo  -- no tocar lo que no está en la lista
END,
updated_at = NOW()
WHERE activo = TRUE
  AND (
    LOWER(nombre_mp) LIKE '%acido hialuronico 50%kd%'
    OR LOWER(nombre_mp) LIKE '%acido hialuronico 1500%kd%'
    OR LOWER(nombre_mp) LIKE '%alfa arbutina%'
    OR LOWER(nombre_mp) LIKE '%betaglucan%'
    OR LOWER(nombre_mp) LIKE '%acido hialuronico 300%'
    OR LOWER(nombre_mp) LIKE '%centella asiatica%'
    OR LOWER(nombre_mp) LIKE '%silimarina%'
    OR LOWER(nombre_mp) LIKE '%escualeno%'
    OR LOWER(nombre_mp) LIKE '%ectoina%'
    OR LOWER(nombre_mp) LIKE '%resveratrol%'
    OR LOWER(nombre_mp) LIKE '%copper tripeptide%'
    OR LOWER(nombre_mp) LIKE '%backuchiol%'
    OR LOWER(nombre_mp) LIKE '%acetyl hexapeptide%'
    OR LOWER(nombre_mp) LIKE '%retinaldehido%'
    OR LOWER(nombre_mp) LIKE '%adenosina%'
    OR LOWER(nombre_mp) LIKE '%ergotioneina%'
    OR LOWER(nombre_mp) LIKE '%glutation%'
    OR LOWER(nombre_mp) LIKE '%palmitoyl tripeptide%'
    OR LOWER(nombre_mp) LIKE '%palmitoyl tetrapeptide%'
    OR LOWER(nombre_mp) LIKE '%biotinoil tripeptido%'
  );

-- PASO 3: VERIFICAR cambios aplicados
SELECT codigo, nombre_mp, stock_minimo AS minimo_nuevo
FROM materiales
WHERE activo = TRUE
  AND (
    LOWER(nombre_mp) LIKE '%acido hialuronico%'
    OR LOWER(nombre_mp) LIKE '%alfa arbutina%'
    OR LOWER(nombre_mp) LIKE '%betaglucan%'
    OR LOWER(nombre_mp) LIKE '%centella asiatica%'
    OR LOWER(nombre_mp) LIKE '%silimarina%'
    OR LOWER(nombre_mp) LIKE '%escualeno%'
    OR LOWER(nombre_mp) LIKE '%ectoina%'
    OR LOWER(nombre_mp) LIKE '%resveratrol%'
    OR LOWER(nombre_mp) LIKE '%copper tripeptide%'
    OR LOWER(nombre_mp) LIKE '%backuchiol%'
    OR LOWER(nombre_mp) LIKE '%acetyl hexapeptide%'
    OR LOWER(nombre_mp) LIKE '%retinaldehido%'
    OR LOWER(nombre_mp) LIKE '%adenosina%'
    OR LOWER(nombre_mp) LIKE '%ergotioneina%'
    OR LOWER(nombre_mp) LIKE '%glutation%'
    OR LOWER(nombre_mp) LIKE '%palmitoyl%'
    OR LOWER(nombre_mp) LIKE '%biotinoil%'
  )
ORDER BY nombre_mp;
