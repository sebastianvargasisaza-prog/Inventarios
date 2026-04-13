#!/usr/bin/env node
/**
 * SCRIPT DE DIAGNÓSTICO - Verifica si los datos están actualizándose correctamente
 * Conecta a Supabase y compara:
 * 1. Stock mostrado por view stock_consolidado
 * 2. Stock real (suma de lotes)
 * 3. Movimientos registrados (tipo='produccion')
 */

import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'

// Cargar variables de entorno
const envPath = path.resolve('./app/.env.local')
if (!fs.existsSync(envPath)) {
  console.error('❌ No se encontró .env.local')
  process.exit(1)
}

const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .reduce((acc, line) => {
    const [key, ...val] = line.split('=')
    if (key.trim()) acc[key.trim()] = val.join('=').trim()
    return acc
  }, {})

const URL = env.NEXT_PUBLIC_SUPABASE_URL
const KEY = env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!URL || !KEY) {
  console.error('❌ Faltan variables de entorno SUPABASE')
  process.exit(1)
}

const supabase = createClient(URL, KEY)

console.log('🔍 DIAGNÓSTICO DE INVENTARIO')
console.log('='.repeat(70))

async function diagnostico() {
  try {
    // 1. Traer stock_consolidado (view)
    console.log('\n📊 1. Stock según VIEW (stock_consolidado):')
    const { data: viewStock } = await supabase
      .from('stock_consolidado')
      .select('id, codigo, nombre_mp, stock_total, estado_stock')
      .order('nombre_mp')

    if (!viewStock || viewStock.length === 0) {
      console.log('⚠️  No hay datos en stock_consolidado')
    } else {
      console.log(`✅ ${viewStock.length} materiales en view`)
      viewStock.slice(0, 5).forEach(m => {
        console.log(`   - ${m.nombre_mp}: ${m.stock_total} (${m.estado_stock})`)
      })
      if (viewStock.length > 5) console.log(`   ... y ${viewStock.length - 5} más`)
    }

    // 2. Calcular stock real desde lotes
    console.log('\n🗂️  2. Stock REAL (suma de lotes activos):')
    const { data: lotes } = await supabase
      .from('lotes')
      .select('id, material_id, cantidad, activo')
      .eq('activo', true)
      .gt('cantidad', 0)

    const stockReal = {}
    if (lotes) {
      lotes.forEach(l => {
        stockReal[l.material_id] = (stockReal[l.material_id] || 0) + l.cantidad
      })
    }

    const { data: materiales } = await supabase
      .from('materiales')
      .select('id, nombre_mp')

    let discrepancias = 0
    materiales?.forEach(m => {
      const real = stockReal[m.id] || 0
      const view = viewStock?.find(v => v.id === m.id)?.stock_total || 0
      if (real !== view) {
        discrepancias++
        if (discrepancias <= 5) {
          console.log(`   ⚠️  ${m.nombre_mp}: View=${view}, Real=${real}`)
        }
      }
    })

    if (discrepancias > 0) {
      console.log(`\n🚨 ${discrepancias} discrepancias encontradas (view vs lotes)`)
    } else {
      console.log('✅ Stock coincide entre view y lotes')
    }

    // 3. Verificar movimientos
    console.log('\n📝 3. Movimientos de PRODUCCIÓN (últimas 10):')
    const { data: movimientos } = await supabase
      .from('movimientos')
      .select('id, tipo, cantidad, usuario, created_at, producto_relacionado')
      .eq('tipo', 'produccion')
      .order('created_at', { ascending: false })
      .limit(10)

    if (!movimientos || movimientos.length === 0) {
      console.log('❌ NO HAY movimientos con tipo="produccion"')

      // Ver qué tipos SÍ hay
      const { data: allMovs } = await supabase
        .from('movimientos')
        .select('tipo')
        .order('created_at', { ascending: false })
        .limit(20)

      if (allMovs && allMovs.length > 0) {
        const tipos = [...new Set(allMovs.map(m => m.tipo))]
        console.log(`   Tipos encontrados: ${tipos.join(', ')}`)
      }
    } else {
      console.log(`✅ ${movimientos.length} movimientos de producción`)
      movimientos.forEach(m => {
        const fecha = new Date(m.created_at).toLocaleString('es-ES')
        console.log(`   - ${fecha}: ${m.cantidad} kg (${m.producto_relacionado}) por ${m.usuario}`)
      })
    }

    // 4. Resumen
    console.log('\n' + '='.repeat(70))
    console.log('📋 RESUMEN:')
    if (discrepancias > 0) {
      console.log('❌ PROBLEMA: El view stock_consolidado está DESINCRONIZADO')
      console.log('   Solución: Recrear el view en Supabase')
    } else {
      console.log('✅ Stock está sincronizado')
    }

    if (!movimientos || movimientos.length === 0) {
      console.log('❌ PROBLEMA: No hay movimientos con tipo="produccion"')
      console.log('   Verifica que registrarProduccion() use tipo: "produccion"')
    } else {
      console.log(`✅ ${movimientos.length} movimientos registrados`)
    }

  } catch (err) {
    console.error('❌ Error:', err.message)
  }
}

diagnostico()
