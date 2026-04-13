// ═══════════════════════════════════════════════════════════════════════════
// EJECUTA ESTO EN LA CONSOLA DE SUPABASE EN 3 PASOS:
// ═══════════════════════════════════════════════════════════════════════════
//
// PASO 1: Abre tu navegador → Supabase → Tu proyecto
// PASO 2: Arriba a la derecha, haz clic en el usuario → "API Documentation"
//         (o abre DevTools con F12 → Console)
// PASO 3: Copia TODO este código (desde // hasta el final)
// PASO 4: Pégalo en la consola y presiona ENTER
//
// ═══════════════════════════════════════════════════════════════════════════

(async () => {
  console.log('🔧 Reparando el panel...')

  // Detectar si estamos en Supabase SQL Editor
  const isSqlEditor = window.location.href.includes('supabase') && document.querySelector('[data-testid="sql-editor"]')

  if (!isSqlEditor) {
    console.log('⚠️ No estás en SQL Editor. Abre: Supabase → SQL Editor')
    console.log('Luego copia y pega este script nuevamente.')
    return
  }

  const sql = `DROP VIEW IF EXISTS stock_consolidado CASCADE;

CREATE OR REPLACE VIEW stock_consolidado AS
SELECT
  m.id, m.codigo, m.nombre_mp, m.nombre_inci, m.unidad, m.stock_minimo,
  COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) AS stock_total,
  COUNT(l.id) FILTER (WHERE l.activo = TRUE AND l.cantidad > 0) AS num_lotes,
  MIN(l.fecha_vencimiento) FILTER (WHERE l.activo = TRUE AND l.fecha_vencimiento IS NOT NULL) AS proximo_vencimiento,
  CASE
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= 0 THEN 'SIN STOCK'
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= m.stock_minimo THEN 'BAJO MINIMO'
    WHEN COALESCE(SUM(l.cantidad) FILTER (WHERE l.activo = TRUE), 0) <= m.stock_minimo * 1.5 THEN 'STOCK BAJO'
    ELSE 'OK'
  END AS estado_stock
FROM materiales m
LEFT JOIN lotes l ON l.material_id = m.id
WHERE m.activo = TRUE
GROUP BY m.id, m.codigo, m.nombre_mp, m.nombre_inci, m.unidad, m.stock_minimo;

DROP INDEX IF EXISTS idx_lotes_material_activo;
CREATE INDEX idx_lotes_material_activo ON lotes(material_id, activo) WHERE activo = TRUE;`

  // Buscar el editor de SQL y pegar el código
  const editor = document.querySelector('[data-testid="sql-editor"] textarea') ||
                 document.querySelector('.monaco-editor textarea')

  if (editor) {
    editor.value = sql
    editor.dispatchEvent(new Event('input', { bubbles: true }))
    console.log('✅ SQL pegado en el editor')
    console.log('⏭️  Ahora haz clic en el botón RUN (arriba a la derecha)')
  } else {
    console.log('⚠️ No pude encontrar el editor automáticamente.')
    console.log('Solución manual:')
    console.log('1. Abre Supabase → SQL Editor')
    console.log('2. Copia el contenido de fix_stock_consolidado.sql')
    console.log('3. Pégalo en el editor')
    console.log('4. Haz clic en RUN')
  }
})()
