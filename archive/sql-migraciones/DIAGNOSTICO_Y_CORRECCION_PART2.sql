-- DIAGNÓSTICO: Identificar códigos faltantes en MPMP00108-MPMP00207
-- Ejecutar esta consulta primero para ver qué códigos están presentes

SELECT codigo FROM materiales
WHERE codigo >= 'MPMP00108' AND codigo <= 'MPMP00207'
ORDER BY codigo;

-- Resultado esperado: 92 códigos (deberían ser 100)
-- Luego de ejecutar arriba, podrás identificar visualmente cuáles faltan en la secuencia
