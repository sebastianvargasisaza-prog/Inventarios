-- VERIFICACIÓN POST-CARGA: PART 2 (MPMP00108-MPMP00207)
-- Ejecutar DESPUÉS de insertar el contenido de PASO2_Part2_COMPLETO.sql

-- 1. Contar total de materiales en el rango Part 2
SELECT COUNT(*) as total_part2, 'Esperado: 100' as objetivo
FROM materiales
WHERE codigo >= 'MPMP00108' AND codigo <= 'MPMP00207';

-- 2. Verificación general de las 3 partes
SELECT
  (SELECT COUNT(*) FROM materiales WHERE codigo BETWEEN 'MPMP00001' AND 'MPMP00107') as part1_mpmp001_107,
  (SELECT COUNT(*) FROM materiales WHERE codigo BETWEEN 'MPMP00108' AND 'MPMP00207') as part2_mpmp108_207,
  (SELECT COUNT(*) FROM materiales WHERE codigo BETWEEN 'MPMP00208' AND 'MPMP00306') as part3_mpmp208_306,
  (SELECT COUNT(*) FROM materiales WHERE codigo LIKE 'MPMP%') as total_mpmp;

-- 3. Mostrar todos los códigos presentes en Part 2 para inspección visual
SELECT codigo, nombre_inci
FROM materiales
WHERE codigo >= 'MPMP00108' AND codigo <= 'MPMP00207'
ORDER BY codigo;

-- 4. Si alguno falta, mostrará huecos en la secuencia arriba
-- Los 100 deberían ser consecutivos de MPMP00108 a MPMP00207
