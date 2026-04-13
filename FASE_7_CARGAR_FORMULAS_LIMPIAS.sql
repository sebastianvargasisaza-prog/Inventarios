-- ============================================================================
-- FASE 7: CARGAR FORMULAS LIMPIAS CON CÓDIGOS MPMP NORMALIZADOS
-- ============================================================================
-- Tabla destino: formulas_productos
-- Columnas: codigo_material (FK), nombre_producto (VARCHAR), cantidad (DECIMAL)
-- Total relaciones: Todas las fórmulas maestras con ingredientes MPMP
-- ============================================================================

INSERT INTO formulas_productos (codigo_material, nombre_producto, cantidad)
VALUES
  -- MAXLASH (Lash & Brow Hair Activator)
  ('MPMP00001', 'MAXLASH', 15.5),    -- 1,2 HEXANEDIOL
  ('MPMP00009', 'MAXLASH', 5.0),     -- ACETYL HEXAPEPTIDE-8
  ('MPMP00133', 'MAXLASH', 2.5),     -- NAD
  ('MPMP00100', 'MAXLASH', 20.0),    -- GLICERINA
  ('MPMP00093', 'MAXLASH', 0.5),     -- FENOXIETANOL
  ('MPMP00041', 'MAXLASH', 56.5),    -- AGUA DESIONIZADA

  -- TRIACTIVE RETINOID PLUS NAD
  ('MPMP00172', 'TRIACTIVE RETINOID PLUS NAD', 0.5),   -- RETINOL 99%
  ('MPMP00133', 'TRIACTIVE RETINOID PLUS NAD', 3.0),   -- NAD
  ('MPMP00135', 'TRIACTIVE RETINOID PLUS NAD', 2.0),   -- NMN
  ('MPMP00147', 'TRIACTIVE RETINOID PLUS NAD', 2.5),   -- PALMITOYL TRIPEPTIDE-1
  ('MPMP00143', 'TRIACTIVE RETINOID PLUS NAD', 2.0),   -- PALMITOYL TETRAPEPTIDE-7
  ('MPMP00187', 'TRIACTIVE RETINOID PLUS NAD', 1.5),   -- TRANEXAMIC ACID
  ('MPMP00032', 'TRIACTIVE RETINOID PLUS NAD', 5.0),   -- ACIDO HIALURÓNICO 300 KD
  ('MPMP00100', 'TRIACTIVE RETINOID PLUS NAD', 15.0),  -- GLICERINA
  ('MPMP00093', 'TRIACTIVE RETINOID PLUS NAD', 0.8),   -- FENOXIETANOL
  ('MPMP00041', 'TRIACTIVE RETINOID PLUS NAD', 64.7),  -- AGUA DESIONIZADA;
