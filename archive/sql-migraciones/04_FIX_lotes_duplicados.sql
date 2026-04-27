-- ============================================================
-- FIX LOTES DUPLICADOS — Mismo código de lote en 2 materiales
-- Generado: 2026-04-11 basado en auditoría Query 3
-- ============================================================
-- ESTRATEGIA: para cada par, identificar cuál material es correcto
-- y eliminar (o desactivar) el lote del material incorrecto.
-- EJECUTAR POR GRUPOS — verificar después de cada uno.
-- ============================================================

-- ── VERIFICACIÓN PREVIA ──────────────────────────────────────
-- Corre esto PRIMERO para confirmar cuántos duplicados hay ahora:
SELECT COUNT(*) AS duplicados_activos FROM lotes l1
JOIN lotes l2 ON l1.codigo_lote = l2.codigo_lote AND l1.material_id < l2.material_id
JOIN materiales m1 ON l1.material_id = m1.id
JOIN materiales m2 ON l2.material_id = m2.id
WHERE l1.activo = TRUE AND l2.activo = TRUE;
-- Esperado antes del fix: 21 | Esperado después: 0-4 (los dudosos quedan para verificar manual)


-- ============================================================
-- GRUPO A: LOTES MAL ASIGNADOS (código pertenece a material X,
--          fue insertado por error en material Y)
--          Evidencia: corregir_lotes_mismatch.sql + cantidades distintas
-- ============================================================

-- 1. LYPH251108 → pertenece a ERGOTHIONEINE (100g)
--    Aparece en ACIDO KOJICO con 3072g (cantidad incorrecta, lote asignado por error)
DELETE FROM lotes
WHERE codigo_lote = 'LYPH251108'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPACKOSO01' LIMIT 1)
  AND cantidad = 3072;

-- 2. YT20251209 → pertenece a POTASIUM AZELOYL DIGLICINATE (1300g)
--    Aparece en GLICINA con 1300g (INSERT erróneo)
DELETE FROM lotes
WHERE codigo_lote = 'YT20251209'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPGLICSO01' LIMIT 1);

-- 3. LYPH251029 → pertenece a 3-O-ETHYL ASCORBIC ACID (2000g)
--    Aparece en MYRISTOYL PENTAPEPTIDE-17 con solo 2g (INSERT erróneo)
DELETE FROM lotes
WHERE codigo_lote = 'LYPH251029'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPMYRPENP17' LIMIT 1);

-- 4. 24062024BCA → pertenece a PROPANEDIOL (5000g, BEAUTY PROPANEDIOL)
--    Aparece en BEAUTY OIL CENTELLA ASIATICA con 1000g (INSERT erróneo)
DELETE FROM lotes
WHERE codigo_lote = '24062024BCA'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPBEAUOILCEN01' LIMIT 1);

-- 5. YT20250723 → pertenece a TRITERPENES 80% (100g)
--    Aparece en BENZYL NICOTINATE con 40g (INSERT erróneo)
DELETE FROM lotes
WHERE codigo_lote = 'YT20250723'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPBENZNIC01' LIMIT 1);

-- 6. LYPH251221 → pertenece a ASIATICOSIDE 95% (100g)
--    Aparece en PALMITOYL TETRAPEPTIDO-7 con solo 15g (INSERT erróneo)
DELETE FROM lotes
WHERE codigo_lote = 'LYPH251221'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPPALTETP7' LIMIT 1);

-- 7. LYPH250724 → pertenece a CENTELLA ASIATICA EXTRACT (17.5g)
--    Aparece en VANILLYL BUTYLER con 900g (INSERT erróneo con cantidad incorrecta)
DELETE FROM lotes
WHERE codigo_lote = 'LYPH250724'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPVANIBUTY01' LIMIT 1);

-- 8. LYPH250615 → pertenece a N-ACETYL CYSTEINE (987g)
--    Aparece en HYDROLIZED KERATIN (956g) y MENTHYL LACTTE (700g) — ambos incorrectos
DELETE FROM lotes
WHERE codigo_lote = 'LYPH250615'
  AND material_id IN (
    SELECT id FROM materiales WHERE codigo IN ('MPHYDRKERA01', 'MPMENTLACT01')
  );


-- ============================================================
-- GRUPO B: MISMO PRODUCTO, DOS NOMBRES (nombre comercial vs INCI)
--          Solución: eliminar el lote del registro menos preciso
-- ============================================================

-- 9. 249D3A720 → SILICA (genérico) vs SILICA MSS-500/3H (específico)
--    Mantener en MSS-500, eliminar del genérico
DELETE FROM lotes
WHERE codigo_lote = '249D3A720'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPSILMSO01' LIMIT 1);

-- 10. YT-MBT20240819 → TINOSORB S (marca) vs METHILENE BIS-BENZOTRIAZOLYL (INCI)
--     Mantener en METHILENE BIS-BENZOTRIAZOLYL (INCI), eliminar de TINOSORB S
DELETE FROM lotes
WHERE codigo_lote = 'YT-MBT20240819'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPTINOSB01' LIMIT 1);

-- 11. CP.4229.RGZ.3 → GLYCYRRHIZA GLABRA ROOT EXTRACT (INCI) vs REGALIZ RAIZ POLVO
--     Mantener INCI, eliminar español
DELETE FROM lotes
WHERE codigo_lote = 'CP.4229.RGZ.3'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPREGARAIZPO01' LIMIT 1);

-- 12. LYPH251122 → ACETYL HEXAPEPTIDE-8 (9.8g, cantidad real del lote LYPH)
--     TETRAHEXYLDECYL ASCORBATE tiene 1120g con mismo código → cantidad incorrecta
DELETE FROM lotes
WHERE codigo_lote = 'LYPH251122'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPTHDASOSO01' LIMIT 1);

-- 13. 250306006 → BIOSURE (800g) vs BIOSURE FE (1430g)
--     BIOSURE FE es el nombre completo del producto. Mantener FE, eliminar genérico.
DELETE FROM lotes
WHERE codigo_lote = '250306006'
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPBIOS01' LIMIT 1);


-- ============================================================
-- GRUPO C: VERIFICACIÓN MANUAL REQUERIDA
--          Productos genuinamente distintos con mismo código de lote.
--          NO ejecutar hasta confirmar físicamente cuál es correcto.
-- ============================================================

/*
-- 104001-25 y 114277-25: TWEEN 80 vs TWEEN 20
--   Son moléculas distintas. El mismo código de lote en ambas sugiere
--   error en la carga original. Revisar etiquetas físicas.
--   Una vez confirmado, eliminar del material incorrecto:
DELETE FROM lotes WHERE codigo_lote IN ('104001-25','114277-25')
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPTWEEL02' LIMIT 1);
-- O del TWEEN 20 si resulta ser el erróneo:
DELETE FROM lotes WHERE codigo_lote IN ('104001-25','114277-25')
  AND material_id = (SELECT id FROM materiales WHERE codigo = 'MPTWEELI01' LIMIT 1);

-- FHD-240820-60: BUTYLENE GLYCOL (1000g) vs 1,2 HEXANEDIOL (891g)
--   Son diferentes. Revisar etiqueta física del lote.

-- YT-ET20240812: ETHYLHEXYL TRIAZONE vs ETHYLEXYL METHOXICINNAMATE
--   Ambos fotoprotectores pero distintos. Revisar.

-- 28353823: TINOGARD Q vs TINOGARD TT
--   Variantes distintas del mismo conservante. Revisar.

-- LYPH250606: L-CARNOSINE (170g) vs L-CARNITINA (170g)
--   Aminoácidos distintos. El código LYPH es del mismo proveedor.
--   Revisar etiqueta del lote físico.

-- L17923: FITOEXTRACTO LAVANDA vs ACEITE ESENCIAL LAVANDA → productos distintos
-- 2030125: FITO EXTRACTO ROMERO vs ACEITE ESENCIAL ROMERO → productos distintos
*/


-- ============================================================
-- GRUPO D: MATERIALES DUPLICADOS (mismo nombre, 2 registros activos)
--          Query 2 encontró 2 casos
-- ============================================================

-- JOJOBA: MPBEOJOJO1 (2160g) vs MPBEAUOILJOJ01 (1980g)
-- Mantener MPBEAUOILJOJ01 (código INCI normalizado), transferir lotes del viejo
UPDATE lotes
SET material_id = (SELECT id FROM materiales WHERE codigo = 'MPBEAUOILJOJ01' LIMIT 1)
WHERE material_id = (SELECT id FROM materiales WHERE codigo = 'MPBEOJOJO1' LIMIT 1)
  AND activo = TRUE;
-- Luego desactivar el viejo:
UPDATE materiales SET activo = FALSE, updated_at = NOW()
WHERE codigo = 'MPBEOJOJO1';

-- SILICONA EN ACEITE: MPSILICONAEN01 (16660g) vs MPSILIACEI3501 (4012g)
-- Mantener MPSILICONAEN01 (tiene más stock / parece el principal), transferir lotes
UPDATE lotes
SET material_id = (SELECT id FROM materiales WHERE codigo = 'MPSILICONAEN01' LIMIT 1)
WHERE material_id = (SELECT id FROM materiales WHERE codigo = 'MPSILIACEI3501' LIMIT 1)
  AND activo = TRUE;
UPDATE materiales SET activo = FALSE, updated_at = NOW()
WHERE codigo = 'MPSILIACEI3501';


-- ============================================================
-- VERIFICACIÓN FINAL — correr después de todos los grupos
-- ============================================================
SELECT COUNT(*) AS duplicados_restantes FROM lotes l1
JOIN lotes l2 ON l1.codigo_lote = l2.codigo_lote AND l1.material_id < l2.material_id
JOIN materiales m1 ON l1.material_id = m1.id
JOIN materiales m2 ON l2.material_id = m2.id
WHERE l1.activo = TRUE AND l2.activo = TRUE;

-- Estado final de stock:
SELECT estado_stock, COUNT(*) AS cant, ROUND(SUM(stock_total)::numeric,0) AS total_g
FROM stock_consolidado
GROUP BY estado_stock ORDER BY cant DESC;
