import supabase from '@/lib/supabase'

export const dynamic = 'force-dynamic'

export async function GET(req) {
  try {
    const { searchParams } = new URL(req.url)
    const seccion = searchParams.get('s') || 'resumen'

    if (seccion === 'resumen') {
      const [stock, alertas, movimientos] = await Promise.all([
        supabase
          .from('stock_consolidado')
          .select('*')
          .order('stock_total', { ascending: true }),

        supabase
          .from('alertas_para_compra')
          .select('id, material_id, stock_actual, stock_minimo, cantidad_sugerida_compra, created_at, codigo, nombre_mp, unidad')
          .order('stock_actual', { ascending: true }),

        // FIX: Agregar .eq('tipo', 'produccion') para filtrar SOLO movimientos de producción
        supabase
          .from('movimientos')
          .select('tipo, cantidad, usuario, producto_relacionado, created_at, materiales(nombre_mp)')
          .eq('tipo', 'produccion')  // ← NUEVO: Solo movimientos de producción
          .order('created_at', { ascending: false })
          .limit(50),
      ])

      const stockData = stock.data || []
      const alertasData = alertas.data || []
      const movsData = movimientos.data || []

      // Mapa de stock en vivo por material_id para enriquecer alertas
      const stockMap = {}
      stockData.forEach(m => {
        stockMap[m.id] = m
      })

      // Alertas enriquecidas con stock real
      const alertasEnriquecidas = alertasData.map(a => ({
        ...a,
        cantidad_sugerida: a.cantidad_sugerida_compra,
        materiales: { codigo: a.codigo, nombre_mp: a.nombre_mp, unidad: a.unidad },
        stock_actual: stockMap[a.material_id]?.stock_total ?? a.stock_actual,
        estado_stock_live: stockMap[a.material_id]?.estado_stock ?? 'DESCONOCIDO',
      }))

      // FIX: Mejorar cálculo de movimientos_hoy con timezone awareness
      const ahora = new Date()
      const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate())
      const finHoy = new Date(inicioHoy.getTime() + 24 * 60 * 60 * 1000)

      const movimientosHoy = movsData.filter(m => {
        if (!m.created_at) return false
        const fecha = new Date(m.created_at)
        return fecha >= inicioHoy && fecha < finHoy
      })

      const noCache = {
        headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
      }

      return Response.json(
        {
          kpis: {
            total_mps: stockData.length,
            sin_stock: stockData.filter(m => m.estado_stock === 'SIN STOCK').length,
            bajo_minimo: stockData.filter(m => m.estado_stock === 'BAJO MINIMO').length,
            alertas_activas: alertasEnriquecidas.length,
            movimientos_hoy: movimientosHoy.length, // ← FIX: Ahora cuenta solo producción de hoy
          },
          alertas: alertasEnriquecidas.slice(0, 50),
          movimientos_recientes: movsData.slice(0, 15),
          stock_critico: stockData
            .filter(m => ['SIN STOCK', 'BAJO MINIMO'].includes(m.estado_stock))
            .slice(0, 30),
          stock_ok: stockData.filter(m => m.estado_stock === 'OK').slice(0, 100),
        },
        noCache
      )
    }

    if (seccion === 'stock') {
      const { data } = await supabase
        .from('stock_consolidado')
        .select('*')
        .order('nombre_mp')

      return Response.json(
        { stock: data || [] },
        {
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
        }
      )
    }

    if (seccion === 'vencer') {
      const { data } = await supabase
        .from('lotes_por_vencer')
        .select('*')

      return Response.json({ lotes: data || [] })
    }

    return Response.json({ error: 'Sección no válida' }, { status: 400 })
  } catch (err) {
    console.error('Error en /api/panel:', err)
    return Response.json({ error: err.message }, { status: 500 })
  }
}
