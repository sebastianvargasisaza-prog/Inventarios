-- ============================================
-- FASE 6: CARGAR MATERIALES CON CÓDIGOS NORMALIZADOS
-- ============================================

-- INSTRUCCIÓN: Reemplaza la lista abajo con la lista maestra que compilemos
-- Formato: ('MPMP00001', 'NOMBRE MATERIAL', 'KG', TRUE),

INSERT INTO materiales (codigo, nombre_inci, unidad, activo)
VALUES
  ('MPMP00001', 'AGUA DESIONIZADA', 'KG', TRUE),
  ('MPMP00002', 'PROPILENGLICOL', 'KG', TRUE),
  ('MPMP00003', 'BETAINA', 'KG', TRUE),
  ('MPMP00004', 'GLICERINA', 'KG', TRUE),
  ('MPMP00005', 'CAFEINA', 'KG', TRUE),
  ('MPMP00006', 'GLUCONOLACTONA', 'KG', TRUE),
  ('MPMP00007', 'FENOXIETANOL', 'KG', TRUE),
  ('MPMP00008', 'ALANTOINA', 'KG', TRUE),
  ('MPMP00009', 'VITAMINA E POLVO', 'KG', TRUE),
  ('MPMP00010', 'ACIDO HIALURONICO 50 KD', 'KG', TRUE),
  ('MPMP00011', 'SILICONA LIQUIDA', 'KG', TRUE),
  ('MPMP00012', 'SORBATO DE POTASIO', 'KG', TRUE),
  ('MPMP00013', 'ACIDO LACTICO', 'KG', TRUE),
  ('MPMP00014', 'BENZOATO DE SODIO', 'KG', TRUE),
  ('MPMP00015', 'ACIDO HIALURONICO 1500 KD', 'KG', TRUE),
  ('MPMP00016', 'ADENOSINA', 'KG', TRUE),
  ('MPMP00017', 'ALOE VERA', 'KG', TRUE),
  ('MPMP00018', 'CENTELLA', 'KG', TRUE),
  ('MPMP00019', 'ACETYL TETRAPEPTIDE-5', 'KG', TRUE),
  ('MPMP00020', 'ACIDO TRANEXAMICO', 'KG', TRUE),
  ('MPMP00021', 'CARBOPOL', 'KG', TRUE),
  ('MPMP00022', 'GOMA XANTAN', 'KG', TRUE),
  ('MPMP00023', 'EDTA DISODICO', 'KG', TRUE),
  ('MPMP00024', 'TRIETANOLAMINA 85%', 'KG', TRUE),
  ('MPMP00025', 'ACIDO CAPRILOIL SALICILICO', 'KG', TRUE),
  ('MPMP00026', 'ACIDO AZELAICO', 'KG', TRUE),
  ('MPMP00027', 'HIDROXIDO DE SODIO', 'KG', TRUE),
  ('MPMP00028', 'AZELOLIL DIGLICINATO DE POTASIO', 'KG', TRUE),
  ('MPMP00029', 'EPI-ON', 'KG', TRUE),
  ('MPMP00030', 'NIACINAMIDA', 'KG', TRUE),
  ('MPMP00031', 'FOSFATO DE ASCORBILO SODICO', 'KG', TRUE),
  ('MPMP00032', 'ZINC PCA', 'KG', TRUE),
  ('MPMP00033', 'ACIDO HIALURONICO 300 KD', 'KG', TRUE),
  ('MPMP00034', 'PANTENOL POLVO', 'KG', TRUE),
  ('MPMP00035', 'ECTOINA', 'KG', TRUE),
  ('MPMP00036', 'TERPENOS SOLUBLES 80%', 'KG', TRUE),
  ('MPMP00037', 'FITATO DE SODIO', 'KG', TRUE),
  ('MPMP00038', 'ACETYL TETRAPEPTIDE-40', 'KG', TRUE),
  ('MPMP00039', '1,2 HEXANEDIOL', 'KG', TRUE),
  ('MPMP00040', 'GRANSIL VX419', 'KG', TRUE),
  ('MPMP00041', 'BIOSURE FE', 'KG', TRUE)
  -- AGREGAR MÁS AQUÍ CUANDO COMPILEMOS LISTA COMPLETA
;

-- ============================================
-- VERIFICACIÓN
-- ============================================

SELECT COUNT(*) as total_materiales FROM materiales;
-- Debe devolver el número total de materiales insertados

SELECT * FROM materiales ORDER BY codigo LIMIT 5;
-- Debe mostrar los primeros 5 materiales normalizados

-- ============================================
-- Checar que no hay duplicados
-- ============================================

SELECT codigo, COUNT(*) FROM materiales
GROUP BY codigo
HAVING COUNT(*) > 1;
-- Debe estar VACÍO (sin resultados)
